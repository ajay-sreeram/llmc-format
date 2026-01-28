from __future__ import annotations

from pathlib import Path

import yaml

from .models import Chat, ToolUseBlock, ToolResultBlock


def write(chat: Chat) -> str:
    """Serialize a Chat object to .llmc format string.

    Uses XML-style tags for thinking and tool blocks (handles nested markdown).
    """
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
            elif block.type == "thinking":
                parts.append("<think>")
                parts.append(block.text)
                parts.append("</think>")
            elif block.type == "tool_use":
                # Build tag with optional attributes
                attrs = _build_tool_use_attrs(block)
                parts.append(f"<tool_use{attrs}>")
                parts.append(block.text)
                parts.append("</tool_use>")
            elif block.type == "tool_result":
                # Build tag with optional attributes
                attrs = _build_tool_result_attrs(block)
                parts.append(f"<tool_result{attrs}>")
                parts.append(block.text)
                parts.append("</tool_result>")
            parts.append("")

    return "\n".join(parts)


def _build_tool_use_attrs(block: ToolUseBlock) -> str:
    """Build attribute string for tool_use tag."""
    attrs = []
    if block.id:
        attrs.append(f'id="{block.id}"')
    if block.name:
        attrs.append(f'name="{block.name}"')
    return (" " + " ".join(attrs)) if attrs else ""


def _build_tool_result_attrs(block: ToolResultBlock) -> str:
    """Build attribute string for tool_result tag."""
    attrs = []
    if block.id:
        attrs.append(f'id="{block.id}"')
    if block.is_error:
        attrs.append('is_error="true"')
    return (" " + " ".join(attrs)) if attrs else ""


def write_file(chat: Chat, path: str | Path) -> None:
    """Write a Chat object to an .llmc file on disk."""
    Path(path).write_text(write(chat), encoding="utf-8")
