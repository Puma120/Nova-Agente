"""Repository layer — Users, Conversations, Messages, Documents."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Conversation, Document, GoogleCredential, Message, User


# ── Users ─────────────────────────────────────────────────────────────────────

async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_or_create_google_user(
    session: AsyncSession, *, email: str, name: str, google_sub: str, avatar_url: str | None,
) -> User:
    """Find a user by their Google account, creating one on first sign-in."""
    result = await session.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()
    if not user:
        user = await get_user_by_email(session, email)  # link a pre-existing email row
    if user:
        user.name = name or user.name
        user.google_sub = google_sub
        user.avatar_url = avatar_url
    else:
        user = User(email=email, name=name or email.split("@")[0],
                    google_sub=google_sub, avatar_url=avatar_url)
        session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def set_onboarded(session: AsyncSession, user_id: str) -> None:
    user = await get_user_by_id(session, user_id)
    if user and not user.is_onboarded:
        user.is_onboarded = True
        await session.commit()


# ── Google credentials ────────────────────────────────────────────────────────

async def get_google_credential(session: AsyncSession, user_id: str) -> GoogleCredential | None:
    result = await session.execute(
        select(GoogleCredential).where(GoogleCredential.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_google_credential(session: AsyncSession, user_id: str, **fields) -> GoogleCredential:
    cred = await get_google_credential(session, user_id)
    if cred:
        for key, value in fields.items():
            setattr(cred, key, value)
    else:
        cred = GoogleCredential(user_id=user_id, **fields)
        session.add(cred)
    await session.commit()
    await session.refresh(cred)
    return cred


async def delete_google_credential(session: AsyncSession, user_id: str) -> bool:
    cred = await get_google_credential(session, user_id)
    if not cred:
        return False
    await session.delete(cred)
    await session.commit()
    return True


# ── Conversations ─────────────────────────────────────────────────────────────

async def create_conversation(
    session: AsyncSession, user_id: str, titulo: str = "Nueva conversacion", mode: str = "nova"
) -> Conversation:
    conv = Conversation(user_id=user_id, titulo=titulo, mode=mode)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def get_conversation(session: AsyncSession, conv_id: str) -> Conversation | None:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.id == conv_id)
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()


async def get_conversations_by_user(session: AsyncSession, user_id: str) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_conversation(session: AsyncSession, conv_id: str) -> bool:
    conv = await get_conversation(session, conv_id)
    if not conv:
        return False
    await session.delete(conv)
    await session.commit()
    return True


# ── Messages ──────────────────────────────────────────────────────────────────

async def add_message(
    session: AsyncSession, conversation_id: str, role: str, content: str,
    image_url: str | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id, role=role, content=content, image_url=image_url,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def get_messages(session: AsyncSession, conversation_id: str) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


# ── Documents ─────────────────────────────────────────────────────────────────

async def create_document(
    session: AsyncSession, user_id: str, filename: str, description: str | None, chunk_count: int
) -> Document:
    doc = Document(user_id=user_id, filename=filename, description=description, chunk_count=chunk_count)
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def get_all_documents(session: AsyncSession, user_id: str) -> list[Document]:
    result = await session.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(session: AsyncSession, doc_id: str) -> Document | None:
    result = await session.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def delete_document(session: AsyncSession, doc_id: str) -> bool:
    doc = await get_document(session, doc_id)
    if not doc:
        return False
    await session.delete(doc)
    await session.commit()
    return True
