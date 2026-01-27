from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ThinkingBlock:
    text: str
    type: Literal["thinking"] = "thinking"


@dataclass
class ToolUseBlock:
    text: str
    type: Literal["tool_use"] = "tool_use"


@dataclass
class ToolResultBlock:
    text: str
    type: Literal["tool_result"] = "tool_result"


@dataclass
class ContentBlock:
    text: str
    type: Literal["text"] = "text"


from typing import Union
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
