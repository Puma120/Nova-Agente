"""Nova's tools — the actions the agent can take, surfaced to the user as live steps.

Each tool is a LangChain ``@tool``. Tools that need the current user read it from
the injected ``RunnableConfig`` (``config["configurable"]["user_id"]``), which keeps
``user_id`` out of the schema the LLM sees.
"""

import logging
from datetime import datetime, timedelta, timezone

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from . import google_calendar, memory_service, repo
from .db import AsyncSessionLocal
from .rag_service import rag_service

logger = logging.getLogger("nova-agent")


def _user_id(config: RunnableConfig) -> str:
    return config.get("configurable", {}).get("user_id", "")


@tool
def establecer_emocion(emocion: str) -> str:
    """Establece la emocion que Nova expresa al responder. Llama esta herramienta
    como PRIMERA accion en cada respuesta, antes de escribir el texto.

    Valores validos: neutral, happy, talking, sad, angry, surprised, excited, thinking.
    neutral=respuesta normal. happy=buenas noticias o ayuda exitosa.
    talking=explicacion larga o tecnica. sad=no sabe algo o hay un error.
    angry=detecta un bug o problema grave. surprised=dato inesperado o curioso.
    excited=logro del usuario o tema fascinante. thinking=esta razonando algo complejo."""
    return f"Emocion establecida: {emocion}"


@tool
async def buscar_en_conocimiento(query: str, config: RunnableConfig) -> str:
    """Busca informacion en la base de conocimiento y en los documentos que el usuario
    ha subido. Usala SIEMPRE que la pregunta pueda responderse con material del usuario
    (sus documentos, notas o base de conocimiento personal). Es el punto fuerte de Nova."""
    results = await rag_service.search(query, user_id=_user_id(config))
    if not results:
        return "Sin resultados relevantes en la base de conocimiento."
    return "\n\n".join(f"[Fuente: {r['source']}]\n{r['content']}" for r in results)


@tool
def guardar_en_memoria(categoria: str, clave: str, valor: str, config: RunnableConfig) -> str:
    """Guarda un dato del usuario en su memoria persistente (su 'gemelo digital').
    Usala cuando el usuario pida recordar algo, o cuando detectes informacion relevante
    sobre el: nombre, edad, gustos, metas, rutinas, datos personales, trabajo, etc.

    categoria: agrupador del dato. Ej: 'Datos personales', 'Preferencias', 'Metas',
      'Salud', 'Trabajo', 'Notas'.
    clave: nombre corto del dato. Ej: 'Nombre', 'Ciudad', 'Idioma preferido'.
    valor: el contenido a recordar."""
    memory_service.save_memory_entry(_user_id(config), categoria, clave, valor)
    return f"Guardado en memoria: {clave} = {valor}"


@tool
def eliminar_de_memoria(clave: str, config: RunnableConfig) -> str:
    """Elimina un dato de la memoria persistente del usuario cuando pida olvidarlo.

    clave: nombre del dato a eliminar (el mismo con el que se guardo)."""
    deleted = memory_service.delete_memory_entry(_user_id(config), clave)
    return "Eliminado de la memoria." if deleted else "No encontre ese dato en la memoria."


@tool
def guardar_preferencia_culinaria(preferencia: str, config: RunnableConfig) -> str:
    """Guarda una preferencia de cocina del usuario: gustos, alergias, dieta,
    ingredientes favoritos o que evita. Nova tambien es un gran asistente de cocina."""
    memory_service.save_memory_entry(_user_id(config), "Cocina", preferencia[:40], preferencia)
    return f"Preferencia culinaria guardada: {preferencia}"


@tool
def guardar_receta(nombre: str, contenido: str, config: RunnableConfig) -> str:
    """Guarda una receta en el recetario personal del usuario.

    nombre: nombre de la receta.
    contenido: ingredientes y pasos."""
    memory_service.save_memory_entry(_user_id(config), "Recetas", nombre, contenido)
    return f"Receta '{nombre}' guardada en tu recetario."


@tool
async def consultar_calendario(dias: int, config: RunnableConfig) -> str:
    """Consulta los proximos eventos del Google Calendar del usuario.

    dias: cuantos dias hacia adelante mirar (1 = hoy, 7 = esta semana)."""
    user_id = _user_id(config)
    async with AsyncSessionLocal() as session:
        events = await google_calendar.list_events(
            session, user_id,
            time_max=datetime.now(timezone.utc) + timedelta(days=max(dias, 1)),
        )
    if events is None:
        return ("El usuario aun no ha conectado su Google Calendar. Pidele que lo "
                "conecte desde el panel de integraciones.")
    if not events:
        return "No hay eventos en ese rango."
    lines = []
    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date", ""))
        lines.append(f"- {start}: {ev.get('summary', '(sin titulo)')}")
    return "\n".join(lines)


@tool
async def crear_evento_calendario(
    titulo: str, inicio: str, fin: str, descripcion: str, config: RunnableConfig
) -> str:
    """Crea un evento en el Google Calendar del usuario.

    titulo: nombre del evento.
    inicio / fin: fecha y hora en formato ISO 8601 (ej. 2026-05-20T15:00:00).
    descripcion: detalles del evento; pasa una cadena vacia si no hay."""
    user_id = _user_id(config)
    try:
        start_dt = datetime.fromisoformat(inicio)
        end_dt = datetime.fromisoformat(fin)
    except ValueError:
        return "Formato de fecha invalido. Usa ISO 8601, ej. 2026-05-20T15:00:00."
    async with AsyncSessionLocal() as session:
        event = await google_calendar.create_event(
            session, user_id, titulo, start_dt, end_dt, descripcion,
        )
    if event is None:
        return ("El usuario aun no ha conectado su Google Calendar. Pidele que lo "
                "conecte desde el panel de integraciones.")
    return f"Evento creado: {titulo} ({inicio})."


@tool
async def finalizar_onboarding(config: RunnableConfig) -> str:
    """Marca el onboarding del usuario como completado. Llamala UNA sola vez, cuando
    durante su primera conversacion ya hayas conocido lo basico del usuario (su nombre,
    a que se dedica, sus intereses) y lo hayas guardado en memoria."""
    async with AsyncSessionLocal() as session:
        await repo.set_onboarded(session, _user_id(config))
    return "Onboarding completado. El usuario ya esta listo para usar Nova."


# Human-readable labels for the live "agent steps" panel in the chat UI.
TOOL_LABELS = {
    "establecer_emocion": "Ajustando el tono",
    "buscar_en_conocimiento": "Buscando en tu base de conocimiento",
    "guardar_en_memoria": "Guardando en tu memoria",
    "eliminar_de_memoria": "Actualizando tu memoria",
    "guardar_preferencia_culinaria": "Recordando tus gustos de cocina",
    "guardar_receta": "Guardando la receta en tu recetario",
    "consultar_calendario": "Consultando tu Google Calendar",
    "crear_evento_calendario": "Creando un evento en tu calendario",
    "finalizar_onboarding": "Completando tu perfil",
}

NOVA_TOOLS = [
    establecer_emocion,
    buscar_en_conocimiento,
    guardar_en_memoria,
    eliminar_de_memoria,
    guardar_preferencia_culinaria,
    guardar_receta,
    consultar_calendario,
    crear_evento_calendario,
    finalizar_onboarding,
]
