from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import (
    Block,
    Chat,
    ContentBlock,
    Message,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

_HEADER_RE = re.compile(r"^## (system|user|assistant)\s*$")
_FENCE_OPEN_RE = re.compile(r"^```(thinking|tool_use|tool_result)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^```\s*$")


def parse(text: str) -> Chat:
    """Parse an .llmc string into a Chat object."""
    metadata: dict[str, object] = {}
    body = text

    # Extract YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            metadata = yaml.safe_load(parts[1]) or {}
            body = parts[2]

    # Split into messages
    messages: list[Message] = []
    lines = body.split("\n")
    current_role: str | None = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_role, current_lines
        if current_role is not None:
            blocks = _parse_blocks(current_lines)
            messages.append(Message(role=current_role, blocks=blocks))  # type: ignore[arg-type]
        current_role = None
        current_lines = []

    for line in lines:
        m = _HEADER_RE.match(line)
        if m:
            flush()
            current_role = m.group(1)
        elif current_role is not None:
            current_lines.append(line)

    flush()

    return Chat(messages=messages, metadata=metadata)


def parse_file(path: str | Path) -> Chat:
    """Parse an .llmc file from disk."""
    return parse(Path(path).read_text(encoding="utf-8"))


def _parse_blocks(lines: list[str]) -> list[Block]:
    """Parse message body lines into a sequence of blocks."""
    blocks: list[Block] = []
    text_lines: list[str] = []
    fence_type: str | None = None
    fence_lines: list[str] = []

    def flush_text():
        content = "\n".join(text_lines).strip()
        if content:
            blocks.append(ContentBlock(text=content))
        text_lines.clear()

    for line in lines:
        if fence_type is None:
            m = _FENCE_OPEN_RE.match(line)
            if m:
                flush_text()
                fence_type = m.group(1)
                fence_lines = []
            else:
                text_lines.append(line)
        else:
            if _FENCE_CLOSE_RE.match(line):
                content = "\n".join(fence_lines)
                if fence_type == "thinking":
                    blocks.append(ThinkingBlock(text=content))
                elif fence_type == "tool_use":
                    blocks.append(ToolUseBlock(text=content))
                elif fence_type == "tool_result":
                    blocks.append(ToolResultBlock(text=content))
                fence_type = None
                fence_lines = []
            else:
                fence_lines.append(line)

    # Remaining text
    flush_text()

    return blocks
