"""Pydantic schemas — Nova Agent."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=4)
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    image_base64: Optional[str] = Field(None, description="Imagen en base64 para vision")
    mode: str = Field(default="nova", description="Agente activo: 'nova' | 'chef'")


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    sources: List[str] = Field(default_factory=list)
    emotion: str = "neutral"
    uploaded_document: Optional["DocumentUploadResponse"] = None


# ── Conversations ─────────────────────────────────────────────────────────────

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    titulo: str
    mode: str = "nova"
    created_at: datetime
    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    image_url: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    description: Optional[str] = None
    chunk_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: List[DocumentUploadResponse]
    total: int


# ── RAG Search ────────────────────────────────────────────────────────────────

class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = Field(5, ge=1, le=20)


class RAGSearchResult(BaseModel):
    content: str
    source: str
    score: float


class RAGSearchResponse(BaseModel):
    results: List[RAGSearchResult]
    query: str
