# `.llmc` File Format Specification

**Version:** 1.0

## Overview

`.llmc` (LLM Chat) is a Markdown-based file format for representing LLM conversations, including thinking/reasoning tokens. Files are human-readable as plain Markdown and machine-parseable.

## Structure

An `.llmc` file consists of:

1. **YAML frontmatter** (optional) — metadata enclosed in `---` fences
2. **Messages** — delimited by H2 headers (`## role`)

### Frontmatter

Optional YAML block at the start of the file:

```yaml
---
model: claude-opus-4-5-20251101
timestamp: 2026-01-27T10:00:00Z
---
```

Any key-value pairs are allowed. `model` and `timestamp` are conventional.

### Messages

Each message starts with an H2 header containing the role:

```markdown
## system

You are a helpful assistant.

## user

What is 2+2?

## assistant

The answer is **4**.
```

Valid roles: `system`, `user`, `assistant`.

### Thinking Blocks

Inside assistant messages, thinking/reasoning tokens are represented as fenced code blocks with the `thinking` info string:

````markdown
## assistant

```thinking
Let me reason about this step by step...
```

Here is my response.
````

### Tool Use and Tool Results (Optional)

Tool interactions use fenced code blocks with `tool_use` or `tool_result` info strings. Content is JSON.

````markdown
```tool_use
{"name": "calculator", "input": {"expression": "2+2"}}
```

```tool_result
{"output": "4"}
```
````

## Parsing Rules

1. Split the file at lines matching `^## (system|user|assistant)\s*$`.
2. Everything before the first H2 header (after frontmatter) is ignored.
3. Within each message, identify fenced blocks by matching opening `` ```thinking ``, `` ```tool_use ``, `` ```tool_result `` and closing `` ``` `` lines.
4. All other content within a message is plain text/Markdown content.
5. A message may contain multiple content blocks (text, thinking, tool_use, tool_result) in order.

## File Extension

`.llmc`

## MIME Type (Conventional)

`text/markdown` (with `.llmc` extension for identification)
