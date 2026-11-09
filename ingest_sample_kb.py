import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = CURRENT_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    import subprocess
    result = subprocess.run([str(VENV_PYTHON)] + sys.argv, check=False)
    sys.exit(result.returncode)

load_dotenv(CURRENT_DIR / ".env")

from app.core.config import settings
from app.services.ingestion import ingestion_service
from app.rag.vectorstore import vector_manager


def ingest_knowledge_base(data_dir: Path = None):
    target_dir = data_dir or settings.DATA_DIR
    print("\n" + "=" * 70)
    print("ENTERPRISE HR POLICY AGENTIC RAG — KNOWLEDGE BASE INGESTION")
    print("=" * 70)
    print(f"Target Directory: {target_dir}")
    print(f"Pinecone Index:   {settings.PINECONE_INDEX_NAME}")
    print(f"Namespace:        {settings.PINECONE_NAMESPACE}")
    print(f"Embedding Model:  {settings.EMBEDDING_MODEL}")
    print("-" * 70)

    # 1. Ensure index exists
    print("Step 1: Checking Pinecone index status...")
    vector_manager.ensure_index_exists(dimension=settings.EMBEDDING_DIMENSION)

    # 2. Load and split documents
    print("Step 2: Parsing HR documents from knowledge base...")
    chunks = ingestion_service.load_and_split_directory(target_dir)
    print(f"Successfully extracted and chunked: {len(chunks)} chunks.")

    if not chunks:
        print("[Warning] No documents found to ingest!")
        return 0

    # Preview sample chunk
    print("\nSample Chunk Preview:")
    print(f"Source: {chunks[0].metadata.get('source')}")
    print(f"Content: {chunks[0].page_content[:200]}...\n")

    # 3. Upsert to Pinecone
    print("Step 3: Generating embeddings and upserting vectors to Pinecone...")
    total_ingested = vector_manager.add_documents(chunks)
    print(f"Successfully uploaded {total_ingested} chunks to namespace '{settings.PINECONE_NAMESPACE}'.")

    # 4. Describe index stats
    print("\nStep 4: Fetching updated Pinecone index statistics...")
    try:
        stats = vector_manager.get_index_stats()
        print(f"Index Statistics: {stats}")
    except Exception as e:
        print(f"Could not fetch stats: {e}")

    print("=" * 70)
    print("Ingestion pipeline completed successfully.")
    print("=" * 70 + "\n")
    return total_ingested


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest HR policy documents into Pinecone vector store.")
    parser.add_argument("--dir", type=str, default=None, help="Custom folder containing documents.")
    args = parser.parse_args()

    custom_dir = Path(args.dir) if args.dir else settings.DATA_DIR
    ingest_knowledge_base(custom_dir)
