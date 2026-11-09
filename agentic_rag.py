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
# Modular Imports from the 7 Project Components
# ---------------------------------------------------------------------------
# Part 1: Sections 1-6 (Vector database and retriever setup)
from part1_vector_db import embeddings, vectorstore, retriever, pc, INDEX_NAME, NAMESPACE

# Part 2: Sections 7-10 (Models, search tools, and structured decision schemas)
from part2_models_and_decisions import llm, web_search, RouteDecision, EvidenceGrade, AgentState

# Part 3: Sections 11-20 (Graph nodes and conditional decision logic)
import part3_graph_nodes

# Part 4: Section 21 (StateGraph compilation)
from part4_build_workflow import workflow, app

# Part 5: Section 22 (Graph visualization)
from part5_visualize_graph import visualize_graph

# Part 6: Section 23 (Helper function)
from part6_helper_function import ask_agent

# Part 7: Sections 24-27 (Demos 1-4)
from part7_run_demos import run_all_demos

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Industry-style Agentic RAG assistant.")
    parser.add_argument("--query", "-q", type=str, help="Ask a single question directly.")
    parser.add_argument("--visualize", "-v", action="store_true", help="Generate graph visualization.")
    args = parser.parse_args()

    if args.visualize:
        visualize_graph()
    elif args.query:
        ask_agent(args.query)
    else:
        run_all_demos()
