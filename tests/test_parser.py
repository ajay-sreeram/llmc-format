from pathlib import Path

from llmc import Chat, ContentBlock, Message, ThinkingBlock, parse, write


EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_parse_simple():
    chat = parse(EXAMPLES.joinpath("simple_chat.llmc").read_text())
    assert len(chat.messages) == 3
    assert chat.messages[0].role == "system"
    assert chat.messages[1].role == "user"
    assert chat.messages[2].role == "assistant"
    assert "Paris" in chat.messages[2].text


def test_parse_thinking():
    chat = parse(EXAMPLES.joinpath("thinking_chat.llmc").read_text())
    assistant = chat.messages[2]
    assert any(b.type == "thinking" for b in assistant.blocks)
    assert any(b.type == "text" for b in assistant.blocks)
    thinking = [b for b in assistant.blocks if b.type == "thinking"][0]
    assert "2+2=4" in thinking.text


def test_metadata():
    chat = parse(EXAMPLES.joinpath("simple_chat.llmc").read_text())
    assert chat.metadata["model"] == "claude-opus-4-5-20251101"


def test_round_trip():
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
