"""Nova Agent — a LangGraph agent with RAG, memory and tools.

The graph is a classic agent loop: an ``agente`` node that calls the LLM (bound to
Nova's tools) and a ``tools`` node that runs whatever the LLM asked for, looping until
the LLM answers without tool calls.

Consumers use :func:`astream_nova` to get a normalized stream of events
(``step`` / ``token`` / ``emotion`` / ``sources`` / ``done``) — the same events the
chat UI renders as Nova's visible reasoning. :func:`chat_nova` is the non-streaming
convenience wrapper built on top of it.
"""

import logging
import re
from datetime import datetime

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from . import memory_service
from .llm_provider import get_llm
from .nova_tools import NOVA_TOOLS, TOOL_LABELS
from .rag_service import rag_service

logger = logging.getLogger("nova-agent")

SYSTEM_PROMPT = """Eres Nova, el asistente personal e inteligente del usuario — su "buddy" digital.
No eres un chatbot mas: eres la evolucion hacia agentes inteligentes. Gestionas la memoria
del usuario como un gemelo digital y tienes herramientas para actuar por el.

PERSONALIDAD:
- Amigable, cercana y con energia. Hablas como un buen amigo, no como un manual.
- Tuteas al usuario y usas su nombre cuando lo conoces.

Fecha y hora actual: {now}

HERRAMIENTAS (usalas; no las menciones por su nombre tecnico):
- establecer_emocion: SIEMPRE tu PRIMERA accion, antes de escribir la respuesta.
- buscar_en_conocimiento: usala siempre que la pregunta pueda responderse con los
  documentos o la base de conocimiento del usuario. Es tu punto fuerte.
- guardar_en_memoria / eliminar_de_memoria: gestiona el gemelo digital del usuario.
  Guarda proactivamente lo que aprendas de el (nombre, gustos, metas, rutinas...).
- guardar_preferencia_culinaria / guardar_receta: tambien eres un gran asistente de
  cocina; recuerda los gustos y las recetas del usuario.
- consultar_calendario / crear_evento_calendario: gestiona la agenda del usuario en
  Google Calendar. Usa la fecha y hora actual para calcular fechas relativas.

REGLAS:
1. Responde claro, conciso y en el idioma del usuario.
2. Usa formato Markdown cuando mejore la legibilidad.
3. Si usaste buscar_en_conocimiento, basa la respuesta en lo que encontraste. Si no
   hallaste nada relevante, dilo y responde con tu conocimiento general.
4. No inventes informacion.

MEMORIA PERSISTENTE DEL USUARIO (su gemelo digital):
{file_memory}

CONTEXTO DE CONVERSACIONES PREVIAS:
{memory_context}

DOCUMENTOS QUE EL USUARIO HA SUBIDO (consulta su contenido con buscar_en_conocimiento):
{user_documents}
{extra_context}{onboarding}"""

ONBOARDING_BLOCK = """

--- MODO ONBOARDING (primera vez del usuario) ---
Es la primera conversacion de este usuario contigo. Preséntate de forma calida y, de
manera natural y conversacional (nunca como un formulario), hazle preguntas para
conocerlo: su nombre, a que se dedica, sus intereses, sus metas y como le gusta que le
hablen. Haz solo una o dos preguntas a la vez. Guarda cada dato que aprendas con
guardar_en_memoria. Cuando ya tengas una buena imagen de quien es, llama a
finalizar_onboarding y dale la bienvenida explicandole brevemente que puedes hacer por el."""


# ── Graph ─────────────────────────────────────────────────────────────────────

async def _agente(state: MessagesState) -> dict:
    llm = get_llm().bind_tools(NOVA_TOOLS)
    return {"messages": [await llm.ainvoke(state["messages"])]}


def _build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("agente", _agente)
    builder.add_node("tools", ToolNode(NOVA_TOOLS))
    builder.add_edge(START, "agente")
    builder.add_conditional_edges("agente", tools_condition)
    builder.add_edge("tools", "agente")
    return builder.compile()


nova_graph = _build_graph()


# ── Prompt + message assembly ─────────────────────────────────────────────────

async def build_system_prompt(
    user_id: str,
    message: str,
    extra_rag_context: str | None = None,
    user_docs: list[str] | None = None,
    onboarding: bool = False,
) -> str:
    file_memory = memory_service.read_memory(user_id) or "Sin datos guardados aun."

    memory_results = await rag_service.search_memory(message, user_id)
    mem_parts = [r["content"] for r in memory_results if r["score"] > 0.3]
    memory_context = "\n".join(mem_parts) if mem_parts else "Sin contexto previo."

    docs_str = "\n".join(f"- {n}" for n in user_docs) if user_docs else "Sin documentos subidos aun."

    extra = (
        f"\n\n--- DOCUMENTO RECIEN SUBIDO POR EL USUARIO ---\n{extra_rag_context}\n--- FIN DEL DOCUMENTO ---"
        if extra_rag_context else ""
    )
    onboarding_block = ONBOARDING_BLOCK if onboarding else ""

    return SYSTEM_PROMPT.format(
        now=datetime.now().strftime("%Y-%m-%d %H:%M (%A)"),
        file_memory=file_memory,
        memory_context=memory_context,
        user_documents=docs_str,
        extra_context=extra,
        onboarding=onboarding_block,
    )


async def build_messages(
    message: str,
    conversation_history: list[dict],
    user_id: str,
    image_base64: str | None = None,
    extra_rag_context: str | None = None,
    user_docs: list[str] | None = None,
    onboarding: bool = False,
) -> list[BaseMessage]:
    system = await build_system_prompt(user_id, message, extra_rag_context, user_docs, onboarding)
    messages: list[BaseMessage] = [SystemMessage(content=system)]
    for msg in conversation_history[-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    if image_base64:
        messages.append(HumanMessage(content=[
            {"type": "text", "text": message or "Analiza esta imagen"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]))
    else:
        messages.append(HumanMessage(content=message))
    return messages


# ── Streaming ─────────────────────────────────────────────────────────────────

_SOURCE_RE = re.compile(r"\[Fuente: ([^\]]+)\]")


def _content_text(chunk) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
    return str(content)


def _step_detail(name: str, args: dict) -> str:
    if name == "buscar_en_conocimiento":
        return str(args.get("query", ""))
    if name == "guardar_en_memoria":
        return str(args.get("clave", ""))
    if name == "guardar_receta":
        return str(args.get("nombre", ""))
    if name == "consultar_calendario":
        dias = args.get("dias")
        return f"proximos {dias} dias" if dias else "proximos eventos"
    if name == "crear_evento_calendario":
        return str(args.get("titulo", ""))
    return ""


async def astream_nova(messages: list[BaseMessage], user_id: str):
    """Run the Nova graph and yield normalized events for the chat UI.

    Event shapes:
      {"type": "step", "name", "label", "status": "running"|"done", "detail"}
      {"type": "token", "text"}
      {"type": "emotion", "value"}
      {"type": "sources", "value": [..]}   (emitted once, near the end)
      {"type": "done", "text", "emotion"}  (emitted last)
    """
    config = {"configurable": {"user_id": user_id}, "recursion_limit": 15}
    sources: set[str] = set()
    emotion = "neutral"
    final_text: list[str] = []

    async for event in nova_graph.astream_events(
        {"messages": messages}, config=config, version="v2"
    ):
        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_tool_start" and name in TOOL_LABELS:
            args = event["data"].get("input", {}) or {}
            if name == "establecer_emocion":
                emotion = str(args.get("emocion", "neutral"))
                yield {"type": "emotion", "value": emotion}
            yield {
                "type": "step", "name": name, "label": TOOL_LABELS[name],
                "status": "running", "detail": _step_detail(name, args),
            }

        elif kind == "on_tool_end" and name in TOOL_LABELS:
            output = event["data"].get("output")
            text = getattr(output, "content", output)
            if name == "buscar_en_conocimiento" and isinstance(text, str):
                sources.update(_SOURCE_RE.findall(text))
            yield {
                "type": "step", "name": name, "label": TOOL_LABELS[name],
                "status": "done", "detail": "",
            }

        elif kind == "on_chat_model_stream":
            piece = _content_text(event["data"]["chunk"])
            if piece:
                final_text.append(piece)
                yield {"type": "token", "text": piece}

    yield {"type": "sources", "value": sorted(sources)}
    yield {"type": "done", "text": "".join(final_text).strip(), "emotion": emotion}
    logger.info(
        "[Nova] Response (%d chars, %d sources, emotion=%s)",
        len("".join(final_text)), len(sources), emotion,
    )


async def chat_nova(messages: list[BaseMessage], user_id: str) -> tuple[str, list[str], str]:
    """Non-streaming convenience wrapper — returns (text, sources, emotion)."""
    text, sources, emotion = "", [], "neutral"
    async for event in astream_nova(messages, user_id):
        if event["type"] == "sources":
            sources = event["value"]
        elif event["type"] == "done":
            text, emotion = event["text"], event["emotion"]
    return text, sources, emotion
