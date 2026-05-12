"""Nova Agent — FastAPI application."""

import logging
import os
import uuid
import traceback

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import create_access_token, decode_token, hash_password, verify_password
from .config import settings
from .db import AsyncSessionLocal, init_db
from .gemini_service import chat_with_rag, interpret_image
from .chef_agent import chat_with_chef
from .rag_service import rag_service
from .schemas import (
    AuthResponse,
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    LoginRequest,
    MessageResponse,
    RAGSearchRequest,
    RegisterRequest,
    UserResponse,
)
from . import repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nova-agent")

app = FastAPI(title="Nova Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )

security = HTTPBearer(auto_error=False)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
):
    if not creds:
        raise HTTPException(401, "Token requerido")
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(401, "Token invalido o expirado")
    user = await repo.get_user_by_id(session, payload["sub"])
    if not user:
        raise HTTPException(401, "Usuario no encontrado")
    return user


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    # Configure LangSmith tracing if enabled
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        logger.info("[LangSmith] Tracing enabled — project: %s", settings.langsmith_project)

    await init_db()
    os.makedirs(settings.pdf_upload_dir, exist_ok=True)
    os.makedirs(settings.knowledge_base_dir, exist_ok=True)
    os.makedirs(settings.user_memory_dir, exist_ok=True)
    rag_service.initialize()
    kb_count = await rag_service.ingest_knowledge_base_dir()
    logger.info("[Startup] Knowledge base: %d new chunks ingested", kb_count)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=AuthResponse)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_db)):
    existing = await repo.get_user_by_email(session, body.email)
    if existing:
        raise HTTPException(409, "Email ya registrado")
    hashed = hash_password(body.password)
    user = await repo.create_user(session, body.email, body.name or body.email.split("@")[0], hashed)
    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        access_token=token, user_id=user.id, email=user.email, name=user.name,
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)):
    user = await repo.get_user_by_email(session, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(
        access_token=token, user_id=user.id, email=user.email, name=user.name,
    )


@app.get("/auth/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return user


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # Get or create conversation
    if body.conversation_id:
        conv = await repo.get_conversation(session, body.conversation_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(404, "Conversacion no encontrada")
    else:
        title = body.message[:60] + ("..." if len(body.message) > 60 else "")
        conv = await repo.create_conversation(session, user.id, title, mode=body.mode)

    # Build history
    messages = await repo.get_messages(session, conv.id)
    history = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    await repo.add_message(session, conv.id, "user", body.message, image_url="[image]" if body.image_base64 else None)

    # Fetch user's uploaded docs for context
    user_docs = await repo.get_all_documents(session, user.id)
    doc_names = [d.filename for d in user_docs]

    # Generate response — route to the right agent based on mode
    if body.mode == "chef":
        response_text, sources, emotion = await chat_with_chef(
            body.message, history, user.id, image_base64=body.image_base64,
        )
    else:
        response_text, sources, emotion = await chat_with_rag(
            body.message, history, user.id, image_base64=body.image_base64,
            user_docs=doc_names,
        )

    # Save assistant message
    await repo.add_message(session, conv.id, "assistant", response_text)

    return ChatResponse(conversation_id=conv.id, response=response_text, sources=sources, emotion=emotion)


# ── Conversations ─────────────────────────────────────────────────────────────

@app.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db),
):
    convs = await repo.get_conversations_by_user(session, user.id)
    return convs


@app.get("/conversations/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conv_id: str, user=Depends(get_current_user), session: AsyncSession = Depends(get_db),
):
    conv = await repo.get_conversation(session, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(404, "Conversacion no encontrada")
    msgs = await repo.get_messages(session, conv_id)
    return ConversationDetailResponse(
        conversation=conv,
        messages=msgs,
    )


@app.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: str, user=Depends(get_current_user), session: AsyncSession = Depends(get_db),
):
    conv = await repo.get_conversation(session, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(404, "Conversacion no encontrada")
    await repo.delete_conversation(session, conv_id)
    return {"ok": True}


# ── Documents ─────────────────────────────────────────────────────────────────

# ── Shared helper: ingest an uploaded file and register it in the DB ──────────

async def _ingest_upload(
    file: UploadFile,
    user_id: str,
    session,
    description: str = "",
) -> tuple:
    """Save file to disk, ingest into RAG, persist in DB. Returns (doc_record, file_path, chroma_doc_id)."""
    if not file.filename.lower().endswith((".pdf", ".md", ".txt")):
        raise HTTPException(400, "Solo se permiten archivos PDF, Markdown o TXT")

    doc_id = str(uuid.uuid4())
    user_upload_dir = os.path.join(settings.pdf_upload_dir, user_id)
    os.makedirs(user_upload_dir, exist_ok=True)
    safe_filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(user_upload_dir, safe_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    if file.filename.lower().endswith(".pdf"):
        chunk_count = await rag_service.ingest_pdf(file_path, file.filename, doc_id, user_id=user_id)
    else:
        chunk_count = await rag_service.ingest_markdown(file_path, file.filename, doc_id, user_id=user_id)

    doc = await repo.create_document(session, user_id, file.filename, description or None, chunk_count)
    return doc, file_path, doc_id


@app.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    description: str = Form(""),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    doc, _, _cid = await _ingest_upload(file, user.id, session, description)
    return doc


# ── Chat with document (upload PDF directly from chat) ───────────────────────

@app.post("/chat/document", response_model=ChatResponse)
async def chat_with_document(
    file: UploadFile = File(...),
    message: str = Form(""),
    conversation_id: str = Form(""),
    mode: str = Form("nova"),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Upload a document from the chat input. Ingests it into RAG and sends a chat message."""
    # 1. Ingest file
    doc, _, chroma_doc_id = await _ingest_upload(file, user.id, session)

    # 2. Get or create conversation
    if conversation_id:
        conv = await repo.get_conversation(session, conversation_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(404, "Conversacion no encontrada")
    else:
        title = (message or file.filename)[:60]
        conv = await repo.create_conversation(session, user.id, title, mode=mode)

    # 3. Build history and user message
    user_msg_text = message or f"He subido el archivo: {file.filename}"
    messages_db = await repo.get_messages(session, conv.id)
    history = [{"role": m.role, "content": m.content} for m in messages_db]

    await repo.add_message(session, conv.id, "user", user_msg_text)

    # 4. Inject document chunks directly so Nova can always see the fresh upload
    chunks = rag_service.get_document_chunks(chroma_doc_id)
    extra_ctx = None
    if chunks:
        extra_ctx = (
            f"[Documento recién subido por el usuario: {file.filename}]\n"
            + "\n\n".join(c["content"] for c in chunks)
        )

    # 5. Generate response
    user_docs = await repo.get_all_documents(session, user.id)
    doc_names = [d.filename for d in user_docs]
    if mode == "chef":
        response_text, sources, emotion = await chat_with_chef(
            user_msg_text, history, user.id,
        )
    else:
        response_text, sources, emotion = await chat_with_rag(
            user_msg_text, history, user.id,
            extra_rag_context=extra_ctx,
            user_docs=doc_names,
        )

    await repo.add_message(session, conv.id, "assistant", response_text)

    return ChatResponse(
        conversation_id=conv.id,
        response=response_text,
        sources=sources,
        emotion=emotion,
        uploaded_document=DocumentUploadResponse.model_validate(doc),
    )


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(user=Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    docs = await repo.get_all_documents(session, user.id)
    return DocumentListResponse(documents=docs, total=len(docs))


@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str, user=Depends(get_current_user), session: AsyncSession = Depends(get_db),
):
    doc = await repo.get_document(session, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(404, "Documento no encontrado")
    rag_service.delete_document_chunks(doc.id)
    await repo.delete_document(session, doc_id)
    return {"ok": True}


# ── RAG search ────────────────────────────────────────────────────────────────

@app.post("/rag/search")
async def rag_search(body: RAGSearchRequest, user=Depends(get_current_user)):
    results = await rag_service.search(body.query, user_id=user.id, top_k=body.top_k)
    return {"results": results, "total": len(results)}


# ── Vision ────────────────────────────────────────────────────────────────────

@app.post("/vision/interpret")
async def vision_interpret(
    body: dict, user=Depends(get_current_user),
):
    image_b64 = body.get("image_base64")
    instruction = body.get("instruction", "")
    if not image_b64:
        raise HTTPException(400, "image_base64 requerido")
    result = await interpret_image(image_b64, instruction)
    return {"interpretation": result}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "nova-agent"}
