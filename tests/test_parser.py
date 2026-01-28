from pathlib import Path

from llmc import (
    Chat,
    ContentBlock,
    Message,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    parse,
    write,
)


EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_parse_simple():
    chat = parse(EXAMPLES.joinpath("simple_chat.llmc").read_text())
    assert len(chat.messages) == 3
    assert chat.messages[0].role == "system"
    assert chat.messages[1].role == "user"
    assert chat.messages[2].role == "assistant"
    assert "Paris" in chat.messages[2].text


def test_parse_thinking_legacy_fence():
    """Test legacy fence-style thinking blocks (backward compatibility)."""
    chat = parse(EXAMPLES.joinpath("thinking_chat.llmc").read_text())
    assistant = chat.messages[2]
    assert any(b.type == "thinking" for b in assistant.blocks)
    assert any(b.type == "text" for b in assistant.blocks)
    thinking = [b for b in assistant.blocks if b.type == "thinking"][0]
    assert "2+2=4" in thinking.text


def test_parse_thinking_xml_style():
    """Test XML-style <think> tags."""
    text = """## assistant

<think>
Let me think about this step by step.
The answer is 42.
</think>

The answer is **42**.
"""
    chat = parse(text)
    assistant = chat.messages[0]
    assert len(assistant.blocks) == 2
    assert assistant.blocks[0].type == "thinking"
    assert "step by step" in assistant.blocks[0].text
    assert assistant.blocks[1].type == "text"


def test_parse_thinking_with_nested_markdown():
    """Test that thinking blocks can contain markdown code fences."""
    text = """## assistant

<think>
Let me write some code:

```python
x = 2 + 2
print(x)  # 4
```

So the answer is 4.
</think>

The answer is **4**.
"""
    chat = parse(text)
    assistant = chat.messages[0]
    thinking = assistant.blocks[0]
    assert thinking.type == "thinking"
    assert "```python" in thinking.text
    assert "print(x)" in thinking.text


def test_parse_tool_use_with_attributes():
    """Test tool_use blocks with id and name attributes."""
    text = """## assistant

<tool_use id="toolu_123" name="calculator">
{"expression": "2+2"}
</tool_use>
"""
    chat = parse(text)
    tool_use = chat.messages[0].blocks[0]
    assert tool_use.type == "tool_use"
    assert tool_use.id == "toolu_123"
    assert tool_use.name == "calculator"
    assert "expression" in tool_use.text


def test_parse_tool_result_with_attributes():
    """Test tool_result blocks with id and is_error attributes."""
    text = """## user

<tool_result id="toolu_123">
{"result": 4}
</tool_result>
"""
    chat = parse(text)
    tool_result = chat.messages[0].blocks[0]
    assert tool_result.type == "tool_result"
    assert tool_result.id == "toolu_123"
    assert tool_result.is_error is False


def test_parse_tool_result_error():
    """Test tool_result with is_error=true."""
    text = """## user

<tool_result id="toolu_456" is_error="true">
{"error": "Connection timeout"}
</tool_result>
"""
    chat = parse(text)
    tool_result = chat.messages[0].blocks[0]
    assert tool_result.type == "tool_result"
    assert tool_result.id == "toolu_456"
    assert tool_result.is_error is True


def test_parse_tool_chat_example():
    """Test the comprehensive tool_chat.llmc example."""
    chat = parse(EXAMPLES.joinpath("tool_chat.llmc").read_text())
    assert len(chat.messages) == 5

    # Check assistant message with thinking and tool calls
    assistant = chat.messages[2]
    thinking_blocks = [b for b in assistant.blocks if b.type == "thinking"]
    tool_use_blocks = [b for b in assistant.blocks if b.type == "tool_use"]

    assert len(thinking_blocks) == 1
    assert "```python" in thinking_blocks[0].text  # Nested code block
    assert len(tool_use_blocks) == 2

    # Check tool use attributes
    weather_tool = tool_use_blocks[0]
    assert weather_tool.id == "toolu_01"
    assert weather_tool.name == "get_weather"

    calc_tool = tool_use_blocks[1]
    assert calc_tool.id == "toolu_02"
    assert calc_tool.name == "calculator"

    # Check tool results
    user_with_results = chat.messages[3]
    tool_results = [b for b in user_with_results.blocks if b.type == "tool_result"]
    assert len(tool_results) == 2
    assert tool_results[0].id == "toolu_01"
    assert tool_results[1].id == "toolu_02"


def test_metadata():
    chat = parse(EXAMPLES.joinpath("simple_chat.llmc").read_text())
    assert chat.metadata["model"] == "claude-opus-4-5-20251101"


def test_round_trip():
    """Test that parse -> write -> parse produces equivalent results."""
    original_text = EXAMPLES.joinpath("thinking_chat.llmc").read_text()
    chat = parse(original_text)
    output = write(chat)
    chat2 = parse(output)
    assert len(chat2.messages) == len(chat.messages)
    for m1, m2 in zip(chat.messages, chat2.messages):
        assert m1.role == m2.role
        assert len(m1.blocks) == len(m2.blocks)
        for b1, b2 in zip(m1.blocks, m2.blocks):
            assert b1.type == b2.type
            assert b1.text == b2.text


def test_round_trip_with_tools():
    """Test round trip with tool blocks preserving attributes."""
    chat = Chat(
        messages=[
            Message(
                role="assistant",
                blocks=[
                    ToolUseBlock(text='{"x": 1}', id="tool_1", name="test_tool"),
                ],
            ),
            Message(
                role="user",
                blocks=[
                    ToolResultBlock(text='{"result": 42}', id="tool_1", is_error=False),
                ],
            ),
        ]
    )
    output = write(chat)
    chat2 = parse(output)

    tool_use = chat2.messages[0].blocks[0]
    assert tool_use.id == "tool_1"
    assert tool_use.name == "test_tool"

    tool_result = chat2.messages[1].blocks[0]
    assert tool_result.id == "tool_1"
    assert tool_result.is_error is False


def test_empty_metadata():
    text = "## user\n\nHello\n"
    chat = parse(text)
    assert chat.metadata == {}
    assert len(chat.messages) == 1


def test_programmatic_construction():
    chat = Chat(
        messages=[
            Message(role="user", blocks=[ContentBlock(text="Hi")]),
            Message(
                role="assistant",
                blocks=[
                    ThinkingBlock(text="Greeting detected."),
                    ContentBlock(text="Hello!"),
                ],
            ),
        ]
    )
    output = write(chat)
    chat2 = parse(output)
    assert chat2.messages[1].blocks[0].type == "thinking"
    assert chat2.messages[1].blocks[1].text == "Hello!"


def test_both_think_and_thinking_tags():
    """Test that both <think> and <thinking> tags work."""
    text1 = "## assistant\n\n<think>\nThought 1\n</think>\n\nResponse"
    text2 = "## assistant\n\n<thinking>\nThought 2\n</thinking>\n\nResponse"

    chat1 = parse(text1)
    chat2 = parse(text2)

    assert chat1.messages[0].blocks[0].type == "thinking"
    assert chat2.messages[0].blocks[0].type == "thinking"
    assert "Thought 1" in chat1.messages[0].blocks[0].text
    assert "Thought 2" in chat2.messages[0].blocks[0].text
