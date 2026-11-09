import os
import time
from typing import List, Optional
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings

def get_embeddings():
    """Initializes embeddings based on environment configuration."""
    # Check if OpenAI is explicitly requested and key is present
    if settings.OPENAI_API_KEY and "text-embedding" in settings.EMBEDDING_MODEL.lower():
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    
    # Default to fast, local, high-performance HuggingFace embeddings (384-dim)
    from langchain_huggingface import HuggingFaceEmbeddings
    try:
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception:
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            encode_kwargs={"normalize_embeddings": True},
        )

class VectorStoreManager:
    def __init__(self):
        self.embeddings = get_embeddings()
        self.index_name = settings.PINECONE_INDEX_NAME
        self.namespace = settings.PINECONE_NAMESPACE
        self._pc: Optional[Pinecone] = None
        self._vectorstore: Optional[PineconeVectorStore] = None
        self._retriever = None

    @property
    def pc(self) -> Pinecone:
        if self._pc is None:
            if not settings.PINECONE_API_KEY:
                raise ValueError("PINECONE_API_KEY is not set in environment or .env")
            self._pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        return self._pc

    def ensure_index_exists(self, dimension: int = 384):
        """Ensures the Pinecone index exists, creating a serverless index if absent."""
        existing_indexes = [idx["name"] for idx in self.pc.list_indexes()]
        if self.index_name not in existing_indexes:
            print(f"[Pinecone] Creating index '{self.index_name}' ({dimension} dims, cosine)...")
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            while not self.pc.describe_index(self.index_name).status["ready"]:
                time.sleep(1)
            print(f"[Pinecone] Index '{self.index_name}' is ready.")

    def get_vectorstore(self) -> PineconeVectorStore:
        """Returns initialized PineconeVectorStore."""
        if self._vectorstore is None:
            index = self.pc.Index(self.index_name)
            self._vectorstore = PineconeVectorStore(
                index=index,
                embedding=self.embeddings,
                namespace=self.namespace,
            )
        return self._vectorstore

    def get_retriever(self, k: Optional[int] = None):
        """Returns LangChain retriever configured for the enterprise knowledge base."""
        top_k = k or settings.TOP_K_RETRIEVAL
        vstore = self.get_vectorstore()
        return vstore.as_retriever(
            search_kwargs={
                "k": top_k,
                "namespace": self.namespace,
            }
        )

    def add_documents(self, documents: List[Document], batch_size: int = 100) -> int:
        """Upserts documents into the Pinecone index in batches."""
        if not documents:
            return 0
        vstore = self.get_vectorstore()
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            vstore.add_documents(batch)
            total += len(batch)
            print(f"[Pinecone] Ingested {total}/{len(documents)} chunks...")
        return total

    def get_index_stats(self):
        """Returns metadata stats for the current index and namespace."""
        index = self.pc.Index(self.index_name)
        return index.describe_index_stats()


vector_manager = VectorStoreManager()
