"""Chef Agent — Chefsito: Asistente de Cocina con Memoria a Largo Plazo (LangGraph + Trustcall)."""

import json
import logging
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, merge_message_runs
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.store.base import BaseStore, GetOp, Item, ListNamespacesOp, PutOp, SearchOp
from pydantic import BaseModel, Field
from trustcall import create_extractor
from typing_extensions import TypedDict

try:
    from . import memory_service
    from .config import settings
    from .rag_service import rag_service
except ImportError:
    # langgraph dev loads the file as a standalone module (no parent package).
    # Add backend/ to sys.path so absolute imports work.
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from app import memory_service  # type: ignore
    from app.config import settings  # type: ignore
    from app.rag_service import rag_service  # type: ignore

logger = logging.getLogger("nova-agent")


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class PerfilChef(BaseModel):
    """Perfil culinario del usuario."""

    nombre: Optional[str] = Field(description="Nombre del cocinero", default=None)
    nivel: Optional[str] = Field(
        description="Nivel de habilidad: principiante | intermedio | avanzado",
        default=None,
    )
    restricciones: list[str] = Field(
        description="Restricciones alimentarias o alergias (lactosa, gluten, nueces…)",
        default_factory=list,
    )
    utensilios: list[str] = Field(
        description="Utensilios o electrodomésticos disponibles (horno, licuadora, wok…)",
        default_factory=list,
    )
    cocinas_favoritas: list[str] = Field(
        description="Tipos de cocina preferidos (mexicana, italiana, asiática…)",
        default_factory=list,
    )


class Receta(BaseModel):
    """Una receta en el recetario personal del usuario."""

    nombre: str = Field(description="Nombre del platillo")
    ingredientes: list[str] = Field(
        description="Lista de ingredientes con cantidad aproximada",
        default_factory=list,
    )
    pasos: list[str] = Field(
        description="Pasos de preparación en orden",
        default_factory=list,
    )
    tiempo_minutos: Optional[int] = Field(
        description="Tiempo total de preparación en minutos",
        default=None,
    )
    porciones: Optional[int] = Field(
        description="Número de porciones que rinde la receta",
        default=None,
    )
    dificultad: Literal["fácil", "media", "difícil"] = Field(
        description="Nivel de dificultad",
        default="fácil",
    )
    tipo_cocina: Optional[str] = Field(
        description="Estilo de cocina (mexicana, italiana, fusión…)",
        default=None,
    )
    puntuacion: Optional[int] = Field(
        description="Puntuación del 1 al 5 dada por el usuario",
        default=None,
    )
    notas: Optional[str] = Field(
        description="Notas personales, variaciones o sustituciones",
        default=None,
    )
    apta_sin_lactosa: Optional[bool] = Field(
        description="True si la receta es apta para intolerantes a la lactosa",
        default=None,
    )
    estado: Literal["pendiente", "probada", "favorita", "archivada"] = Field(
        description="Estado de la receta en el recetario",
        default="pendiente",
    )


class ActualizarMemoriaChef(TypedDict):
    """Decisión sobre qué tipo de memoria del recetario actualizar."""

    tipo: Literal["perfil", "recetas", "instrucciones"]


# ── Prompts ───────────────────────────────────────────────────────────────────

PROMPT_CHEFSITO = """Eres Chefsito, un asistente culinario entusiasta y amigable.
Tu misión es ayudar a {nombre} a descubrir, guardar y mejorar recetas en su recetario personal. Solo añade recetas al recetario cuando estés seguro de que el usuario quiere guardarlas o cuando detectes que ha compartido una receta que vale la pena guardar. No dudes en guardar recetas proactivamente aunque el usuario no lo pida explícitamente, pero siempre prioriza la calidad sobre la cantidad.

Tienes acceso a tres tipos de memoria a largo plazo:
1. Perfil culinario (nivel, restricciones, utensilios, preferencias)
2. Recetario personal (colección de recetas con puntuaciones y notas)
3. Instrucciones personalizadas para guardar recetas

Perfil actual del cocinero:
<perfil>
{perfil}
</perfil>

Recetario actual:
<recetario>
{recetario}
</recetario>

Instrucciones personalizadas para guardar recetas:
<instrucciones>
{instrucciones}
</instrucciones>

Memoria general del usuario (preferencias, datos, notas):
<memoria_general>
{memoria_general}
</memoria_general>

Documentos subidos por el usuario (PDFs y archivos):
<documentos>
{rag_context}
</documentos>

REGLAS:
1. Analiza el mensaje del usuario.
2. Decide si actualizar memoria:
   - Datos personales o culinarios → llama a ActualizarMemoriaChef con tipo `perfil`
   - El usuario menciona o quiere guardar una receta → tipo `recetas`
   - El usuario expresa preferencias sobre cómo guardar recetas → tipo `instrucciones`
3. Notifica al usuario SOLO cuando guardes una receta. No menciones el perfil ni instrucciones.
4. Guarda recetas proactivamente aunque el usuario no lo pida explícitamente.
5. Responde en el idioma que use el usuario.
6. Usa formato Markdown para mejorar la legibilidad.
7. Sé cálido, entusiasta y usa emojis de comida cuando sea natural."""

INSTRUCCION_TC = """Reflexiona sobre la siguiente conversación culinaria.

Usa las herramientas disponibles para extraer y guardar la información relevante.
Usa llamadas en paralelo para manejar actualizaciones e inserciones simultáneamente.

Hora del sistema: {hora}"""

CREAR_INSTRUCCIONES_CHEF = """Reflexiona sobre la siguiente conversación culinaria.

Actualiza las instrucciones sobre cómo guardar recetas en el recetario del usuario.
Usa el feedback del usuario para mejorar la forma en que se registran las recetas.

Instrucciones actuales:
<instrucciones_actuales>
{instrucciones_actuales}
</instrucciones_actuales>"""


# ── Model backend selection ───────────────────────────────────────────────────

_OLLAMA_MODEL = "gemma4"
_OLLAMA_BASE_URL = "http://localhost:11434"


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


# ── Lazy-initialized model & extractors ──────────────────────────────────────

_modelo = None
_extractor_perfil = None


def _get_model():
    global _modelo
    if _modelo is None:
        if _check_ollama_available():
            logger.info("[Chefsito] Backend: Ollama (%s)", _OLLAMA_MODEL)
            _modelo = ChatOllama(
                model=_OLLAMA_MODEL,
                base_url=_OLLAMA_BASE_URL,
                temperature=0.3,
            )
        else:
            logger.info("[Chefsito] Backend: Gemini (%s)", settings.gemini_chat_model)
            _modelo = ChatGoogleGenerativeAI(
                model=settings.gemini_chat_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.3,
            )
    return _modelo


def _get_extractor_perfil():
    global _extractor_perfil
    if _extractor_perfil is None:
        _extractor_perfil = create_extractor(
            _get_model(),
            tools=[PerfilChef],
            tool_choice="PerfilChef",
        )
    return _extractor_perfil


# ── SQLite-backed long-term store ────────────────────────────────────────────

_STORE_DB = Path(__file__).parent.parent / "chef_store.db"


class SqliteChefStore(BaseStore):
    """Persistent SQLite store for Chefsito's long-term memory."""

    def __init__(self, db_path: str) -> None:
        self._db_path = str(db_path)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _setup(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chef_store (
                    namespace  TEXT NOT NULL,
                    key        TEXT NOT NULL,
                    value      TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
            """)
            conn.commit()

    @staticmethod
    def _ns(namespace: tuple) -> str:
        return json.dumps(list(namespace))

    @staticmethod
    def _row_to_item(row: tuple, namespace: tuple) -> Item:
        return Item(
            value=json.loads(row[2]),
            key=row[1],
            namespace=namespace,
            created_at=datetime.fromisoformat(row[3]),
            updated_at=datetime.fromisoformat(row[4]),
        )

    def batch(self, ops) -> list:
        results: list = []
        pending_puts: list = []

        with self._connect() as conn:
            for op in ops:
                if isinstance(op, GetOp):
                    ns_str = self._ns(op.namespace)
                    row = conn.execute(
                        "SELECT namespace, key, value, created_at, updated_at "
                        "FROM chef_store WHERE namespace=? AND key=?",
                        (ns_str, op.key),
                    ).fetchone()
                    results.append(self._row_to_item(row, op.namespace) if row else None)

                elif isinstance(op, SearchOp):
                    ns_str = self._ns(op.namespace_prefix)
                    rows = conn.execute(
                        "SELECT namespace, key, value, created_at, updated_at "
                        "FROM chef_store WHERE namespace=? LIMIT ? OFFSET ?",
                        (ns_str, op.limit, op.offset),
                    ).fetchall()
                    results.append([self._row_to_item(r, op.namespace_prefix) for r in rows])

                elif isinstance(op, PutOp):
                    pending_puts.append(op)
                    results.append(None)

                elif isinstance(op, ListNamespacesOp):
                    rows = conn.execute(
                        "SELECT DISTINCT namespace FROM chef_store"
                    ).fetchall()
                    results.append([tuple(json.loads(r[0])) for r in rows])

                else:
                    results.append(None)

            now = datetime.now(timezone.utc).isoformat()
            for op in pending_puts:
                ns_str = self._ns(op.namespace)
                if op.value is None:
                    conn.execute(
                        "DELETE FROM chef_store WHERE namespace=? AND key=?",
                        (ns_str, op.key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO chef_store (namespace, key, value, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(namespace, key) DO UPDATE SET
                            value      = excluded.value,
                            updated_at = excluded.updated_at
                        """,
                        (ns_str, op.key, json.dumps(op.value), now, now),
                    )
            conn.commit()

        return results

    async def abatch(self, ops) -> list:
        import asyncio
        ops_list = list(ops)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.batch, ops_list)


chef_store = SqliteChefStore(_STORE_DB)


# ── Nodes ─────────────────────────────────────────────────────────────────────

def chefsito(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Nodo principal: carga memorias del store y genera la respuesta del agente."""
    user_id = config["configurable"]["user_id"]

    # Perfil culinario
    mems_perfil = store.search(("perfil_chef", user_id))
    perfil = mems_perfil[0].value if mems_perfil else {}

    # Recetario — resumen compacto
    mems_recetas = store.search(("recetas_chef", user_id))
    recetario_lines = []
    for m in mems_recetas:
        r = m.value
        stars = f" ★{r.get('puntuacion')}/5" if r.get("puntuacion") else ""
        recetario_lines.append(
            f"- **{r.get('nombre', '?')}** ({r.get('tipo_cocina', '?')}) "
            f"{r.get('tiempo_minutos', '?')} min{stars}"
        )
    recetario = "\n".join(recetario_lines) if recetario_lines else "Vacío — aún no has guardado recetas."

    # Instrucciones personalizadas
    mems_inst = store.search(("instrucciones_chef", user_id))
    instrucciones = mems_inst[0].value.get("memoria", "") if mems_inst else ""

    # Memoria general compartida (archivo .md)
    memoria_general = memory_service.read_memory(user_id) or "Sin datos guardados aún."

    # Contexto RAG (PDFs del usuario) — pre-calculado en chat_with_chef y pasado por config
    rag_context = config["configurable"].get("rag_context") or "Sin documentos subidos."

    nombre = perfil.get("nombre") or "cocinero"
    system_msg = PROMPT_CHEFSITO.format(
        nombre=nombre,
        perfil=perfil or "Sin datos aún.",
        recetario=recetario,
        instrucciones=instrucciones or "Sin instrucciones personalizadas.",
        memoria_general=memoria_general,
        rag_context=rag_context,
    )

    respuesta = _get_model().bind_tools([ActualizarMemoriaChef]).invoke(
        [SystemMessage(content=system_msg)] + state["messages"]
    )
    return {"messages": [respuesta]}


def actualizar_perfil_chef(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Actualiza el perfil culinario del usuario con Trustcall."""
    user_id = config["configurable"]["user_id"]
    namespace = ("perfil_chef", user_id)

    items_existentes = store.search(namespace)
    memorias_existentes = (
        [(item.key, "PerfilChef", item.value) for item in items_existentes]
        if items_existentes else None
    )

    instruccion = INSTRUCCION_TC.format(hora=datetime.now().isoformat())
    mensajes = list(merge_message_runs(
        [SystemMessage(content=instruccion)] + state["messages"][:-1]
    ))

    resultado = _get_extractor_perfil().invoke({
        "messages": mensajes,
        "existing": memorias_existentes,
    })

    for r, rmeta in zip(resultado["responses"], resultado["response_metadata"]):
        doc_id = rmeta.get("json_doc_id", str(uuid.uuid4()))
        if rmeta.get("deleted"):
            store.put(namespace, doc_id, None)
        else:
            store.put(namespace, doc_id, r.model_dump(mode="json"))

    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {"messages": [{"role": "tool", "content": "perfil actualizado", "tool_call_id": tool_call_id}]}


def actualizar_recetas_chef(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Actualiza el recetario personal con Trustcall (soporta inserciones y patches)."""
    user_id = config["configurable"]["user_id"]
    namespace = ("recetas_chef", user_id)

    items_existentes = store.search(namespace)
    memorias_existentes = (
        [(item.key, "Receta", item.value) for item in items_existentes]
        if items_existentes else None
    )

    instruccion = INSTRUCCION_TC.format(hora=datetime.now().isoformat())
    mensajes = list(merge_message_runs(
        [SystemMessage(content=instruccion)] + state["messages"][:-1]
    ))

    extractor_recetas = create_extractor(
        _get_model(),
        tools=[Receta],
        tool_choice="Receta",
        enable_inserts=True,
    )

    resultado = extractor_recetas.invoke({
        "messages": mensajes,
        "existing": memorias_existentes,
    })

    for r, rmeta in zip(resultado["responses"], resultado["response_metadata"]):
        doc_id = rmeta.get("json_doc_id", str(uuid.uuid4()))
        if rmeta.get("deleted"):
            store.put(namespace, doc_id, None)
        else:
            store.put(namespace, doc_id, r.model_dump(mode="json"))

    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {"messages": [{"role": "tool", "content": "receta guardada", "tool_call_id": tool_call_id}]}


def actualizar_instrucciones_chef(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Actualiza las instrucciones personalizadas sobre cómo guardar recetas."""
    user_id = config["configurable"]["user_id"]
    namespace = ("instrucciones_chef", user_id)

    memoria_existente = store.get(namespace, "instrucciones_chef_usuario")
    system_msg = CREAR_INSTRUCCIONES_CHEF.format(
        instrucciones_actuales=(
            memoria_existente.value.get("memoria") if memoria_existente else None
        )
    )

    nueva_memoria = _get_model().invoke(
        [SystemMessage(content=system_msg)]
        + state["messages"][:-1]
        + [HumanMessage(content="Actualiza las instrucciones según esta conversación.")]
    )
    store.put(namespace, "instrucciones_chef_usuario", {"memoria": nueva_memoria.content})

    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {"messages": [{"role": "tool", "content": "instrucciones actualizadas", "tool_call_id": tool_call_id}]}


# ── Router ────────────────────────────────────────────────────────────────────

def enrutar_chef(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
) -> Literal["actualizar_perfil_chef", "actualizar_recetas_chef", "actualizar_instrucciones_chef", "__end__"]:
    """Enruta al nodo de memoria correspondiente según el tipo elegido por el agente."""
    mensaje = state["messages"][-1]
    if not getattr(mensaje, "tool_calls", None):
        return END
    tipo = mensaje.tool_calls[0]["args"]["tipo"]
    rutas = {
        "perfil": "actualizar_perfil_chef",
        "recetas": "actualizar_recetas_chef",
        "instrucciones": "actualizar_instrucciones_chef",
    }
    return rutas.get(tipo, END)


# ── Build graph ───────────────────────────────────────────────────────────────

def _build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node(chefsito)
    builder.add_node(actualizar_perfil_chef)
    builder.add_node(actualizar_recetas_chef)
    builder.add_node(actualizar_instrucciones_chef)

    builder.add_edge(START, "chefsito")
    builder.add_conditional_edges("chefsito", enrutar_chef)
    builder.add_edge("actualizar_perfil_chef", "chefsito")
    builder.add_edge("actualizar_recetas_chef", "chefsito")
    builder.add_edge("actualizar_instrucciones_chef", "chefsito")

    # When loaded by langgraph dev/Studio the platform rejects custom stores
    # (it injects its own). Only pass our SqliteChefStore when running normally.
    _in_studio = __name__ != "app.chef_agent"
    return builder.compile(store=None if _in_studio else chef_store)


# Module-level compiled graph (reused across requests)
chef_graph = _build_graph()


# ── Emotion inference ─────────────────────────────────────────────────────────

def _infer_emotion(text: str) -> str:
    """Simple heuristic to map response content to an emotion label."""
    lower = text.lower()
    if any(w in lower for w in ["guardé", "guardada", "guardado", "agregué", "añadí", "guardé"]):
        return "happy"
    if any(w in lower for w in ["increíble", "fantástic", "excelente", "¡qué bien", "genial", "delicioso"]):
        return "excited"
    if any(w in lower for w in ["no tengo", "no sé", "no encontré", "lo siento", "no puedo"]):
        return "sad"
    return "talking"


# ── Thread-pool executor for sync graph in async FastAPI ─────────────────────

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chefsito")


def _run_chef_sync(
    message: str,
    history: list[dict],
    user_id: str,
    image_base64: Optional[str],
    rag_context: str = "",
) -> tuple[str, str]:
    """Run the chef graph synchronously. Returns (response_text, emotion)."""
    # Convert DB history to LangChain messages (last 20 turns)
    lc_messages = []
    for msg in history[-20:]:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))

    # Build current user message (with optional image)
    if image_base64:
        try:
            user_content = [
                {"type": "text", "text": message or "Analiza esta imagen"},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_base64}"},
            ]
            lc_messages.append(HumanMessage(content=user_content))
        except Exception:
            lc_messages.append(HumanMessage(content=message))
    else:
        lc_messages.append(HumanMessage(content=message))

    config = {"configurable": {"user_id": user_id, "rag_context": rag_context}}
    result = chef_graph.invoke({"messages": lc_messages}, config)

    last_msg = result["messages"][-1]
    raw = last_msg.content if hasattr(last_msg, "content") else last_msg
    # content can be a list of parts (e.g. [{"type": "text", "text": "..."}])
    if isinstance(raw, list):
        response_text = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in raw
        ).strip()
    else:
        response_text = str(raw)
    emotion = _infer_emotion(response_text)
    return response_text, emotion


async def chat_with_chef(
    message: str,
    conversation_history: list[dict],
    user_id: str,
    image_base64: Optional[str] = None,
) -> tuple[str, list[str], str]:
    """Async entry point called from main.py — runs the LangGraph chef in a thread pool."""
    import asyncio

    # Search RAG (user PDFs + global knowledge) before entering the sync thread
    rag_results = await rag_service.search(message, user_id=user_id)
    rag_context = ""
    if rag_results:
        parts = [f"[Fuente: {r['source']}]\n{r['content']}" for r in rag_results]
        rag_context = "\n\n".join(parts)

    loop = asyncio.get_event_loop()
    response_text, emotion = await loop.run_in_executor(
        _executor, _run_chef_sync, message, conversation_history, user_id, image_base64, rag_context
    )
    logger.info(
        "[Chefsito] Response (%d chars, emotion=%s)", len(response_text), emotion
    )
    return response_text, [], emotion
