from __future__ import annotations

from pathlib import Path

import yaml

from .models import Chat


def write(chat: Chat) -> str:
    """Serialize a Chat object to .llmc format string."""
    parts: list[str] = []

    if chat.metadata:
        parts.append("---")
        parts.append(yaml.dump(chat.metadata, default_flow_style=False).strip())
        parts.append("---")
        parts.append("")

    for msg in chat.messages:
        parts.append(f"## {msg.role}")
        parts.append("")
        for block in msg.blocks:
            if block.type == "text":
                parts.append(block.text)
            else:
                parts.append(f"```{block.type}")
                parts.append(block.text)
                parts.append("```")
            parts.append("")

    return "\n".join(parts)


def write_file(chat: Chat, path: str | Path) -> None:
    """Write a Chat object to an .llmc file on disk."""
    Path(path).write_text(write(chat), encoding="utf-8")
