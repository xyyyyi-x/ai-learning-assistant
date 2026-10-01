import pytest

from rag_prompt import SYSTEM_PROMPT, build_rag_messages


def test_build_messages():
    chunks = [
        {
            "source": "python.md",
            "chunk_index": 3,
            "text": "没有显式返回值时，普通函数返回None。",
            "score": 1,
        }
    ]

    messages = build_rag_messages("  函数返回什么？  ", chunks)

    assert messages == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "用户问题：\n函数返回什么？\n\n"
                "参考资料：\n"
                "[1] 来源：python.md；片段：3\n"
                "没有显式返回值时，普通函数返回None。"
            ),
        },
    ]


def test_two_chunks_and_no_mutation():
    chunks = [
        {"source": "a.md", "chunk_index": 1, "text": "第一段正文", "score": 2},
        {"source": "b.md", "chunk_index": 5, "text": "第二段正文", "score": 1},
    ]
    original = [dict(chunk) for chunk in chunks]

    messages = build_rag_messages("问题", chunks)

    content = messages[1]["content"]
    assert "[1] 来源：a.md；片段：1\n第一段正文" in content
    assert "[2] 来源：b.md；片段：5\n第二段正文" in content
    assert content.index("[1]") < content.index("[2]")

    assert chunks == original


def test_blank_question():
    chunks = [
        {"source": "a.md", "chunk_index": 1, "text": "正文", "score": 1},
    ]

    with pytest.raises(ValueError, match="问题不能为空"):
        build_rag_messages("   ", chunks)


def test_empty_chunks():
    with pytest.raises(ValueError, match="参考资料不能为空"):
        build_rag_messages("问题", [])
