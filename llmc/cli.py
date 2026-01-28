from __future__ import annotations

import argparse
import json
import sys

from .models import Chat, ContentBlock, Message
from .parser import parse, parse_file
from .writer import write


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        chat = parse_file(args.file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    n = len(chat.messages)
    print(f"Valid .llmc file: {n} message{'s' if n != 1 else ''}")
    if chat.metadata:
        print(f"  metadata: {list(chat.metadata.keys())}")
    for msg in chat.messages:
        block_info = []
        for b in msg.blocks:
            if b.type == "tool_use":
                label = f"tool_use({b.name})" if b.name else "tool_use"
                block_info.append(label)
            elif b.type == "tool_result":
                label = "tool_error" if b.is_error else "tool_result"
                block_info.append(label)
            else:
                block_info.append(b.type)
        print(f"  {msg.role}: {block_info}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """Convert a JSON messages array to .llmc format."""
    try:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}", file=sys.stderr)
        return 1

    messages_data = data if isinstance(data, list) else data.get("messages", [])
    messages = []
    for m in messages_data:
        role = m.get("role", "user")
        content = m.get("content", "")
        messages.append(Message(role=role, blocks=[ContentBlock(text=content)]))

    chat = Chat(messages=messages)
    print(write(chat))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="llmc", description="LLM Chat file tool")
    sub = parser.add_subparsers(dest="command")

    p_val = sub.add_parser("validate", help="Validate an .llmc file")
    p_val.add_argument("file", help="Path to .llmc file")

    p_conv = sub.add_parser("convert", help="Convert JSON messages to .llmc")
    p_conv.add_argument("file", help="Path to JSON file")

    args = parser.parse_args()
    if args.command == "validate":
        return cmd_validate(args)
    elif args.command == "convert":
        return cmd_convert(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
