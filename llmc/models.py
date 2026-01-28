from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Union


@dataclass
class ThinkingBlock:
    """Reasoning/chain-of-thought content from the model."""
    text: str
    type: Literal["thinking"] = "thinking"


@dataclass
class ToolUseBlock:
    """Tool/function call made by the model."""
    text: str  # JSON content (parameters/input)
    type: Literal["tool_use"] = "tool_use"
    id: Optional[str] = None  # Unique identifier for matching results
    name: Optional[str] = None  # Tool/function name


@dataclass
class ToolResultBlock:
    """Result returned from a tool execution."""
    text: str  # JSON content (output)
    type: Literal["tool_result"] = "tool_result"
    id: Optional[str] = None  # Matches the tool_use id
    is_error: bool = False  # Whether the tool execution failed


@dataclass
class ContentBlock:
    """Regular text/markdown content."""
    text: str
    type: Literal["text"] = "text"


Block = Union[ThinkingBlock, ToolUseBlock, ToolResultBlock, ContentBlock]


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Return concatenated text content (non-thinking, non-tool blocks)."""
        return "\n\n".join(b.text for b in self.blocks if b.type == "text")


@dataclass
class Chat:
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
