import os
import sys
import argparse
from pathlib import Path

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = CURRENT_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    import subprocess
    result = subprocess.run([str(VENV_PYTHON)] + sys.argv, check=False)
    sys.exit(result.returncode)

import uvicorn
from dotenv import load_dotenv

# Load environment configuration
load_dotenv(CURRENT_DIR / ".env")
from app.core.config import settings

def main():
    parser = argparse.ArgumentParser(description="Start Enterprise HR Policy Agentic RAG Copilot Server.")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host address to bind.")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to listen on.")
    parser.add_argument("--reload", action="store_true", default=settings.DEBUG, help="Enable live auto-reload.")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🏢 ENTERPRISE HR POLICY & EMPLOYEE SUPPORT AGENTIC RAG COPILOT")
    print("=" * 70)
    print(f"Server URL:        http://localhost:{args.port}")
    print(f"API Docs:          http://localhost:{args.port}/docs")
    print(f"Pinecone Index:    {settings.PINECONE_INDEX_NAME}")
    print(f"Namespace:         {settings.PINECONE_NAMESPACE}")
    print(f"LLM Model:         {settings.GROQ_MODEL}")
    print(f"Embeddings:        {settings.EMBEDDING_MODEL}")
    print("=" * 70 + "\n")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )

if __name__ == "__main__":
    main()

