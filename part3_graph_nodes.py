import os
import sys
import subprocess

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CURRENT_DIR, "venv", "Scripts", "python.exe")
if os.path.exists(VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(VENV_PYTHON):
    result = subprocess.run([VENV_PYTHON] + sys.argv, check=False)
    sys.exit(result.returncode)

from typing import Literal
from part2_models_and_decisions import (
    retriever,
    llm,
    web_search,
    RouteDecision,
    EvidenceGrade,
    AgentState,
)

# Initialize structured output LLMs
router_llm = llm.with_structured_output(RouteDecision, method="json_mode")
kb_grader_llm = llm.with_structured_output(EvidenceGrade, method="json_mode")
web_grader_llm = llm.with_structured_output(EvidenceGrade, method="json_mode")

# ---------------------------------------------------------------------------
# Section 11: Node 1 — Route the Question
# ---------------------------------------------------------------------------
def route_question(state: AgentState):
    question = state["question"]
    decision = router_llm.invoke(f'''
You are a router for an Agentic RAG assistant.

Route to "kb" if the user asks about:
- Agentic RAG
- LangGraph Agentic RAG workflow
- retrieval grading
- query rewriting
- RAG architecture
- retriever tools
- web fallback in RAG

Route to "direct" only for greetings, thanks, or very simple conversation.

Question:
{question}

Return your response as valid JSON.
Example:
{{"route": "kb"}}
''')
    print("[Router Decision]:", decision.route)
    return {
        "current_query": question,
        "source_used": decision.route,
    }

def route_after_router(state: AgentState) -> Literal["retrieve_kb", "direct_answer"]:
    if state["source_used"] == "kb":
        return "retrieve_kb"
    return "direct_answer"

# ---------------------------------------------------------------------------
# Section 12: Node 2 — Retrieve from the Private KB
# ---------------------------------------------------------------------------
def retrieve_kb(state: AgentState):
    query = state["current_query"]
    docs = retriever.invoke(query)
    print(f"[KB Retriever] Query: {query}")
    print(f"[KB Retriever] Retrieved: {len(docs)} chunks")
    return {"kb_docs": docs}

# ---------------------------------------------------------------------------
# Section 13: Node 3 — Grade Private KB Evidence
# ---------------------------------------------------------------------------
def grade_kb_evidence(state: AgentState):
    question = state["question"]
    context = "\n\n".join(
        f"Source: {doc.metadata.get('source')}\n{doc.page_content}"
        for doc in state["kb_docs"]
    )
    grade = kb_grader_llm.invoke(f'''
You are an evidence grader.

Question:
{question}

Private KB evidence:
{context}

Can this private KB evidence answer the question?
Return "good" if it can answer.
Return "weak" if it cannot answer or is incomplete.

Return your response as valid JSON.
Example:
{{"grade": "good"}}
''')
    print("[KB Grader Decision]:", grade.grade)
    return {"kb_grade": grade.grade}

def decide_after_kb_grade(state: AgentState) -> Literal["generate_from_kb", "search_web"]:
    if state["kb_grade"] == "good":
        return "generate_from_kb"
    return "search_web"

# ---------------------------------------------------------------------------
# Section 14: Node 4 — Tavily Web Search Fallback
# ---------------------------------------------------------------------------
def search_web(state: AgentState):
    query = state["current_query"]
    print(f"[Tavily Search] Query: {query}")
    result = web_search.invoke({"query": query})
    if isinstance(result, dict):
        answer = result.get("answer", "")
        results = result.get("results", [])
        lines = []
        if answer:
            lines.append(f"Tavily answer: {answer}")
        for item in results:
            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "")
            lines.append(f"Title: {title}\nURL: {url}\nContent: {content}")
        web_text = "\n\n".join(lines) if lines else str(result)
    else:
        web_text = str(result)
    print(f"[Tavily Search] Result characters: {len(web_text)}")
    return {
        "web_results": web_text,
        "source_used": "web",
    }

# ---------------------------------------------------------------------------
# Section 15: Node 5 — Grade Web Evidence
# ---------------------------------------------------------------------------
def grade_web_evidence(state: AgentState):
    question = state["question"]
    web_results = state["web_results"]
    grade = web_grader_llm.invoke(f'''
You are an evidence grader.

Question:
{question}

Web search evidence:
{web_results}

Can this web evidence answer the question?
Return "good" if it can answer.
Return "weak" if it cannot answer or is incomplete.

Return your response as valid JSON.
Example:
{{"grade": "good"}}
''')
    print("[Web Grader Decision]:", grade.grade)
    return {"web_grade": grade.grade}

MAX_RETRIES = 1

def decide_after_web_grade(state: AgentState) -> Literal["generate_from_web", "rewrite_query", "answer_insufficient"]:
    if state["web_grade"] == "good":
        return "generate_from_web"
    if state["retry_count"] < MAX_RETRIES:
        return "rewrite_query"
    return "answer_insufficient"

# ---------------------------------------------------------------------------
# Section 16: Node 6 — Rewrite the Query
# ---------------------------------------------------------------------------
def rewrite_query(state: AgentState):
    question = state["question"]
    retry_count = state["retry_count"] + 1
    rewritten = llm.invoke(f'''
Rewrite the question for better retrieval and web search.

Rules:
- Preserve original intent.
- Make it specific and search-friendly.
- Do not answer.
- Return only the rewritten query.

Original question:
{question}
''').content.strip()
    print("[Rewriter Query]:", rewritten)
    return {
        "current_query": rewritten,
        "retry_count": retry_count,
    }

# ---------------------------------------------------------------------------
# Section 17: Node 7 — Generate from Private KB
# ---------------------------------------------------------------------------
def generate_from_kb(state: AgentState):
    question = state["question"]
    context = "\n\n".join(
        f"[KB Source: {doc.metadata.get('source')}]\n{doc.page_content}"
        for doc in state["kb_docs"]
    )
    answer = llm.invoke(f'''
You are a technical instructor.

Answer using ONLY the private KB context.

Rules:
- Beginner-friendly explanation.
- Do not invent unsupported details.
- Mention that the answer is based on the private KB.
- Include source type: Private KB.

Question:
{question}

Private KB context:
{context}
''').content
    return {
        "answer": answer,
        "source_used": "private_kb",
    }

# ---------------------------------------------------------------------------
# Section 18: Node 8 — Generate from Web Search
# ---------------------------------------------------------------------------
def generate_from_web(state: AgentState):
    question = state["question"]
    web_context = state["web_results"]
    answer = llm.invoke(f'''
You are a technical instructor.

The private KB was insufficient, so web search was used.

Answer using ONLY the web search context.

Rules:
- Beginner-friendly explanation.
- Do not invent unsupported details.
- Mention that the answer is based on Tavily web search.
- Include source type: Web Search.
- If URLs are present in context, include the most useful ones.

Question:
{question}

Web search context:
{web_context}
''').content
    return {
        "answer": answer,
        "source_used": "web_search",
    }

# ---------------------------------------------------------------------------
# Section 19: Node 9 — Direct Answer
# ---------------------------------------------------------------------------
def direct_answer(state: AgentState):
    question = state["question"]
    answer = llm.invoke(f'''
Respond briefly and naturally.

Message:
{question}
''').content
    return {
        "answer": answer,
        "source_used": "direct",
    }

# ---------------------------------------------------------------------------
# Section 20: Node 10 — Insufficient Evidence Answer
# ---------------------------------------------------------------------------
def answer_insufficient(state: AgentState):
    answer = (
        "I could not find enough reliable evidence in the private knowledge base "
        "or the web search results to answer this confidently. "
        "Please provide more specific documents or rephrase the question."
    )
    return {
        "answer": answer,
        "source_used": "insufficient_evidence",
    }

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PART 3: GRAPH NODES (10 NODES DEFINED)")
    print("=" * 60)
    print("Nodes ready:")
    print("1.  route_question")
    print("2.  retrieve_kb")
    print("3.  grade_kb_evidence")
    print("4.  search_web")
    print("5.  grade_web_evidence")
    print("6.  rewrite_query")
    print("7.  generate_from_kb")
    print("8.  generate_from_web")
    print("9.  direct_answer")
    print("10. answer_insufficient")
    print("\nTesting Router Node with test question:")
    res = route_question({"question": "Hello there", "current_query": "", "kb_docs": [], "web_results": "", "kb_grade": "", "web_grade": "", "answer": "", "source_used": "", "retry_count": 0})
    print("Output:", res)
    print("=" * 60)

