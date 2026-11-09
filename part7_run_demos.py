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
# Sections 24 to 27: Run Demos 1 through 4
# ---------------------------------------------------------------------------
from part6_helper_function import ask_agent

def run_all_demos():
    print("\n" + "=" * 90)
    print("PART 7: RUN ALL 4 DEMOS")
    print("=" * 90)

    print("\n" + "-" * 50)
    print("## 24. Demo 1 — Answer from Private KB")
    print("-" * 50)
    ask_agent("In Agentic RAG, what happens when retrieved documents are not relevant?")

    print("\n" + "-" * 50)
    print("## 25. Demo 2 — Web Search Fallback")
    print("-" * 50)
    ask_agent("What is Tavily Search and why is it useful for AI agents and RAG workflows?")

    print("\n" + "-" * 50)
    print("## 26. Demo 3 — Direct Answer")
    print("-" * 50)
    ask_agent("Hello, how are you?")

    print("\n" + "-" * 50)
    print("## 27. Demo 4 — Ask a Current / External Question")
    print("-" * 50)
    ask_agent("What is the current LangChain Tavily package used for Python web search integration?")

if __name__ == "__main__":
    run_all_demos()

