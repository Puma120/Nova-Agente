# Nova Agent

Nova is a personal AI assistant — a *digital twin* that manages your memory and acts
on your behalf through tools. Built on **LangGraph**, it streams its reasoning live
(you see which tool it's using), does RAG over your own documents, and connects to
Google Calendar. Auth is **Sign in with Google** only.

---

## Architecture

```
Nova-Agente/
  backend/                   # FastAPI app (Python 3.11+), port 8010
    app/
      main.py                # HTTP endpoints, startup, CORS, SSE streaming
      config.py              # Pydantic Settings — reads from .env
      db.py                  # SQLAlchemy async engine + init_db() migrations
      models.py              # ORM: User, Conversation, Message, Document, GoogleCredential
      schemas.py             # Pydantic request/response schemas
      auth.py                # JWT session tokens (HS256)
      repo.py                # Async CRUD layer
      llm_provider.py        # Central LLM/embeddings — openai | gemini | ollama
      rag_service.py         # Pinecone vector store, embeddings, PDF/MD/TXT ingestion
      nova_agent.py          # Nova: LangGraph StateGraph + astream_nova() event stream
      nova_tools.py          # The agent's tools (RAG, memory, cooking, calendar, onboarding)
      google_calendar.py     # Google OAuth login + Calendar API
      vision.py              # Standalone image interpretation
      memory_service.py      # Per-user Markdown memory files
    knowledge_base/          # .md/.txt files auto-ingested on startup (global RAG)
    pdf_uploads/             # Per-user uploads (subfolder per user UUID)
    user_memory/             # Per-user memory Markdown files
    nova.db                  # SQLite (auto-created)
    langgraph.json           # LangGraph Studio config
  frontend/                  # React 19 + Vite + Tailwind CSS v4, port 5174
    src/
      App.jsx                # Shell: auth gate + sidebar/panel layout
      context/AppContext.jsx # Auth + conversations state
      lib/api.js             # Fetch wrappers (incl. SSE streamChat)
      lib/presets.js         # Quick-start prompt presets
      components/            # NovaFace, ChatView, MessageBubble, AgentSteps,
                             #   Composer, Sidebar, AuthScreen, DocsPanel,
                             #   IntegrationsPanel, PresetGrid, Markdown
  start.ps1                  # One-shot launcher (Windows)
```

---

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, Python 3.11+, uvicorn |
| Database | SQLite via SQLAlchemy async (aiosqlite) |
| Vector store | Pinecone (serverless, one index / two namespaces) |
| Agent framework | LangGraph (`StateGraph` + `ToolNode`) |
| LLM / embeddings | Pluggable: OpenAI (default) · Gemini · Ollama |
| Auth | Sign in with Google (OAuth2) → JWT session token |
| Integrations | Google Calendar |
| Frontend | React 19, Vite, Tailwind CSS v4 |
| Observability | LangSmith (optional, off by default) |

---

## How it works

### Nova — a LangGraph agent

`nova_agent.py` builds a `StateGraph`: an `agente` node (the LLM bound to Nova's tools)
and a `tools` node (`ToolNode`), looping until the LLM answers without tool calls.

Tools (`nova_tools.py`):

| Tool | What it does |
|---|---|
| `establecer_emocion` | Sets Nova's facial expression for the reply |
| `buscar_en_conocimiento` | RAG search over the user's knowledge base — a *visible* step |
| `guardar_en_memoria` / `eliminar_de_memoria` | Mutates the user's persistent memory (the "digital twin") |
| `guardar_preferencia_culinaria` / `guardar_receta` | Cooking skill (the former Chefsito, folded in) |
| `consultar_calendario` / `crear_evento_calendario` | Reads / writes Google Calendar |
| `finalizar_onboarding` | Marks the first-run onboarding complete |

### Streaming — you see what it's doing

`POST /chat/stream` runs the graph via `astream_events` and emits Server-Sent Events:
`conversation` → a mix of `step` / `token` / `emotion` / `sources` → `done`. The UI
renders the `step` events as a live "reasoning" panel (e.g. *"Buscando en tu base de
conocimiento"*, *"Consultando tu Google Calendar"*). `POST /chat` is the non-streaming
equivalent; `POST /chat/document` ingests an upload then answers.

### LLM provider layer

All model/embedding calls go through `llm_provider.py`. Set `LLM_PROVIDER` in `.env`:

| `LLM_PROVIDER` | Chat model | Embedding model | Vector dim |
|---|---|---|---|
| `openai` (default) | `ChatOpenAI` (`gpt-4o-mini`) | `text-embedding-3-small` | 1536 |
| `gemini` | `ChatGoogleGenerativeAI` | `gemini-embedding-001` | 768 |
| `ollama` | `ChatOllama` | `gemini-embedding-001` | 768 |

### RAG pipeline (Pinecone)

One Pinecone index, two namespaces: `knowledge` and `memory`.

1. At startup, files in `knowledge_base/` are ingested with `user_id=""` (global),
   deduped by an md5 `content_hash`.
2. User uploads go to `pdf_uploads/<user_id>/` and are ingested with `user_id=<uuid>`.
   Formats: `.pdf`, `.md`, `.txt`.
3. `buscar_en_conocimiento` queries Pinecone with a native metadata filter
   (`user_id ∈ {"", current_user}`).
4. Files uploaded via `POST /chat/document` have their chunks fetched by `doc_id` and
   prepended to the prompt as `extra_rag_context`, so Nova always sees the fresh upload.

> **Note:** a Pinecone index has a fixed dimension. It must match the embedding model
> (see the table above). Switching `LLM_PROVIDER` across that boundary requires a new
> `PINECONE_INDEX_NAME`.

### Memory & onboarding

Per-user memory ("digital twin") lives as Markdown files in `user_memory/` — Nova reads
the whole file into its system prompt and mutates it via the memory tools. New users
have `is_onboarded = false`; while false, Nova runs a natural conversational onboarding
and calls `finalizar_onboarding` once it knows the user.

### Auth — Sign in with Google

The only sign-in method. `GET /auth/google/login` returns the Google consent URL; a
single consent grants identity **and** Calendar access. The callback
(`/integrations/google/callback`) creates/finds the user, stores their OAuth
credentials, mints a JWT and redirects back to the UI with `?token=`. Stored
credentials are reused by the calendar tools.

---

## Setup

### Requirements

- Python 3.11+
- Node.js 18+
- A **Pinecone** account + API key — [pinecone.io](https://www.pinecone.io/)
- An LLM key for the active provider (OpenAI by default, or Gemini)
- A **Google OAuth client** (Web application) — [console.cloud.google.com](https://console.cloud.google.com/)
  with the Calendar API enabled and `http://localhost:8010/integrations/google/callback`
  as an authorized redirect URI

### Backend

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

cd backend
pip install -r requirements.txt

cp .env.example .env
# Edit .env — see "Environment variables" below

uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

Verify with `GET http://localhost:8010/health`. There is no test suite.

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5174  (proxies /api/* → localhost:8010/*)
```

### Windows one-shot

```powershell
.\start.ps1
```

---

## API endpoints

All endpoints are at the **root** level; the Vite dev proxy maps `/api/*` → `/*`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/google/login` | Returns the Google OAuth consent URL |
| `GET` | `/integrations/google/callback` | OAuth redirect target → mints JWT, redirects to UI |
| `GET` | `/auth/me` | Current user |
| `POST` | `/chat` | Send a message (non-streaming JSON) |
| `POST` | `/chat/stream` | Send a message — **SSE** stream of agent steps + tokens |
| `POST` | `/chat/document` | Upload a file + send a message (multipart) |
| `GET` | `/conversations` | List conversations |
| `GET` | `/conversations/{id}` | Conversation + messages |
| `DELETE` | `/conversations/{id}` | Delete conversation |
| `POST` | `/documents` | Upload a document into RAG |
| `GET` | `/documents` | List the user's documents |
| `DELETE` | `/documents/{id}` | Delete a document + its vectors |
| `POST` | `/rag/search` | Raw RAG search |
| `POST` | `/vision/interpret` | Analyze an image (base64) |
| `GET` | `/integrations/google/status` | Whether Google/Calendar is configured & connected |
| `GET` | `/health` | Health check |

### `POST /chat/stream` — SSE event types

`conversation` (`{conversation_id}`) · `step` (`{name, label, status, detail}`) ·
`token` (`{text}`) · `emotion` (`{value}`) · `sources` (`{value: [...]}`) ·
`done` (`{text, emotion}`) · `error` (`{message}`).

---

## Environment variables

See `backend/.env.example` for the full list. Key ones:

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `openai` (default) \| `gemini` \| `ollama` |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai` |
| `GEMINI_API_KEY` | Required for `gemini`, and for embeddings under `ollama` |
| `PINECONE_API_KEY` | Required — vector store |
| `PINECONE_INDEX_NAME` | Index name (auto-created on startup with the right dimension) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Required — Sign in with Google + Calendar |
| `GOOGLE_REDIRECT_URI` | Must match the Google console exactly (default: `http://localhost:8010/integrations/google/callback`) |
| `JWT_SECRET_KEY` | Random secret, min 32 chars |

Storage paths (`DATABASE_URL`, `PDF_UPLOAD_DIR`, `KNOWLEDGE_BASE_DIR`, `USER_MEMORY_DIR`)
default to local directories under `backend/` and are created automatically.

### Google OAuth notes

- The Calendar scope is "sensitive", so Google shows an *"app not verified"* screen.
  It is bypassable via **Advanced → Go to Nova** — full verification is only needed for
  a public release.
- In **Testing** mode only emails added as *test users* can sign in. In **Production**
  anyone can, but each user sees the unverified screen once.

---

## LangGraph Studio (optional)

```bash
cd backend
langgraph dev --port 2024
# Open https://smith.langchain.com/studio → connect to localhost:2024
```

Graph: `nova` → `backend/app/nova_agent.py:nova_graph`.
