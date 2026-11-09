import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-grade Forward Deployed Engineer (FDE) Agentic RAG assistant for Human Resources and employee inquiries.",
)

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Template configuration
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Include API Router
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root(request: Request):
    """Serve the Enterprise Copilot Web Dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "groq_model": settings.GROQ_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "pinecone_index": settings.PINECONE_INDEX_NAME,
            "pinecone_namespace": settings.PINECONE_NAMESPACE,
        },
    )


@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print(f"🚀 {settings.PROJECT_NAME} (v{settings.VERSION}) Starting up...")
    print(f"📍 Pinecone Index: {settings.PINECONE_INDEX_NAME} (ns: {settings.PINECONE_NAMESPACE})")
    print(f"📍 LLM Model: {settings.GROQ_MODEL}")
    print(f"📍 Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"📍 Knowledge Base Directory: {settings.DATA_DIR}")
    print("=" * 60)
