"""RAG Service — ChromaDB vector store with Gemini embeddings."""

import hashlib
import logging
import os
import uuid
from pathlib import Path

import chromadb
from google import genai
from google.genai import types
from pypdf import PdfReader

from .config import settings

logger = logging.getLogger("nova-agent")


class RAGService:
    def __init__(self):
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._memory_collection: chromadb.Collection | None = None
        self._genai_client: genai.Client | None = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._genai_client = genai.Client(api_key=settings.gemini_api_key)
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name, metadata={"hnsw:space": "cosine"},
        )
        self._memory_collection = self._client.get_or_create_collection(
            name="nova_memory", metadata={"hnsw:space": "cosine"},
        )
        self._initialized = True
        logger.info(
            "[RAG] ChromaDB ready: knowledge=%d docs, memory=%d docs",
            self._collection.count(), self._memory_collection.count(),
        )

    # ── Text extraction ───────────────────────────────────────────────────────

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        reader = PdfReader(pdf_path)
        pages = [p.extract_text() for p in reader.pages if p.extract_text()]
        return "\n\n".join(p.strip() for p in pages)

    def _read_markdown(self, md_path: str) -> str:
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()

    # ── Chunking ──────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str) -> list[str]:
        size, overlap = settings.rag_chunk_size, settings.rag_chunk_overlap
        chunks, start = [], 0
        while start < len(text):
            chunk = text[start : start + size].strip()
            if chunk:
                chunks.append(chunk)
            start += size - overlap
        return chunks

    # ── Embeddings ────────────────────────────────────────────────────────────

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            result = self._genai_client.models.embed_content(
                model=f"models/{settings.gemini_embedding_model}",
                contents=batch,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            embeddings.extend([e.values for e in result.embeddings])
        return embeddings

    def _embed_query(self, query: str) -> list[float]:
        result = self._genai_client.models.embed_content(
            model=f"models/{settings.gemini_embedding_model}",
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def ingest_pdf(self, pdf_path: str, filename: str, doc_id: str, user_id: str) -> int:
        self.initialize()
        text = self._extract_text_from_pdf(pdf_path)
        if not text.strip():
            return 0
        return self._ingest_text(text, filename, doc_id, user_id=user_id)

    async def ingest_markdown(self, md_path: str, filename: str, doc_id: str, content_hash: str = "", user_id: str = "") -> int:
        self.initialize()
        text = self._read_markdown(md_path)
        if not text.strip():
            return 0
        return self._ingest_text(text, filename, doc_id, content_hash=content_hash, user_id=user_id)

    def _ingest_text(self, text: str, filename: str, doc_id: str, content_hash: str = "", user_id: str = "") -> int:
        chunks = self._chunk_text(text)
        if not chunks:
            return 0
        embeddings = self._embed_texts(chunks)
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"source": filename, "doc_id": doc_id, "chunk_index": i, "content_hash": content_hash, "user_id": user_id}
            for i in range(len(chunks))
        ]
        self._collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        logger.info("[RAG] Ingested '%s': %d chunks (user=%s)", filename, len(chunks), user_id or "global")
        return len(chunks)

    async def ingest_knowledge_base_dir(self) -> int:
        self.initialize()
        kb_dir = settings.knowledge_base_dir
        if not os.path.isdir(kb_dir):
            return 0
        total = 0
        for fname in os.listdir(kb_dir):
            fpath = os.path.join(kb_dir, fname)
            if not os.path.isfile(fpath) or not fname.lower().endswith((".md", ".txt")):
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            content_hash = hashlib.md5(content.encode()).hexdigest()
            existing = self._collection.get(where={"source": fname}, include=["metadatas"])
            if existing["ids"]:
                old_hash = existing["metadatas"][0].get("content_hash", "") if existing["metadatas"] else ""
                if old_hash == content_hash:
                    continue
                self._collection.delete(ids=existing["ids"])
            doc_id = str(uuid.uuid4())
            if fname.lower().endswith(".md"):
                count = await self.ingest_markdown(fpath, fname, doc_id, content_hash=content_hash)
            else:
                count = self._ingest_text(content, fname, doc_id, content_hash=content_hash) if content.strip() else 0
            total += count
        return total

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(self, query: str, user_id: str, top_k: int | None = None) -> list[dict]:
        """Search knowledge base + user-uploaded docs. Global docs (user_id='') are always visible."""
        self.initialize()
        if self._collection.count() == 0:
            return []
        k = top_k or settings.rag_top_k
        qe = self._embed_query(query)
        # Fetch more results then filter, since ChromaDB $or is limited
        results = self._collection.query(
            query_embeddings=[qe],
            n_results=min(k * 4, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        out = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0],
            ):
                doc_user = meta.get("user_id", "")
                # Allow: global (empty user_id) or belonging to this user
                if doc_user == "" or doc_user == user_id:
                    out.append({"content": doc, "source": meta.get("source", "unknown"), "score": 1 - dist})
                if len(out) >= k:
                    break
        return out

    # ── Memory ────────────────────────────────────────────────────────────────

    async def search_memory(self, query: str, user_id: str, top_k: int = 5) -> list[dict]:
        self.initialize()
        if self._memory_collection.count() == 0:
            return []
        qe = self._embed_query(query)
        results = self._memory_collection.query(
            query_embeddings=[qe],
            n_results=min(top_k, self._memory_collection.count()),
            where={"user_id": user_id},
            include=["documents", "metadatas", "distances"],
        )
        out = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0],
            ):
                out.append({"content": doc, "source": "memory", "score": 1 - dist})
        return out

    async def save_memory(self, user_id: str, insight: str) -> None:
        self.initialize()
        if not insight.strip():
            return
        embedding = self._embed_texts([insight])[0]
        self._memory_collection.add(
            ids=[str(uuid.uuid4())], embeddings=[embedding], documents=[insight],
            metadatas=[{"user_id": user_id, "type": "conversation_insight"}],
        )

    def delete_document_chunks(self, doc_id: str) -> None:
        self.initialize()
        results = self._collection.get(where={"doc_id": doc_id}, include=[])
        if results["ids"]:
            self._collection.delete(ids=results["ids"])

    def get_document_chunks(self, doc_id: str, max_chunks: int = 12) -> list[dict]:
        """Return stored chunks for a given ChromaDB doc_id."""
        self.initialize()
        results = self._collection.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas"],
        )
        chunks = []
        for doc, meta in zip(results.get("documents") or [], results.get("metadatas") or []):
            chunks.append({"content": doc, "source": meta.get("source", "unknown")})
            if len(chunks) >= max_chunks:
                break
        return chunks


rag_service = RAGService()
