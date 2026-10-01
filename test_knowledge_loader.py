import pytest

from knowledge_loader import load_markdown_documents


def test_load_markdown(tmp_path):
    path = tmp_path / "python.md"
    path.write_text("  函数通过return返回结果。  ", encoding="utf-8")

    result = load_markdown_documents(tmp_path)

    assert result == [
        {
            "source": "python.md",
            "text": "函数通过return返回结果。",
        }
    ]


def test_filter_and_sort(tmp_path):
    (tmp_path / "b.md").write_text("# 第二个", encoding="utf-8")
    (tmp_path / "a.md").write_text("# 第一个", encoding="utf-8")
    (tmp_path / "empty.md").write_text("   \n  ", encoding="utf-8")
    (tmp_path / "note.txt").write_text("不是Markdown", encoding="utf-8")

    result = load_markdown_documents(tmp_path)

    assert [doc["source"] for doc in result] == ["a.md", "b.md"]


def test_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_markdown_documents(tmp_path / "missing")


def test_path_is_not_directory(tmp_path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("内容", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        load_markdown_documents(file_path)
