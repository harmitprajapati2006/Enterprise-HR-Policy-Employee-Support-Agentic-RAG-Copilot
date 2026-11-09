import os
import sys
import subprocess

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CURRENT_DIR, "venv", "Scripts", "python.exe")
if os.path.exists(VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(VENV_PYTHON):
    result = subprocess.run([VENV_PYTHON] + sys.argv, check=False)
    sys.exit(result.returncode)

# ---------------------------------------------------------------------------
# Section 21: Build the LangGraph Workflow
# ---------------------------------------------------------------------------
from langgraph.graph import StateGraph, START, END
from part2_models_and_decisions import AgentState
from part3_graph_nodes import (
    route_question,
    route_after_router,
    retrieve_kb,
    grade_kb_evidence,
    decide_after_kb_grade,
    search_web,
    grade_web_evidence,
    decide_after_web_grade,
    rewrite_query,
    generate_from_kb,
    generate_from_web,
    direct_answer,
    answer_insufficient,
)

# Initialize graph
workflow = StateGraph(AgentState)

# Add all 10 nodes
workflow.add_node("route_question", route_question)
workflow.add_node("retrieve_kb", retrieve_kb)
workflow.add_node("grade_kb_evidence", grade_kb_evidence)
workflow.add_node("search_web", search_web)
workflow.add_node("grade_web_evidence", grade_web_evidence)
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("generate_from_kb", generate_from_kb)
workflow.add_node("generate_from_web", generate_from_web)
workflow.add_node("direct_answer", direct_answer)
workflow.add_node("answer_insufficient", answer_insufficient)

# Connect edges & conditional branching
workflow.add_edge(START, "route_question")

workflow.add_conditional_edges(
    "route_question",
    route_after_router,
    {
        "retrieve_kb": "retrieve_kb",
        "direct_answer": "direct_answer",
    },
)

workflow.add_edge("retrieve_kb", "grade_kb_evidence")

workflow.add_conditional_edges(
    "grade_kb_evidence",
    decide_after_kb_grade,
    {
        "generate_from_kb": "generate_from_kb",
        "search_web": "search_web",
    },
)

workflow.add_edge("search_web", "grade_web_evidence")

workflow.add_conditional_edges(
    "grade_web_evidence",
    decide_after_web_grade,
    {
        "generate_from_web": "generate_from_web",
        "rewrite_query": "rewrite_query",
        "answer_insufficient": "answer_insufficient",
    },
)

workflow.add_edge("rewrite_query", "retrieve_kb")
workflow.add_edge("generate_from_kb", END)
workflow.add_edge("generate_from_web", END)
workflow.add_edge("direct_answer", END)
workflow.add_edge("answer_insufficient", END)

# Compile graph into executable runnable
app = workflow.compile()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PART 4: LANGGRAPH WORKFLOW COMPILED")
    print("=" * 60)
    print("Industry-style Agentic RAG graph compiled successfully.")
    print("Nodes in compiled graph:", list(workflow.nodes.keys()))
    print("Graph Runnable ready:", app is not None)
    print("=" * 60)

