"""Nova Service — Nova Agent with RAG, Vision, and Ollama/Gemini fallback."""

import logging
import re
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langsmith import traceable
from pydantic import BaseModel, Field

from .config import settings
from .rag_service import rag_service
from . import memory_service

logger = logging.getLogger("nova-agent")

# ── Ollama / model selection ───────────────────────────────────────────────────

# _OLLAMA_MODEL = "gemma4:e4b"
_OLLAMA_MODEL = "qwen3.5:9b"

_OLLAMA_BASE_URL = "http://localhost:11434"
_nova_model = None


def _check_ollama_available() -> bool:
    """Ping Ollama and verify the target model is pulled."""
    try:
        import httpx
        resp = httpx.get(f"{_OLLAMA_BASE_URL}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            names = [m["name"] for m in resp.json().get("models", [])]
            return any(_OLLAMA_MODEL == n or n.startswith(_OLLAMA_MODEL + ":") for n in names)
    except Exception:
        pass
    return False


def _get_nova_model():
    global _nova_model
    if _nova_model is None:
        if _check_ollama_available():
            logger.info("[Nova] Backend: Ollama (%s)", _OLLAMA_MODEL)
            _nova_model = ChatOllama(model=_OLLAMA_MODEL, base_url=_OLLAMA_BASE_URL, temperature=0.3)
        else:
            logger.info("[Nova] Backend: Gemini (%s)", settings.gemini_chat_model)
            _nova_model = ChatGoogleGenerativeAI(
                model=settings.gemini_chat_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.3,
            )
    return _nova_model

SYSTEM_PROMPT = """Eres Nova, un asistente virtual inteligente y amigable.
Tu proposito es ayudar a los usuarios respondiendo preguntas, analizando documentos, e interpretando imagenes.

REGLAS:
1. Responde de forma clara, concisa y amigable.
2. Basa siempre tus respuestas en el CONTEXTO proporcionado por la base de conocimiento cuando sea relevante.
3. Si no conoces la respuesta, dilo honestamente en lugar de inventar informacion.
4. Puedes analizar imagenes que el usuario adjunte — describe lo que ves, interpreta documentos, y responde preguntas sobre el contenido visual.
5. Responde en el mismo idioma que use el usuario.
6. Usa formato Markdown para mejorar la legibilidad de tus respuestas (listas, negritas, encabezados cuando sea apropiado).
7. MEMORIA: Cuando el usuario te pida que recuerdes algo, o cuando detectes informacion relevante sobre el usuario (nombre, preferencias, metas, datos personales, etc.), USA la herramienta `guardar_en_memoria` para guardarlo de forma persistente. Cuando te pida olvidar algo, usa `eliminar_de_memoria`.

MEMORIA PERSISTENTE DEL USUARIO:
{file_memory}

CONTEXTO DE CONVERSACIONES PREVIAS:
{memory_context}

DOCUMENTOS SUBIDOS POR EL USUARIO (siempre disponibles en tu base de conocimiento):
{user_documents}

--- BASE DE CONOCIMIENTO ---
{rag_context}
--- FIN BASE DE CONOCIMIENTO ---

IMPORTANTE: Todos los documentos listados en DOCUMENTOS SUBIDOS ya forman parte de tu base de conocimiento y puedes consultarlos SIEMPRE. No le pidas al usuario que los adjunte de nuevo. Si el usuario pregunta sobre ellos, busca en el contexto de la base de conocimiento o pide que haga una pregunta especifica sobre el contenido.
Usa la informacion del contexto para dar respuestas precisas. Si la pregunta no se relaciona con la base de conocimiento, responde con tu conocimiento general.
"""

# ── Tool schemas ────────────────────────────────────────────────────────────────

class EstablecerEmocion(BaseModel):
    """Establece la emocion que Nova debe expresar al responder.
    SIEMPRE llama esta herramienta como primera accion antes de escribir tu respuesta."""
    emocion: Literal["neutral", "happy", "talking", "sad", "angry", "surprised", "excited", "thinking"] = Field(
        description=(
            "neutral=respuesta normal. happy=ayuda exitosa, buenas noticias. "
            "talking=explicacion larga o tecnica. sad=no sabe la respuesta o hay error. "
            "angry=detecta bug, codigo inseguro o problema grave. "
            "surprised=pregunta inesperada o dato curioso. "
            "excited=tema muy interesante, logro del usuario. "
            "thinking=calculando o razonando algo complejo."
        )
    )


class GuardarEnMemoria(BaseModel):
    """Guarda un dato importante del usuario en su memoria persistente.
    Usala cuando el usuario pida que recuerdes algo, o cuando detectes informacion
    relevante sobre el (nombre, edad, preferencias, metas, etc.)."""
    categoria: str = Field(description="Categoria del dato. Ejemplos: 'Datos personales', 'Preferencias', 'Metas', 'Salud', 'Trabajo', 'Notas'")
    clave: str = Field(description="Nombre corto del dato. Ejemplos: 'Nombre', 'Edad', 'Ciudad', 'Idioma preferido'")
    valor: str = Field(description="Valor del dato a guardar")


class EliminarDeMemoria(BaseModel):
    """Elimina un dato de la memoria persistente del usuario cuando pida olvidarlo."""
    clave: str = Field(description="Nombre del dato a eliminar")


_NOVA_TOOLS = [EstablecerEmocion, GuardarEnMemoria, EliminarDeMemoria]


async def _extract_and_save_memory(user_id: str, user_message: str, assistant_response: str) -> None:
    patterns = [
        r"(?:me llamo|mi nombre es|soy)\s+(\w+)",
        r"(?:tengo|padezco|sufro de)\s+(.+?)(?:\.|,|$)",
        r"(?:soy alergico|alergia a)\s+(.+?)(?:\.|,|$)",
        r"(?:prefiero|quisiera|necesito)\s+(.+?)(?:\.|,|$)",
        r"(?:trabajo en|estudio en)\s+(.+?)(?:\.|,|$)",
        r"(?:my name is|i am|i'm)\s+(\w+)",
    ]
    insights = []
    for pattern in patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            insights.append(f"El usuario menciono: {match.group(0).strip()}")
    if insights:
        await rag_service.save_memory(user_id, " | ".join(insights))


@traceable(run_type="chain", name="nova_chat_with_rag")
async def chat_with_rag(
    message: str,
    conversation_history: list[dict],
    user_id: str,
    image_base64: str | None = None,
    extra_rag_context: str | None = None,
    user_docs: list[str] | None = None,
) -> tuple[str, list[str], str]:
    # 1. RAG + memory context
    rag_results = await rag_service.search(message, user_id=user_id)
    sources = list({r["source"] for r in rag_results})
    rag_context = (
        "\n\n".join(f"[Fuente: {r['source']}]\n{r['content']}" for r in rag_results)
        if rag_results else ""
    )
    # Prepend freshly-uploaded doc chunks when provided (guaranteed relevant)
    if extra_rag_context:
        rag_context = extra_rag_context + ("\n\n" + rag_context if rag_context else "")

    # Build user documents list string
    if user_docs:
        docs_str = "\n".join(f"- {name}" for name in user_docs)
    else:
        docs_str = "Sin documentos subidos aun."

    memory_results = await rag_service.search_memory(message, user_id)
    memory_context = "Sin contexto previo."
    if memory_results:
        mem_parts = [r["content"] for r in memory_results if r["score"] > 0.3]
        if mem_parts:
            memory_context = "\n".join(mem_parts)

    file_memory = memory_service.read_memory(user_id) or "Sin datos guardados aun."

    system = SYSTEM_PROMPT.format(
        file_memory=file_memory,
        memory_context=memory_context,
        rag_context=rag_context or "Sin informacion relevante en la base de conocimiento.",
        user_documents=docs_str,
    )

    # 2. Build message list
    lc_messages = [SystemMessage(content=system)]
    for msg in conversation_history[-20:]:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))

    if image_base64:
        lc_messages.append(HumanMessage(content=[
            {"type": "text", "text": message or "Analiza esta imagen"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]))
    else:
        lc_messages.append(HumanMessage(content=message))

    # 3. Invoke with tools — up to 5 rounds
    model_with_tools = _get_nova_model().bind_tools(_NOVA_TOOLS)
    emotion = "neutral"

    for _ in range(5):
        response = await model_with_tools.ainvoke(lc_messages)
        if not getattr(response, "tool_calls", None):
            break
        lc_messages.append(response)
        tool_results = []
        for tc in response.tool_calls:
            name = tc["name"]
            args = tc["args"]
            if name == "EstablecerEmocion":
                emotion = str(args.get("emocion", "neutral"))
                result = "Emocion establecida."
            elif name == "GuardarEnMemoria":
                memory_service.save_memory_entry(
                    user_id,
                    str(args.get("categoria", "Notas")),
                    str(args.get("clave", "")),
                    str(args.get("valor", "")),
                )
                result = "Guardado correctamente."
            elif name == "EliminarDeMemoria":
                deleted = memory_service.delete_memory_entry(user_id, str(args.get("clave", "")))
                result = "Eliminado." if deleted else "No encontrado."
            else:
                result = "Herramienta desconocida."
            tool_results.append(ToolMessage(content=result, tool_call_id=tc["id"]))
        lc_messages.extend(tool_results)

    # Extract text
    raw = response.content
    if isinstance(raw, list):
        response_text = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in raw
        ).strip()
    else:
        response_text = str(raw)

    # 4. Auto-save memory patterns (best-effort)
    try:
        await _extract_and_save_memory(user_id, message, response_text)
    except Exception as exc:
        logger.warning("[Memory] Failed to save: %s", exc)

    logger.info("[Nova] Response (%d chars, %d sources, emotion=%s)", len(response_text), len(sources), emotion)
    return response_text, sources, emotion


async def interpret_image(image_base64: str, instruction: str = "") -> str:
    prompt = instruction or "Analiza esta imagen. Describe lo que ves e interpreta cualquier texto o dato relevante."
    system = SystemMessage(content="Eres Nova, un asistente visual. Analiza imagenes y describe su contenido de forma clara y util.")
    user_msg = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
    ])
    response = await _get_nova_model().ainvoke([system, user_msg])
    raw = response.content
    if isinstance(raw, list):
        return " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in raw).strip()
    return str(raw)
