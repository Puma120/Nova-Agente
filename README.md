# Nova Agent

FastAPI + React/Vite AI assistant with RAG, persistent memory, vision, and dual-agent support (Nova + Chefsito via LangGraph).

---

## Architecture

```
nova-agent/
  backend/                   # FastAPI app (Python 3.11+)
    app/
      main.py                # All HTTP endpoints, startup, CORS
      config.py              # Pydantic Settings — reads from .env
      db.py                  # SQLAlchemy async engine + init_db()
      models.py              # ORM: User, Conversation, Message, Document
      schemas.py             # Pydantic request/response schemas
      auth.py                # JWT (HS256) + bcrypt
      repo.py                # Async CRUD layer
      rag_service.py         # ChromaDB client, embeddings, PDF/MD ingestion
      gemini_service.py      # Nova: LangChain chat, tool loop, RAG, vision
      chef_agent.py          # Chefsito: LangGraph graph, long-term store
      memory_service.py      # Per-user file-based persistent memory (JSON)
    knowledge_base/          # .md/.txt files auto-ingested on startup
    pdf_uploads/             # Per-user uploads (subfolder per user UUID)
    chroma_data/             # ChromaDB persistent vectors
    user_memory/             # Per-user memory JSON files
    nova.db                  # SQLite (auto-created)
    chef_store.db            # Chefsito LangGraph store (auto-created)
    langgraph.json           # LangGraph Studio config
  frontend/                  # React 18 + Vite + Tailwind
    src/
      App.jsx                # Full SPA: auth, sidebar, chat, docs panel
      api.js                 # Typed fetch wrappers for all endpoints
  start.ps1                  # One-shot launcher (Windows)
```

---

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI 0.135, Python 3.11, uvicorn |
| Database | SQLite via SQLAlchemy async (aiosqlite) |
| Vector store | ChromaDB 1.5 (persistent, local) |
| Embeddings | Google `gemini-embedding-001` |
| LLM — primary | `ChatOllama` (qwen3.5:9b at localhost:11434) |
| LLM — fallback | `ChatGoogleGenerativeAI` (configurable Gemini model) |
| Agent framework | LangChain (Nova) + LangGraph (Chefsito) |
| Auth | JWT HS256 + bcrypt |
| Frontend | React 18, Vite, Tailwind CSS |
| Observability | LangSmith (optional, disabled by default) |

---

## How it works

### Model selection (Ollama-first)

On every cold start, both agents ping `http://localhost:11434/api/tags` with a 2-second timeout and check whether `qwen3.5:9b` is in the list. If yes, `ChatOllama` is used; otherwise it falls back to `ChatGoogleGenerativeAI`. The resolved model is cached for the process lifetime.

### RAG pipeline

1. At startup, all files in `knowledge_base/` are ingested into ChromaDB with `user_id=""` (global, visible to all users).
2. User-uploaded files go to `pdf_uploads/<user_id>/` and are ingested with `user_id=<uuid>`.
3. On every chat message, `rag_service.search()` queries ChromaDB with the user's message embedding and returns chunks where `user_id == ""` OR `user_id == current_user`.
4. Results are injected into the system prompt under `--- BASE DE CONOCIMIENTO ---`.
5. When a file is uploaded directly from chat (`POST /chat/document`), its chunks are fetched by `doc_id` (no semantic search) and prepended as `extra_rag_context` so Nova sees them immediately regardless of query relevance.

### Nova (gemini_service.py)

- LangChain message list: `SystemMessage` (filled system prompt) + history (last 20 turns) + current `HumanMessage`.
- Tools: `EstablecerEmocion`, `GuardarEnMemoria`, `EliminarDeMemoria` — Pydantic BaseModel schemas bound via `.bind_tools()`.
- Tool loop: up to 5 rounds of `model.ainvoke()` → `ToolMessage` responses until no tool calls remain.
- System prompt injects: `{file_memory}` (JSON memory file), `{memory_context}` (semantic memory search), `{user_documents}` (list of all uploaded filenames), `{rag_context}` (RAG chunks).

### Chefsito (chef_agent.py)

- LangGraph `StateGraph` with a single `chat` node.
- Long-term memory via `SqliteChefStore` (stdlib sqlite3, `chef_store.db`) — stores per-user preferences and conversation history using `trustcall`.
- RAG context fetched before entering the graph and passed via `config["configurable"]["rag_context"]`.
- `_in_studio` flag (`__name__ != "app.chef_agent"`) disables the custom store when running under LangGraph Studio (which rejects non-standard store types).

### Auth

All endpoints under `/api/` (except `/register` and `/token`) require `Authorization: Bearer <jwt>`. Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).

---

## Setup

### Requirements

- Python 3.11+
- Node.js 18+
- Google Gemini API key — [aistudio.google.com](https://aistudio.google.com/)
- (Optional) [Ollama](https://ollama.com/) with `qwen3.5:9b` pulled

### Backend

```bash
cd backend
python -m venv ../venv
# Windows
..\venv\Scripts\activate
# Linux/Mac
source ../venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set GEMINI_API_KEY and JWT_SECRET_KEY

uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5174  (proxies /api → localhost:8010)
```

### Windows one-shot

```powershell
.\start.ps1           # backend + frontend
.\start.ps1 -Studio   # + LangGraph Studio on :2024
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/register` | Create account |
| `POST` | `/api/token` | Login → JWT |
| `GET` | `/api/me` | Current user |
| `POST` | `/api/chat` | Send message (JSON) |
| `POST` | `/api/chat/document` | Upload file + send message (multipart) |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Conversation + messages |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |
| `POST` | `/api/documents` | Upload document to RAG |
| `GET` | `/api/documents` | List user documents |
| `DELETE` | `/api/documents/{id}` | Delete document + chunks |
| `POST` | `/api/rag/search` | Raw RAG search |
| `POST` | `/api/vision/interpret` | Analyze image (base64) |

### POST /api/chat — request body

```json
{
  "message": "string",
  "conversation_id": "uuid | null",
  "image_base64": "string | null",
  "mode": "nova | chef"
}
```

### POST /api/chat/document — multipart form

| Field | Type | Required |
|---|---|---|
| `file` | `.pdf / .md / .txt` | yes |
| `message` | string | no |
| `conversation_id` | uuid | no |
| `mode` | `nova \| chef` | no (default `nova`) |

---

## Conversation modes

Each conversation has a `mode` column (`nova` or `chef`) set at creation and locked for its lifetime. The frontend shows a locked pill once a conversation has started and routes messages to the correct backend agent.

---

## LangGraph Studio

```bash
# From repo root (venv active):
cd backend
langgraph dev --port 2024
# Open https://smith.langchain.com/studio → connect to localhost:2024
```

Graph: `chefsito` → `backend/app/chef_agent.py:chef_graph`

The agent auto-detects Studio mode and passes `store=None` to avoid store compatibility errors.

---

## Environment variables

See `backend/.env.example` for all variables with descriptions. Required:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key |
| `JWT_SECRET_KEY` | Random secret, min 32 chars |

Everything else has working defaults.

