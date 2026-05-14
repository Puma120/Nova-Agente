"""RAG Service — Pinecone vector store with pluggable embeddings."""

import hashlib
import logging
import os
import time
import uuid

from pinecone import Pinecone, ServerlessSpec
from pypdf import PdfReader

from .config import settings
from .llm_provider import embed_query, embed_texts

logger = logging.getLogger("nova-agent")

# Single index, two namespaces — replaces the old two ChromaDB collections.
_KB_NS = "knowledge"
_MEM_NS = "memory"


class RAGService:
    def __init__(self):
        self._pc: Pinecone | None = None
        self._index = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        name = settings.pinecone_index_name
        existing = {i["name"] for i in self._pc.list_indexes()}
        if name not in existing:
            logger.info("[RAG] Creating Pinecone index '%s' (dim=%d)", name, settings.embedding_dimension)
            self._pc.create_index(
                name=name,
                dimension=settings.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
            )
            while not self._pc.describe_index(name).status["ready"]:
                time.sleep(1)
        self._index = self._pc.Index(name)
        self._initialized = True
        stats = self._index.describe_index_stats()
        logger.info("[RAG] Pinecone ready: %d vectors total", stats.get("total_vector_count", 0))

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
        return embed_texts(texts)

    def _embed_query(self, query: str) -> list[float]:
        return embed_query(query)

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
        vectors = [
            {
                "id": f"{doc_id}_chunk_{i}",
                "values": embeddings[i],
                "metadata": {
                    "text": chunks[i],
                    "source": filename,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "content_hash": content_hash,
                    "user_id": user_id,
                },
            }
            for i in range(len(chunks))
        ]
        for i in range(0, len(vectors), 100):
            self._index.upsert(vectors=vectors[i : i + 100], namespace=_KB_NS)
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
            # Deterministic doc_id per filename so we can find prior chunks by ID prefix
            doc_id = "kb_" + hashlib.md5(fname.encode()).hexdigest()
            existing_ids = self._list_chunk_ids(doc_id)
            if existing_ids:
                fetched = self._index.fetch(ids=existing_ids[:1], namespace=_KB_NS)
                old_hash = ""
                for v in fetched.vectors.values():
                    old_hash = v.metadata.get("content_hash", "")
                if old_hash == content_hash:
                    continue
                self._index.delete(ids=existing_ids, namespace=_KB_NS)
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
        k = top_k or settings.rag_top_k
        qe = self._embed_query(query)
        results = self._index.query(
            vector=qe,
            top_k=k,
            namespace=_KB_NS,
            filter={"user_id": {"$in": ["", user_id]}},
            include_metadata=True,
        )
        out = []
        for match in results.get("matches", []):
            meta = match.get("metadata") or {}
            out.append({
                "content": meta.get("text", ""),
                "source": meta.get("source", "unknown"),
                "score": match.get("score", 0.0),
            })
        return out

    # ── Memory ────────────────────────────────────────────────────────────────

    async def search_memory(self, query: str, user_id: str, top_k: int = 5) -> list[dict]:
        self.initialize()
        qe = self._embed_query(query)
        results = self._index.query(
            vector=qe,
            top_k=top_k,
            namespace=_MEM_NS,
            filter={"user_id": user_id},
            include_metadata=True,
        )
        out = []
        for match in results.get("matches", []):
            meta = match.get("metadata") or {}
            out.append({
                "content": meta.get("text", ""),
                "source": "memory",
                "score": match.get("score", 0.0),
            })
        return out

    async def save_memory(self, user_id: str, insight: str) -> None:
        self.initialize()
        if not insight.strip():
            return
        embedding = self._embed_texts([insight])[0]
        self._index.upsert(
            vectors=[{
                "id": str(uuid.uuid4()),
                "values": embedding,
                "metadata": {"text": insight, "user_id": user_id, "type": "conversation_insight"},
            }],
            namespace=_MEM_NS,
        )

    def _list_chunk_ids(self, doc_id: str) -> list[str]:
        """Return all vector IDs belonging to a doc_id, via ID-prefix listing.

        ``index.list()`` yields paginated responses that iterate over ``ListItem``
        objects (or plain ID strings on older SDKs) — normalize both to strings.
        """
        ids: list[str] = []
        for page in self._index.list(prefix=f"{doc_id}_chunk_", namespace=_KB_NS):
            for item in page:
                ids.append(getattr(item, "id", item))
        return ids

    def delete_document_chunks(self, doc_id: str) -> None:
        self.initialize()
        ids = self._list_chunk_ids(doc_id)
        if ids:
            self._index.delete(ids=ids, namespace=_KB_NS)

    def get_document_chunks(self, doc_id: str, max_chunks: int = 12) -> list[dict]:
        """Return stored chunks for a given doc_id, ordered by chunk_index."""
        self.initialize()
        ids = self._list_chunk_ids(doc_id)
        if not ids:
            return []
        fetched = self._index.fetch(ids=ids, namespace=_KB_NS)
        rows = []
        for v in fetched.vectors.values():
            meta = v.metadata or {}
            rows.append({
                "content": meta.get("text", ""),
                "source": meta.get("source", "unknown"),
                "chunk_index": int(meta.get("chunk_index", 0)),
            })
        rows.sort(key=lambda r: r["chunk_index"])
        return [{"content": r["content"], "source": r["source"]} for r in rows[:max_chunks]]


rag_service = RAGService()
