"""Vision — standalone image interpretation, used by the /vision/interpret endpoint."""

from langchain_core.messages import HumanMessage, SystemMessage

from .llm_provider import get_llm


async def interpret_image(image_base64: str, instruction: str = "") -> str:
    prompt = instruction or (
        "Analiza esta imagen. Describe lo que ves e interpreta cualquier texto o dato relevante."
    )
    system = SystemMessage(
        content="Eres Nova, un asistente visual. Analiza imagenes y describe su contenido de forma clara y util."
    )
    user_msg = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
    ])
    response = await get_llm().ainvoke([system, user_msg])
    raw = response.content
    if isinstance(raw, list):
        return " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in raw
        ).strip()
    return str(raw)
