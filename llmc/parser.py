from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

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

# Legacy fence patterns (backward compatibility)
_FENCE_OPEN_RE = re.compile(r"^```(thinking|tool_use|tool_result)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^```\s*$")

# XML-style tag patterns (primary format)
# Thinking: <think> or <thinking>
_THINK_OPEN_RE = re.compile(r"^<(think|thinking)>\s*$")
_THINK_CLOSE_RE = re.compile(r"^</(think|thinking)>\s*$")

# Tool use: <tool_use id="..." name="...">
_TOOL_USE_OPEN_RE = re.compile(
    r'^<tool_use(?:\s+id=["\']([^"\']*)["\'])?(?:\s+name=["\']([^"\']*)["\'])?\s*>\s*$'
)
_TOOL_USE_CLOSE_RE = re.compile(r"^</tool_use>\s*$")

# Tool result: <tool_result id="..." is_error="true">
_TOOL_RESULT_OPEN_RE = re.compile(
    r'^<tool_result(?:\s+id=["\']([^"\']*)["\'])?(?:\s+is_error=["\']([^"\']*)["\'])?\s*>\s*$'
)
_TOOL_RESULT_CLOSE_RE = re.compile(r"^</tool_result>\s*$")


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
    """Parse message body lines into a sequence of blocks.

    Supports both XML-style tags (primary) and legacy fenced blocks (backward compat).
    """
    blocks: list[Block] = []
    text_lines: list[str] = []

    # State for block parsing
    block_type: str | None = None  # 'thinking', 'tool_use', 'tool_result'
    block_style: str | None = None  # 'xml' or 'fence'
    block_lines: list[str] = []
    block_attrs: dict[str, Optional[str]] = {}

    def flush_text():
        content = "\n".join(text_lines).strip()
        if content:
            blocks.append(ContentBlock(text=content))
        text_lines.clear()

    def create_block(btype: str, content: str, attrs: dict) -> Block:
        """Create the appropriate block type with attributes."""
        if btype == "thinking":
            return ThinkingBlock(text=content)
        elif btype == "tool_use":
            return ToolUseBlock(
                text=content,
                id=attrs.get("id"),
                name=attrs.get("name"),
            )
        elif btype == "tool_result":
            is_error_val = attrs.get("is_error") or ""
            return ToolResultBlock(
                text=content,
                id=attrs.get("id"),
                is_error=is_error_val.lower() == "true",
            )
        else:
            return ContentBlock(text=content)

    i = 0
    while i < len(lines):
        line = lines[i]

        if block_type is None:
            # Not inside a block - check for opening tags/fences

            # Check XML-style thinking tag
            m = _THINK_OPEN_RE.match(line)
            if m:
                flush_text()
                block_type = "thinking"
                block_style = "xml"
                block_lines = []
                block_attrs = {}
                i += 1
                continue

            # Check XML-style tool_use tag
            m = _TOOL_USE_OPEN_RE.match(line)
            if m:
                flush_text()
                block_type = "tool_use"
                block_style = "xml"
                block_lines = []
                block_attrs = {"id": m.group(1), "name": m.group(2)}
                i += 1
                continue

            # Check XML-style tool_result tag
            m = _TOOL_RESULT_OPEN_RE.match(line)
            if m:
                flush_text()
                block_type = "tool_result"
                block_style = "xml"
                block_lines = []
                block_attrs = {"id": m.group(1), "is_error": m.group(2)}
                i += 1
                continue

            # Check legacy fence opening
            m = _FENCE_OPEN_RE.match(line)
            if m:
                flush_text()
                block_type = m.group(1)
                block_style = "fence"
                block_lines = []
                block_attrs = {}
                i += 1
                continue

            # Regular text line
            text_lines.append(line)
            i += 1

        else:
            # Inside a block - look for closing tag/fence
            closed = False

            if block_style == "xml":
                if block_type == "thinking" and _THINK_CLOSE_RE.match(line):
                    closed = True
                elif block_type == "tool_use" and _TOOL_USE_CLOSE_RE.match(line):
                    closed = True
                elif block_type == "tool_result" and _TOOL_RESULT_CLOSE_RE.match(line):
                    closed = True
            elif block_style == "fence":
                if _FENCE_CLOSE_RE.match(line):
                    closed = True

            if closed:
                content = "\n".join(block_lines)
                blocks.append(create_block(block_type, content, block_attrs))
                block_type = None
                block_style = None
                block_lines = []
                block_attrs = {}
            else:
                block_lines.append(line)

            i += 1

    # Remaining text
    flush_text()

    return blocks
