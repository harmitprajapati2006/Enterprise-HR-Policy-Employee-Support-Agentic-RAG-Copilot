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
# Section 23: Helper Function
# ---------------------------------------------------------------------------
from part2_models_and_decisions import AgentState
from part4_build_workflow import app

def ask_agent(question: str):
    """
    Helper function to run the compiled Agentic RAG workflow for a given question.
    """
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
    }

    result = app.invoke(initial_state)

    print("\n" + "=" * 90)
    print("QUESTION:")
    print(question)
    print("\nSOURCE USED:")
    print(result.get("source_used", "unknown"))
    print("\nFINAL ANSWER:")
    print(result.get("answer", ""))
    print("=" * 90 + "\n")

    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ask Agentic RAG a question.")
    parser.add_argument("--query", "-q", type=str, default="Hello, how are you?", help="Question to ask.")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("PART 6: HELPER FUNCTION EXECUTION")
    print("=" * 60)
    ask_agent(args.query)

