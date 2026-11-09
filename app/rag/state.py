from typing import List, Literal, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Structured Decision Schemas (for LLM Structured Outputs)
# ---------------------------------------------------------------------------

class RouteDecision(BaseModel):
    """Routing decision determining whether question requires HR policies or direct conversation."""
    route: Literal["kb", "direct"] = Field(
        description="Use 'kb' for questions regarding HR policies, leave, benefits, payroll, onboarding, or workplace rules. Use 'direct' only for greetings, thanks, or simple conversational chit-chat."
    )
    confidence: Optional[float] = Field(default=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: Optional[str] = Field(default="", description="Brief justification for the chosen route")


class EvidenceGrade(BaseModel):
    """Grading evaluation of whether retrieved evidence is sufficient to answer the question."""
    grade: Literal["good", "weak"] = Field(
        description="'good' means the evidence directly answers the question with sufficient detail. 'weak' means insufficient, missing, or irrelevant information."
    )
    explanation: Optional[str] = Field(default="", description="Reason for the grade")


# ---------------------------------------------------------------------------
# Agentic RAG Shared State Definition
# ---------------------------------------------------------------------------

class Citation(TypedDict, total=False):
    source: str
    title: str
    url: Optional[str]
    snippet: str


class TraceStep(TypedDict, total=False):
    node: str
    status: str
    details: str
    timestamp: str


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
    citations: List[Citation]
    trace: List[TraceStep]

