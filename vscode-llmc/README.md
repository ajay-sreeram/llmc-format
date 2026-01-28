# LLMC File Viewer

View and edit `.llmc` files - a markdown-based format for LLM conversations with **thinking tokens** and **tool calls**.

## Quick Example

```markdown
---
model: claude-opus-4-5
---

## user
What's 15 + 27?

## assistant

<think>
Simple addition: 15 + 27 = 42
</think>

The answer is **42**.

<tool_use id="calc_01" name="calculator">
{"expression": "15 + 27"}
</tool_use>

## user

<tool_result id="calc_01">
{"result": 42}
</tool_result>
```

## Features

- **Syntax Highlighting** - Role headers, thinking blocks, tool calls, markdown
- **Live Preview** - `Ctrl+Shift+P` → "LLMC: Open Preview"
- **Collapsible Thinking** - Expand/collapse reasoning blocks
- **Tool Call Display** - Shows tool names, IDs, and error states

## Supported Formats

| Provider | Thinking Tags | Status |
|----------|---------------|--------|
| DeepSeek R1 | `<think>...</think>` | Supported |
| Qwen/QwQ | `<think>...</think>` | Supported |
| Claude | `<thinking>...</thinking>` | Supported |

## Why LLMC?

- **Markdown-based** - Human readable, version control friendly
- **Nested code blocks** - Thinking can contain code snippets
- **Tool tracking** - Match tool calls with results via IDs
- **Provider agnostic** - Works with any LLM output

## Commands

| Command | Description |
|---------|-------------|
| `LLMC: Open Preview` | Side-by-side rendered preview |

## Links

- [GitHub Repository](https://github.com/ajay-sreeram/llmc-format)
- Python library: `pip install llmc-format`
