"""Memory Service — Persistent per-user markdown memory file."""

import logging
import os
import re
from pathlib import Path

from .config import settings

logger = logging.getLogger("nova-agent")


def _user_memory_path(user_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(user_id))
    return Path(settings.user_memory_dir) / f"{safe_id}.md"


def _parse_memory(content: str) -> dict[str, dict[str, str]]:
    """Parse markdown memory into {section: {key: value}}, preserving order."""
    result: dict[str, dict[str, str]] = {}
    current_section: str | None = None
    for line in content.splitlines():
        if line.startswith("## "):
            current_section = line[3:].strip()
            if current_section not in result:
                result[current_section] = {}
        elif current_section and line.startswith("- **"):
            match = re.match(r"- \*\*(.+?)\*\*: (.+)", line)
            if match:
                result[current_section][match.group(1)] = match.group(2).strip()
    return result


def _render_memory(data: dict[str, dict[str, str]]) -> str:
    """Render memory dict back to markdown."""
    lines = ["# Memoria del usuario", ""]
    for section, entries in data.items():
        if entries:
            lines.append(f"## {section}")
            for key, val in entries.items():
                lines.append(f"- **{key}**: {val}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def read_memory(user_id: str) -> str:
    """Return the full content of the user's memory file, or empty string."""
    path = _user_memory_path(user_id)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def save_memory_entry(user_id: str, categoria: str, clave: str, valor: str) -> None:
    """Upsert a key-value entry under a section in the user's memory file."""
    path = _user_memory_path(user_id)
    os.makedirs(path.parent, exist_ok=True)
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    data = _parse_memory(content)
    if categoria not in data:
        data[categoria] = {}
    data[categoria][clave] = valor
    path.write_text(_render_memory(data), encoding="utf-8")
    logger.info("[MemFile] Guardado [%s] %s = %s (usuario %s)", categoria, clave, valor, user_id)


def delete_memory_entry(user_id: str, clave: str) -> bool:
    """Remove an entry by key from the user's memory file. Returns True if found."""
    path = _user_memory_path(user_id)
    if not path.exists():
        return False
    data = _parse_memory(path.read_text(encoding="utf-8"))
    found = False
    for section in list(data.keys()):
        if clave in data[section]:
            del data[section][clave]
            found = True
            break
    if found:
        path.write_text(_render_memory(data), encoding="utf-8")
        logger.info("[MemFile] Eliminado '%s' (usuario %s)", clave, user_id)
    return found
