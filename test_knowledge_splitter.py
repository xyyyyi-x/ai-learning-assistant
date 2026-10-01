import pytest

from knowledge_splitter import split_documents


def test_split_long_document():
    documents = [
        {"source": "demo.md", "text": "abcdefghij"}
    ]

    result = split_documents(documents, chunk_size=4)

    assert result == [
        {"source": "demo.md", "chunk_index": 1, "text": "abcd"},
        {"source": "demo.md", "chunk_index": 2, "text": "efgh"},
        {"source": "demo.md", "chunk_index": 3, "text": "ij"},
    ]


def test_multiple_documents_boundary():
    documents = [
        {"source": "a.md", "text": "abcd"},
        {"source": "b.md", "text": "xy"},
    ]

    result = split_documents(documents, chunk_size=4)

    assert result == [
        {"source": "a.md", "chunk_index": 1, "text": "abcd"},
        {"source": "b.md", "chunk_index": 1, "text": "xy"},
    ]


def test_empty_documents_and_empty_text():
    assert split_documents([], chunk_size=4) == []

    result = split_documents(
        [{"source": "empty.md", "text": ""}],
        chunk_size=4,
    )
    assert result == []


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_invalid_chunk_size(chunk_size):
    with pytest.raises(ValueError):
        split_documents(
            [{"source": "demo.md", "text": "abc"}],
            chunk_size=chunk_size,
        )
