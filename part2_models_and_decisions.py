import os
import sys
import subprocess

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CURRENT_DIR, "venv", "Scripts", "python.exe")
if os.path.exists(VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(VENV_PYTHON):
    result = subprocess.run([VENV_PYTHON] + sys.argv, check=False)
    sys.exit(result.returncode)

from dotenv import load_dotenv
ENV_FILE = os.path.join(CURRENT_DIR, ".env")
load_dotenv(ENV_FILE)

assert os.getenv("GROQ_API_KEY"), "GROQ_API_KEY is not set in environment or .env"
assert os.getenv("TAVILY_API_KEY"), "TAVILY_API_KEY is not set in environment or .env"

try:
    from typing import List, Literal, Optional, TypedDict
except ImportError:
    from typing import List, Literal, Optional
    from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from langchain_core.documents import Document

# ---------------------------------------------------------------------------
# Section 7: Import Retriever from Part 1
# ---------------------------------------------------------------------------
from part1_vector_db import retriever

# ---------------------------------------------------------------------------
# Section 8: Initialize Groq LLM
# ---------------------------------------------------------------------------
from langchain_groq import ChatGroq

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
)

# ---------------------------------------------------------------------------
# Section 9: Initialize Tavily Web Search
# ---------------------------------------------------------------------------
from langchain_tavily import TavilySearch

web_search = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=True,
    include_raw_content=False,
)

# ---------------------------------------------------------------------------
# Section 10: Define Structured Decisions & State
# ---------------------------------------------------------------------------
class RouteDecision(BaseModel):
    route: Literal["kb", "direct"] = Field(
        description="Use kb for questions needing Agentic RAG docs; direct for greetings/simple chat."
    )

class EvidenceGrade(BaseModel):
    grade: Literal["good", "weak"] = Field(
        description="good means evidence can answer the question; weak means not enough evidence."
    )

class AgentState(TypedDict):
    question: str
    current_query: str
    kb_docs: List[Document]
    web_results: str
    kb_grade: str
    web_grade: str
    answer: str
    source_used: str
    retry_count: int

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PART 2: MODELS, SEARCH TOOLS & STRUCTURED SCHEMAS")
    print("=" * 60)
    print("GROQ_API_KEY configured:", bool(os.getenv("GROQ_API_KEY")))
    print("TAVILY_API_KEY configured:", bool(os.getenv("TAVILY_API_KEY")))
    
    print("\nTesting Groq LLM...")
    llm_test = llm.invoke("Explain Agentic RAG in one sentence.")
    print("Groq output:", llm_test.content)

    print("\nTesting Private KB Retrieval (Section 7)...")
    test_question = "What happens if retrieved documents are not relevant in Agentic RAG?"
    kb_docs = retriever.invoke(test_question)
    print(f"Retrieved {len(kb_docs)} chunks for query: '{test_question}'")
    for i, doc in enumerate(kb_docs[:2], 1):
        print(f"\n--- Chunk {i} ---")
        print(doc.page_content[:200])

    print("\nTavily search ready:", web_search is not None)
    print("Structured decision classes ready: RouteDecision, EvidenceGrade, AgentState")
    print("=" * 60)

