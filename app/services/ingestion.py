import os
from pathlib import Path
from typing import List, Union
from datetime import datetime
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None


class DocumentIngestionService:
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 120):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
            add_start_index=True,
        )

    def load_file(self, file_path: Union[str, Path]) -> List[Document]:
        """Loads a single PDF, TXT, MD, or DOCX file into LangChain Documents."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        content = ""
        metadata = {
            "source": path.name,
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "file_type": suffix.lstrip("."),
            "ingested_at": datetime.now().isoformat(),
        }

        if suffix in [".md", ".markdown", ".txt"]:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        elif suffix == ".pdf":
            if PdfReader is None:
                raise ImportError("pypdf is required to parse PDF files. Install with `pip install pypdf`.")
            reader = PdfReader(str(path))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            content = "\n\n".join(pages)

        elif suffix in [".docx", ".doc"]:
            if docx is None:
                raise ImportError("python-docx is required to parse DOCX files. Install with `pip install python-docx`.")
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            content = "\n\n".join(paragraphs)

        else:
            # Fallback to text reading
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        if not content.strip():
            return []

        # Return single document or split chunks
        doc = Document(page_content=content, metadata=metadata)
        return [doc]

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Splits raw documents into semantic chunks with metadata."""
        if not documents:
            return []
        chunks = self.splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
        return chunks

    def load_and_split_file(self, file_path: Union[str, Path]) -> List[Document]:
        """Load and split single file into chunks."""
        raw_docs = self.load_file(file_path)
        return self.split_documents(raw_docs)

    def load_and_split_directory(self, dir_path: Union[str, Path]) -> List[Document]:
        """Loads all supported documents from a directory and splits them."""
        directory = Path(dir_path)
        if not directory.exists() or not directory.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        supported_exts = {".md", ".markdown", ".txt", ".pdf", ".docx"}
        all_chunks: List[Document] = []

        files = sorted([f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in supported_exts])
        for file in files:
            try:
                chunks = self.load_and_split_file(file)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"[Ingestion Error] Skipping {file.name}: {e}")

        return all_chunks


ingestion_service = DocumentIngestionService()

