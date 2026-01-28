# llmc-format

Parser and writer for the `.llmc` (LLM Chat) file format — a Markdown-based format for representing LLM conversations with thinking tokens and tool calls.

Supports **DeepSeek R1**, **Qwen/QwQ**, and **Claude** thinking formats.

## Preview

![LLMC Preview](vscode-llmc/media/preview.png)

## Install

```bash
pip install -e .
```

## Usage

### Python API

```python
from llmc import parse, write, parse_file, write_file

# Parse from string or file
chat = parse_file("examples/tool_chat.llmc")

for msg in chat.messages:
    print(f"{msg.role}: {[b.type for b in msg.blocks]}")

# Access thinking and tool blocks
for block in msg.blocks:
    if block.type == "thinking":
        print(f"Thinking: {block.text[:50]}...")
    elif block.type == "tool_use":
        print(f"Tool: {block.name} (id={block.id})")

# Serialize back
text = write(chat)
```

### CLI

```bash
# Validate a file
python -m llmc validate examples/tool_chat.llmc
# Output: Valid .llmc file: 5 messages
#   assistant: ['thinking', 'text', 'tool_use(get_weather)', 'tool_use(calculator)']

# Convert JSON messages to .llmc
python -m llmc convert messages.json
```

## VS Code Extension

The **LLMC File Viewer** extension provides syntax highlighting and a rendered chat preview.

### Install

```bash
code --install-extension vscode-llmc/vscode-llmc-0.2.1.vsix
```

### Features

- Syntax highlighting for roles, thinking blocks, tool calls
- **LLMC: Open Preview** command (`Ctrl+Shift+P`)
- Collapsible thinking blocks with markdown rendering
- Tool calls with name, ID, and JSON formatting
- VS Code theme integration (dark/light)

## Format

```markdown
---
model: claude-opus-4-5
---

## user
What's 15 + 27?

## assistant

<think>
Let me calculate: 15 + 27 = 42
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

### Supported Formats

| Provider | Thinking Tags | Status |
|----------|---------------|--------|
| DeepSeek R1 | `<think>...</think>` | ✓ |
| Qwen/QwQ | `<think>...</think>` | ✓ |
| Claude | `<thinking>...</thinking>` | ✓ |
| Legacy | ` ```thinking ``` ` | ✓ |

See [examples/](examples/) for more samples.
