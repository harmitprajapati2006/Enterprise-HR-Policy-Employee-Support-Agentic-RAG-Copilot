import os
import sys
import subprocess

# Auto-relaunch inside local virtual environment if invoked globally
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CURRENT_DIR, "venv", "Scripts", "python.exe")
if os.path.exists(VENV_PYTHON) and os.path.normcase(sys.executable) != os.path.normcase(VENV_PYTHON):
    result = subprocess.run([VENV_PYTHON] + sys.argv, check=False)
    sys.exit(result.returncode)

import time
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Section 2: Configure API Keys
# ---------------------------------------------------------------------------
ENV_FILE = os.path.join(CURRENT_DIR, ".env")
load_dotenv(ENV_FILE)

assert os.getenv("PINECONE_API_KEY"), "PINECONE_API_KEY is not set in environment or .env"

# ---------------------------------------------------------------------------
# Section 5: Create Free Local Embeddings
# ---------------------------------------------------------------------------
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True},
)

# ---------------------------------------------------------------------------
# Section 6: Create the Pinecone Vector Database
# ---------------------------------------------------------------------------
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

INDEX_NAME = "industry-agentic-rag-kb"
NAMESPACE = "langgraph-agentic-rag"

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

if INDEX_NAME not in existing_indexes:
    print(f"Creating Pinecone index '{INDEX_NAME}' (384 dimensions, cosine)...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1",
        ),
    )
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(1)
    print("Pinecone index ready:", INDEX_NAME)

    # Section 3 & 4: Load & Split Documents only when populating new index
    from langchain_community.document_loaders import WebBaseLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    SOURCE_URL = "https://docs.langchain.com/oss/python/langgraph/agentic-rag"
    print(f"Loading documents from {SOURCE_URL}...")
    loader = WebBaseLoader(
        web_paths=(SOURCE_URL,),
        requests_kwargs={"headers": {"User-Agent": "Mozilla/5.0 Agentic-RAG-Industry-Demo"}},
    )
    raw_docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, add_start_index=True)
    chunks = splitter.split_documents(raw_docs)
    print(f"Split into {len(chunks)} chunks.")

    print(f"Uploading chunks to Pinecone namespace '{NAMESPACE}'...")
    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=INDEX_NAME,
        namespace=NAMESPACE,
    )
else:
    index = pc.Index(INDEX_NAME)
    vectorstore = PineconeVectorStore(
        index=index,
        embedding=embeddings,
        namespace=NAMESPACE,
    )

retriever = vectorstore.as_retriever(
    search_kwargs={
        "k": 4,
        "namespace": NAMESPACE,
    }
)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PART 1: VECTOR DATABASE & RETRIEVER SETUP")
    print("=" * 60)
    print("PINECONE_API_KEY configured:", bool(os.getenv("PINECONE_API_KEY")))
    sample_vec = embeddings.embed_query("What is Agentic RAG?")
    print("Embedding dimensions:", len(sample_vec))
    print("Connected to Pinecone index:", INDEX_NAME)
    print("Namespace:", NAMESPACE)
    stats = pc.Index(INDEX_NAME).describe_index_stats()
    print("Index stats:", stats)
    print("Retriever ready:", retriever is not None)
    print("=" * 60)

