import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.rag.workflow import ask_hr_copilot
from app.rag.vectorstore import vector_manager
from app.services.ingestion import ingestion_service
from app.services.audit import audit_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Employee question or prompt")
    session_id: Optional[str] = Field(default="web-session", description="Unique session identifier")


class CitationModel(BaseModel):
    source: str
    title: str
    url: Optional[str] = None
    snippet: str


class TraceItemModel(BaseModel):
    node: str
    status: str
    details: str
    timestamp: str


class ChatResponse(BaseModel):
    question: str
    answer: str
    source_used: str
    kb_grade: Optional[str] = ""
    web_grade: Optional[str] = ""
    retry_count: int = 0
    citations: List[CitationModel] = []
    trace: List[TraceItemModel] = []
    session_id: str


class UploadResponse(BaseModel):
    filename: str
    file_type: str
    chunks_indexed: int
    namespace: str
    status: str


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Executes the full LangGraph Agentic RAG workflow:
    Route -> Retrieve -> Grade -> Web Search -> Retry -> Generate Answer.
    """
    try:
        result = ask_hr_copilot(request.question)
        
        # Save to SQLite audit log
        audit_service.log_interaction(
            question=request.question,
            answer=result.get("answer", ""),
            source_used=result.get("source_used", "unknown"),
            kb_grade=result.get("kb_grade", ""),
            web_grade=result.get("web_grade", ""),
            retry_count=result.get("retry_count", 0),
            citations=result.get("citations", []),
            trace=result.get("trace", []),
            session_id=request.session_id,
        )

        return ChatResponse(
            question=request.question,
            answer=result.get("answer", "No answer could be generated."),
            source_used=result.get("source_used", "unknown"),
            kb_grade=result.get("kb_grade", ""),
            web_grade=result.get("web_grade", ""),
            retry_count=result.get("retry_count", 0),
            citations=result.get("citations", []),
            trace=result.get("trace", []),
            session_id=request.session_id or "web-session",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and index a new HR document (PDF, TXT, MD, DOCX) directly into Pinecone.
    """
    allowed_extensions = {".pdf", ".txt", ".md", ".docx", ".markdown"}
    ext = Path(file.filename).suffix.lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save to uploads directory
    target_path = settings.UPLOADS_DIR / file.filename
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse & split
        chunks = ingestion_service.load_and_split_file(target_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="Document was empty or could not be parsed.")

        # Ingest into Pinecone
        vector_manager.ensure_index_exists(dimension=settings.EMBEDDING_DIMENSION)
        total_ingested = vector_manager.add_documents(chunks)

        return UploadResponse(
            filename=file.filename,
            file_type=ext.lstrip("."),
            chunks_indexed=total_ingested,
            namespace=settings.PINECONE_NAMESPACE,
            status="success",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload & indexing failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for API, Pinecone, and configured models."""
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "tavily_configured": bool(settings.TAVILY_API_KEY),
        "pinecone_configured": bool(settings.PINECONE_API_KEY),
        "pinecone_index": settings.PINECONE_INDEX_NAME,
        "pinecone_namespace": settings.PINECONE_NAMESPACE,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


@router.get("/audit")
async def get_audit_logs(limit: int = 20):
    """Fetch recent execution traces and questions from SQLite audit logs."""
    return audit_service.get_recent_logs(limit=limit)


@router.get("/stats")
async def get_system_stats():
    """Returns analytics on query resolution paths and accuracy."""
    return audit_service.get_stats()


@router.get("/documents")
async def list_documents():
    """Lists all sample policy documents and user-uploaded files."""
    sample_docs = []
    if settings.DATA_DIR.exists():
        for p in sorted(settings.DATA_DIR.iterdir()):
            if p.is_file():
                sample_docs.append({
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "type": "sample_kb",
                })
                
    uploaded_docs = []
    if settings.UPLOADS_DIR.exists():
        for p in sorted(settings.UPLOADS_DIR.iterdir()):
            if p.is_file() and p.name != ".gitkeep":
                uploaded_docs.append({
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "type": "uploaded",
                })

    return {
        "sample_kb_count": len(sample_docs),
        "uploaded_count": len(uploaded_docs),
        "documents": sample_docs + uploaded_docs,
    }

