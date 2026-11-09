import os
import json
from datetime import datetime
from typing import List, Literal, Optional
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END

from app.core.config import settings
from app.rag.state import RouteDecision, EvidenceGrade, AgentState, Citation, TraceStep
from app.rag.vectorstore import vector_manager


def get_llm():
    """Initializes LLM from Groq or OpenAI."""
    if settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=0,
            groq_api_key=settings.GROQ_API_KEY,
        )
    elif settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    else:
        raise ValueError("Neither GROQ_API_KEY nor OPENAI_API_KEY is configured.")


def get_web_search():
    """Initializes Tavily Web Search."""
    if not settings.TAVILY_API_KEY:
        return None
    from langchain_tavily import TavilySearch
    return TavilySearch(
        max_results=5,
        topic="general",
        include_answer=True,
        include_raw_content=False,
        tavily_api_key=settings.TAVILY_API_KEY,
    )


# Initialize global tools and models
llm = get_llm()
web_search = get_web_search()

# Structured output bindings with fallback
try:
    router_llm = llm.with_structured_output(RouteDecision, method="json_mode")
    kb_grader_llm = llm.with_structured_output(EvidenceGrade, method="json_mode")
    web_grader_llm = llm.with_structured_output(EvidenceGrade, method="json_mode")
except Exception:
    router_llm = llm
    kb_grader_llm = llm
    web_grader_llm = llm


def add_trace(state: AgentState, node: str, status: str, details: str):
    """Helper to record execution trace steps."""
    trace_list = list(state.get("trace", []))
    trace_list.append({
        "node": node,
        "status": status,
        "details": details,
        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
    })
    return trace_list


# ---------------------------------------------------------------------------
# Node 1: Route Question
# ---------------------------------------------------------------------------
def route_question(state: AgentState) -> dict:
    question = state["question"]
    prompt = f"""You are a specialized Query Router for an Enterprise Human Resources (HR) & Employee Support Copilot.

Route to "kb" if the user's question relates to:
- Company HR policies, leave rules, sick leave, maternity/paternity leave, or time-off
- Remote work, hybrid schedules, office stipends, or working hours
- Attendance rules, punctuality, holidays, overtime, or timesheets
- Payroll dates, salary breakdown, compensation, tax deductions, or expense reimbursements
- Health insurance, medical coverage, wellness stipends, dental, or vision allowances
- Onboarding, probation periods, resignation notice periods, or offboarding steps
- Code of conduct, harassment reporting (POSH), ethics, or whistleblowing
- Employee records, privacy, HR service desk requests, or requisition forms
- Any workplace inquiry or knowledge base question

Route to "direct" ONLY for simple greetings (e.g. "hi", "hello", "good morning"), expressions of thanks ("thank you"), or brief casual pleasantries that do not ask a factual question.

User Question: {question}

Return your response as valid JSON matching this schema:
{{"route": "kb" | "direct", "reasoning": "brief explanation"}}
"""
    try:
        decision = router_llm.invoke(prompt)
        if isinstance(decision, RouteDecision):
            route_val = decision.route
            reason_val = decision.reasoning or ""
        elif hasattr(decision, "content"):
            content = decision.content.strip()
            # fallback json parse
            data = json.loads(content) if "{" in content else {}
            route_val = data.get("route", "kb")
            reason_val = data.get("reasoning", "")
        else:
            route_val = getattr(decision, "route", "kb")
            reason_val = ""
    except Exception as e:
        print(f"[Router Exception] Falling back to 'kb': {e}")
        route_val = "kb"
        reason_val = f"Fallback route: {e}"

    trace = add_trace(
        state,
        node="Router",
        status="success",
        details=f"Query routed to '{route_val}'. {reason_val}".strip(),
    )

    return {
        "current_query": question,
        "source_used": route_val,
        "trace": trace,
    }


def route_after_router(state: AgentState) -> Literal["retrieve_kb", "direct_answer"]:
    if state.get("source_used") == "kb":
        return "retrieve_kb"
    return "direct_answer"


# ---------------------------------------------------------------------------
# Node 2: Retrieve from Private KB
# ---------------------------------------------------------------------------
def retrieve_kb(state: AgentState) -> dict:
    query = state.get("current_query", state["question"])
    retriever = vector_manager.get_retriever()
    docs = retriever.invoke(query)
    
    trace = add_trace(
        state,
        node="KB Retriever",
        status="success",
        details=f"Retrieved {len(docs)} document chunks from Pinecone namespace '{settings.PINECONE_NAMESPACE}' for query: '{query}'.",
    )
    return {
        "kb_docs": docs,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 3: Grade KB Evidence
# ---------------------------------------------------------------------------
def grade_kb_evidence(state: AgentState) -> dict:
    question = state["question"]
    docs = state.get("kb_docs", [])
    
    if not docs:
        trace = add_trace(
            state,
            node="KB Grader",
            status="weak",
            details="Zero documents retrieved from private KB. Fallback required.",
        )
        return {"kb_grade": "weak", "trace": trace}

    context = "\n\n".join(
        f"[Document: {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}"
        for doc in docs
    )
    prompt = f"""You are an expert HR Evidence Grader.

Question:
{question}

Retrieved Private HR Knowledge Base Evidence:
{context}

Does this retrieved evidence contain specific, accurate information to address the employee's question?
Return "good" if the evidence can directly answer the question.
Return "weak" if the evidence is insufficient, irrelevant, or lacks key details.

Respond with valid JSON:
{{"grade": "good" | "weak", "explanation": "brief reason"}}
"""
    try:
        grade_res = kb_grader_llm.invoke(prompt)
        if isinstance(grade_res, EvidenceGrade):
            grade_val = grade_res.grade
            expl = grade_res.explanation or ""
        elif hasattr(grade_res, "content"):
            content = grade_res.content.strip()
            data = json.loads(content) if "{" in content else {}
            grade_val = data.get("grade", "good")
            expl = data.get("explanation", "")
        else:
            grade_val = getattr(grade_res, "grade", "good")
            expl = ""
    except Exception as e:
        print(f"[KB Grader Exception] Defaulting to good: {e}")
        grade_val = "good"
        expl = "Defaulted due to evaluation error"

    trace = add_trace(
        state,
        node="KB Grader",
        status=grade_val,
        details=f"KB evidence graded as '{grade_val}'. {expl}".strip(),
    )
    return {"kb_grade": grade_val, "trace": trace}


def decide_after_kb_grade(state: AgentState) -> Literal["generate_from_kb", "search_web"]:
    if state.get("kb_grade") == "good":
        return "generate_from_kb"
    return "search_web"


# ---------------------------------------------------------------------------
# Node 4: Tavily Web Search Fallback
# ---------------------------------------------------------------------------
def search_web(state: AgentState) -> dict:
    query = state.get("current_query", state["question"])
    if not web_search:
        trace = add_trace(
            state,
            node="Web Search",
            status="skipped",
            details="Tavily Web Search is not configured or API key missing.",
        )
        return {"web_results": "", "source_used": "web", "trace": trace}

    try:
        result = web_search.invoke({"query": f"company HR standard {query}"})
        lines = []
        if isinstance(result, dict):
            if result.get("answer"):
                lines.append(f"Summary Answer: {result['answer']}")
            for item in result.get("results", []):
                title = item.get("title", "")
                url = item.get("url", "")
                content = item.get("content", "")
                lines.append(f"Source: {title} ({url})\nContent: {content}")
            web_text = "\n\n".join(lines) if lines else str(result)
        else:
            web_text = str(result)
    except Exception as e:
        web_text = ""
        print(f"[Web Search Error]: {e}")

    trace = add_trace(
        state,
        node="Web Search",
        status="success" if web_text else "empty",
        details=f"Tavily web search completed ({len(web_text)} characters received).",
    )
    return {
        "web_results": web_text,
        "source_used": "web",
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 5: Grade Web Evidence
# ---------------------------------------------------------------------------
def grade_web_evidence(state: AgentState) -> dict:
    question = state["question"]
    web_results = state.get("web_results", "")
    
    if not web_results.strip():
        trace = add_trace(
            state,
            node="Web Grader",
            status="weak",
            details="Web search returned no usable results.",
        )
        return {"web_grade": "weak", "trace": trace}

    prompt = f"""You are an Evidence Grader evaluating external web search results for an HR inquiry.

Question:
{question}

Web Search Evidence:
{web_results[:3000]}

Can this web search evidence help answer the employee's inquiry?
Return "good" if it contains relevant, useful context.
Return "weak" if it is irrelevant or off-topic.

Respond with valid JSON:
{{"grade": "good" | "weak", "explanation": "brief reason"}}
"""
    try:
        grade_res = web_grader_llm.invoke(prompt)
        if isinstance(grade_res, EvidenceGrade):
            grade_val = grade_res.grade
            expl = grade_res.explanation or ""
        elif hasattr(grade_res, "content"):
            content = grade_res.content.strip()
            data = json.loads(content) if "{" in content else {}
            grade_val = data.get("grade", "good")
            expl = data.get("explanation", "")
        else:
            grade_val = getattr(grade_res, "grade", "good")
            expl = ""
    except Exception:
        grade_val = "good"
        expl = "Defaulted to good"

    trace = add_trace(
        state,
        node="Web Grader",
        status=grade_val,
        details=f"Web evidence graded as '{grade_val}'. {expl}".strip(),
    )
    return {"web_grade": grade_val, "trace": trace}


def decide_after_web_grade(state: AgentState) -> Literal["generate_from_web", "rewrite_query", "answer_insufficient"]:
    if state.get("web_grade") == "good":
        return "generate_from_web"
    if state.get("retry_count", 0) < settings.MAX_RETRIES:
        return "rewrite_query"
    return "answer_insufficient"


# ---------------------------------------------------------------------------
# Node 6: Rewrite Query for Retry
# ---------------------------------------------------------------------------
def rewrite_query(state: AgentState) -> dict:
    question = state["question"]
    retry_count = state.get("retry_count", 0) + 1
    
    prompt = f"""You are an HR Search Query Optimizer.
The previous search query failed to locate adequate documents for this employee question:
"{question}"

Rewrite the query to be clearer, more standard, and optimized for vector retrieval across HR policy manuals, employee handbooks, leave rules, and enterprise procedures.
Rules:
- Preserve the exact user intent.
- Use official enterprise terminology (e.g., "annual leave", "maternity policy", "notice period", "expense claim").
- Return ONLY the rewritten search query with no additional commentary.
"""
    try:
        rewritten = llm.invoke(prompt).content.strip()
    except Exception:
        rewritten = question

    trace = add_trace(
        state,
        node="Query Rewriter",
        status="retrying",
        details=f"Query reformulated (Retry {retry_count}/{settings.MAX_RETRIES}): '{rewritten}'",
    )
    return {
        "current_query": rewritten,
        "retry_count": retry_count,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 7: Generate Answer from Private KB
# ---------------------------------------------------------------------------
def generate_from_kb(state: AgentState) -> dict:
    question = state["question"]
    docs = state.get("kb_docs", [])
    
    context_chunks = []
    citations: List[Citation] = []
    
    for i, doc in enumerate(docs):
        src = doc.metadata.get("source", f"HR Document {i+1}")
        context_chunks.append(f"[Source: {src}]\n{doc.page_content}")
        citations.append({
            "source": src,
            "title": src.replace("_", " ").replace(".md", "").title(),
            "snippet": doc.page_content[:240].replace("\n", " ").strip() + "...",
        })
        
    context = "\n\n".join(context_chunks)

    prompt = f"""You are the official Enterprise HR Policy & Employee Support AI Copilot.

Answer the employee's question using ONLY the provided official Private HR Knowledge Base documentation.

Guidelines:
1. Provide an authoritative, professional, empathetic, and clear response.
2. Structure your answer logically with bullet points or sections where appropriate.
3. Cite the relevant policy documents (e.g., HR-POL-001, Leave Policy) directly in your response.
4. Do not invent details not stated in the documentation.
5. If the documentation mentions specific timelines, forms, or portals, include them accurately.

Employee Question:
{question}

Official HR Documentation Context:
{context}
"""
    answer = llm.invoke(prompt).content
    
    trace = add_trace(
        state,
        node="Generator",
        status="success",
        details=f"Synthesized authoritative answer from {len(docs)} private HR policy sources.",
    )
    return {
        "answer": answer,
        "source_used": "private_kb",
        "citations": citations,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 8: Generate Answer from Web Search
# ---------------------------------------------------------------------------
def generate_from_web(state: AgentState) -> dict:
    question = state["question"]
    web_context = state.get("web_results", "")
    
    prompt = f"""You are the Enterprise HR Policy & Employee Support AI Copilot.

Notice: The internal private HR policy database did not contain complete information for this query. Information was retrieved from external benchmark and web resources.

Guidelines:
1. Transparently inform the employee that this guidance is based on industry standards and external search results rather than internal proprietary policy.
2. Advise the employee to verify this with their People Partner / HRBP for organization-specific exceptions.
3. Provide an informative, well-structured answer based on the web context.

Employee Question:
{question}

External Web Evidence:
{web_context}
"""
    answer = llm.invoke(prompt).content
    
    citations: List[Citation] = [{
        "source": "External Web Search (Tavily)",
        "title": "Public HR Industry Standards",
        "snippet": web_context[:250].replace("\n", " ").strip() + "...",
    }]

    trace = add_trace(
        state,
        node="Generator",
        status="fallback",
        details="Generated answer from external web search with enterprise disclaimer.",
    )
    return {
        "answer": answer,
        "source_used": "web_search",
        "citations": citations,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 9: Direct Conversational Answer
# ---------------------------------------------------------------------------
def direct_answer(state: AgentState) -> dict:
    question = state["question"]
    prompt = f"""You are the Enterprise HR Policy & Employee Support AI Copilot.
Respond warmly, professionally, and politely to this greeting or conversational message.
Introduce yourself briefly as the AI assistant ready to help with company leave, benefits, payroll, onboarding, or HR policies.

User Message: {question}
"""
    answer = llm.invoke(prompt).content
    trace = add_trace(
        state,
        node="Direct Response",
        status="success",
        details="Provided conversational greeting without triggering document retrieval.",
    )
    return {
        "answer": answer,
        "source_used": "direct",
        "citations": [],
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Node 10: Insufficient Evidence Fallback
# ---------------------------------------------------------------------------
def answer_insufficient(state: AgentState) -> dict:
    answer = (
        "I could not locate verified policy documentation in the Enterprise HR Knowledge Base "
        "or through external web search to answer your specific inquiry with confidence.\n\n"
        "**Recommended Next Steps:**\n"
        "- Submit an inquiry ticket to the People Support Desk via JIRA (`https://hr.enterprise.internal/support`)\n"
        "- Contact your designated HR Business Partner (HRBP) directly\n"
        "- For urgent personal or medical matters, reach the 24/7 Employee Emergency Line at `+1 (800) 555-0199`"
    )
    trace = add_trace(
        state,
        node="Fallback",
        status="insufficient",
        details="Max retries reached without finding reliable evidence. Escalated to HR Service Desk.",
    )
    return {
        "answer": answer,
        "source_used": "insufficient_evidence",
        "citations": [],
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# StateGraph Assembly and Compilation
# ---------------------------------------------------------------------------
def build_agent_workflow():
    builder = StateGraph(AgentState)

    # 1. Add all 10 nodes
    builder.add_node("route_question", route_question)
    builder.add_node("retrieve_kb", retrieve_kb)
    builder.add_node("grade_kb_evidence", grade_kb_evidence)
    builder.add_node("search_web", search_web)
    builder.add_node("grade_web_evidence", grade_web_evidence)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("generate_from_kb", generate_from_kb)
    builder.add_node("generate_from_web", generate_from_web)
    builder.add_node("direct_answer", direct_answer)
    builder.add_node("answer_insufficient", answer_insufficient)

    # 2. Add edges and conditional branches
    builder.add_edge(START, "route_question")

    builder.add_conditional_edges(
        "route_question",
        route_after_router,
        {
            "retrieve_kb": "retrieve_kb",
            "direct_answer": "direct_answer",
        },
    )

    builder.add_edge("retrieve_kb", "grade_kb_evidence")

    builder.add_conditional_edges(
        "grade_kb_evidence",
        decide_after_kb_grade,
        {
            "generate_from_kb": "generate_from_kb",
            "search_web": "search_web",
        },
    )

    builder.add_edge("search_web", "grade_web_evidence")

    builder.add_conditional_edges(
        "grade_web_evidence",
        decide_after_web_grade,
        {
            "generate_from_web": "generate_from_web",
            "rewrite_query": "rewrite_query",
            "answer_insufficient": "answer_insufficient",
        },
    )

    builder.add_edge("rewrite_query", "retrieve_kb")
    builder.add_edge("generate_from_kb", END)
    builder.add_edge("generate_from_web", END)
    builder.add_edge("direct_answer", END)
    builder.add_edge("answer_insufficient", END)

    return builder.compile()


# Compiled LangGraph Runnable
agent_app = build_agent_workflow()


def ask_hr_copilot(question: str) -> AgentState:
    """Convenience execution runner returning complete state including citations and trace."""
    initial_state: AgentState = {
        "question": question,
        "current_query": question,
        "kb_docs": [],
        "web_results": "",
        "kb_grade": "",
        "web_grade": "",
        "answer": "",
        "source_used": "",
        "retry_count": 0,
        "citations": [],
        "trace": [],
    }
    return agent_app.invoke(initial_state)
