import pytest

from knowledge_retriever import search_chunks


def test_rank_by_keyword_matches():
    chunks = [
        {
            "source": "a.md",
            "chunk_index": 1,
            "text": "Python基础",
        },
        {
            "source": "b.md",
            "chunk_index": 1,
            "text": "Python函数参数",
        },
        {
            "source": "c.md",
            "chunk_index": 1,
            "text": "HTTP状态码",
        },
    ]

    result = search_chunks(chunks, "Python 参数")

    assert [item["source"] for item in result] == ["b.md", "a.md"]
    assert [item["score"] for item in result] == [2, 1]
    assert result[0]["text"] == "Python函数参数"
    assert result[0]["chunk_index"] == 1

    # 检索不能给原始资料添加分数
    assert all("score" not in chunk for chunk in chunks)


def test_case_insensitive_and_duplicate_keywords():
    chunks = [
        {"source": "a.md", "chunk_index": 1, "text": "Python Python"},
    ]

    result = search_chunks(chunks, "PYTHON python")

    assert [item["score"] for item in result] == [1]


def test_top_k_and_stable_order():
    chunks = [
        {"source": "a.md", "chunk_index": 1, "text": "函数基础"},
        {"source": "b.md", "chunk_index": 1, "text": "函数返回值"},
        {"source": "c.md", "chunk_index": 1, "text": "函数参数"},
    ]

    result = search_chunks(chunks, "函数", top_k=2)

    assert [item["source"] for item in result] == ["a.md", "b.md"]
    assert [item["score"] for item in result] == [1, 1]


def test_no_results():
    chunks = [
        {"source": "a.md", "chunk_index": 1, "text": "HTTP状态码"},
    ]

    assert search_chunks(chunks, "Python") == []
    assert search_chunks(chunks, "   ") == []
    assert search_chunks([], "Python") == []


@pytest.mark.parametrize("top_k", [0, -1])
def test_invalid_top_k(top_k):
    with pytest.raises(ValueError):
        search_chunks(
            [{"source": "a.md", "chunk_index": 1, "text": "Python"}],
            "Python",
            top_k=top_k,
        )


@pytest.mark.parametrize(
    "query",
    [
        "函数 return",
        "函数，return",
        "函数,return",
        "函数、return",
        "函数；return",
        "函数;return",
    ],
)
def test_separators_split_keywords(query):
    """空格、逗号、顿号和分号都应当作为关键词分隔符。

    正文同时含"函数"和"return"，各种写法都应命中同一条片段，得分为 2。
    """
    chunks = [
        {
            "source": "a.md",
            "chunk_index": 1,
            "text": "函数没有显式返回值时返回None，函数用return交回结果。",
        },
    ]

    result = search_chunks(chunks, query)

    assert len(result) == 1
    assert result[0]["score"] == 2
