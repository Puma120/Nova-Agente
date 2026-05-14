# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
source ../venv/bin/activate          # Linux/Mac
# ..\venv\Scripts\activate           # Windows

uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

There is no test suite. Use `GET /health` to verify the backend is running.

### Frontend

```bash
cd frontend
npm install
npm run dev       # → http://localhost:5174
npm run build
```

### LangGraph Studio (optional)

```bash
cd backend
langgraph dev --port 2024
# Connect at https://smith.langchain.com/studio → localhost:2024
```

### Windows one-shot

```powershell
.\start.ps1           # backend + frontend
.\start.ps1 -Studio   # + LangGraph Studio
```

## Architecture

**Backend** — FastAPI (Python 3.11+), async throughout, running on port 8010.  
**Frontend** — React 19 + Vite + Tailwind CSS, running on port 5174, proxies `/api/*` → `http://localhost:8010/*` (strips the `/api` prefix).

### API routes

All endpoints are at the **root** level (no `/api` prefix in FastAPI). The Vite proxy adds/strips that prefix. Auth endpoints are under `/auth/`, everything else is top-level: `/chat`, `/chat/stream`, `/chat/document`, `/conversations`, `/documents`, `/rag/search`, `/vision/interpret`, `/integrations/google/*`, `/health`.

### Nova agent (LangGraph)

Nova is a single LangGraph agent — `nova_agent.py` builds a `StateGraph` with an `agente` node (LLM bound to tools) and a `tools` node (`ToolNode`), looping until the LLM answers without tool calls. Tools live in `nova_tools.py`: `establecer_emocion`, `buscar_en_conocimiento` (RAG as a visible step), `guardar_en_memoria` / `eliminar_de_memoria`, `guardar_preferencia_culinaria` / `guardar_receta` (the former Chefsito skill, folded in), `consultar_calendario` / `crear_evento_calendario`, `finalizar_onboarding`.

- `astream_nova()` — runs the graph via `astream_events` and yields normalized events (`step` / `token` / `emotion` / `sources` / `done`). Backs `POST /chat/stream` (SSE).
- `chat_nova()` — non-streaming wrapper over `astream_nova()`, backs `POST /chat` and `/chat/document`.
- `build_messages()` — assembles the system prompt (file memory, semantic memory, docs list, current datetime, optional onboarding directive) + history + the new turn.

The `conversations.mode` column still exists but is inert (always `nova`) — there is no dual-agent routing anymore.

### LLM provider layer

All LLM initialization is centralized in `llm_provider.py`. Set `LLM_PROVIDER` in `.env` to swap providers without touching agent code:

| `LLM_PROVIDER` | Chat model | Embedding model |
|---|---|---|
| `openai` (default) | `ChatOpenAI` (`gpt-4o-mini`) | OpenAI `text-embedding-3-small` |
| `gemini` | `ChatGoogleGenerativeAI` | Gemini `gemini-embedding-001` |
| `ollama` | `ChatOllama` | Gemini `gemini-embedding-001` |

- `get_llm()` — returns a `BaseChatModel`, cached via `lru_cache`. Used by the agent via `.bind_tools()` / `.ainvoke()`.
- `embed_texts()` / `embed_query()` — used by `rag_service.py` for ingestion and search.

### RAG pipeline (Pinecone)

`rag_service.py` uses a single Pinecone index with two namespaces: `knowledge` and `memory`.

- **Global knowledge**: files in `knowledge_base/` are auto-ingested at startup with `user_id=""` (deduped by an md5 `content_hash`).
- **User uploads**: stored under `pdf_uploads/<user_id>/`, ingested with `user_id=<uuid>`. Supported formats: `.pdf`, `.md`, `.txt`.
- **Search**: native Pinecone metadata filter `user_id ∈ {"", current_user}`.
- **Immediate context**: documents uploaded via `POST /chat/document` have their chunks fetched by `doc_id` and prepended as `extra_rag_context`.

**Important**: a Pinecone index has a fixed dimension set at creation — it must match the embedding model (OpenAI=1536, Gemini/Ollama=768, via `settings.embedding_dimension`). Switching `LLM_PROVIDER` across that boundary requires a new `PINECONE_INDEX_NAME`.

### Memory & onboarding

Per-user persistent memory ("digital twin") is stored as Markdown files in `user_memory/` (see `memory_service.py`). Nova reads the full file into `{file_memory}` in its system prompt and mutates it via the memory tools. New users have `users.is_onboarded = false`; while false, the system prompt includes an onboarding directive and Nova calls `finalizar_onboarding` once it has gotten to know the user.

### Google Calendar integration

`google_calendar.py` handles the OAuth2 flow; tokens are stored per-user in the `google_credentials` table. Endpoints: `/integrations/google/connect` (returns consent URL), `/integrations/google/callback` (stores token, `state` carries the user_id), `/integrations/google/status`, `DELETE /integrations/google`. The `consultar_calendario` / `crear_evento_calendario` tools read those credentials.

## Environment

Copy `backend/.env.example` to `backend/.env`. Required variables depend on the active provider:

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `openai` (default) \| `gemini` \| `ollama` |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai` |
| `GEMINI_API_KEY` | Required when `LLM_PROVIDER=gemini` (also needed for embeddings with `ollama`) |
| `PINECONE_API_KEY` | Required — vector store |
| `PINECONE_INDEX_NAME` | Index name (auto-created on startup with the right dimension) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional — enables the Google Calendar integration |
| `JWT_SECRET_KEY` | Random secret, min 32 chars |

All local storage paths (`DATABASE_URL`, `PDF_UPLOAD_DIR`, `KNOWLEDGE_BASE_DIR`, `USER_MEMORY_DIR`) default to directories under `backend/` and are created automatically on startup.
