# llmc-format

Parser and writer for the `.llmc` (LLM Chat) file format — a Markdown-based format for representing LLM conversations with thinking tokens.

## Install

```bash
pip install -e .
```

## Usage

### Python API

```python
from llmc import parse, write, parse_file, write_file

# Parse from string or file
chat = parse_file("examples/thinking_chat.llmc")

for msg in chat.messages:
    print(f"{msg.role}: {msg.text}")

# Serialize back
text = write(chat)
```

### CLI

```bash
# Validate a file
llmc validate examples/thinking_chat.llmc

# Convert JSON messages to .llmc
llmc convert messages.json
```

## Format

See [SPEC.md](SPEC.md) for the full specification.

```markdown
---
model: claude-opus-4-5-20251101
timestamp: 2026-01-27T10:00:00Z
---

## user

What is 2+2?

## assistant

\```thinking
The user is asking a simple arithmetic question.
\```

The answer is **4**.
```
