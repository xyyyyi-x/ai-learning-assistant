from unittest.mock import Mock

import pytest
import requests
import rag_service


def test_answer_with_sources(tmp_path, monkeypatch):
    (tmp_path / "python.md").write_text(
        "函数没有显式返回值时返回None。",
        encoding="utf-8",
    )

    fake_answer = Mock(return_value="返回None。[1]")
    monkeypatch.setattr(
        rag_service.rag_model_client,
        "generate_rag_answer",
        fake_answer,
    )

    result = rag_service.answer_question(
        "  没有return时返回什么？  ",
        "  函数  ",
        tmp_path,
    )

    assert result == {
        "answer": "返回None。[1]",
        "sources": [
            {
                "reference_id": 1,
                "source": "python.md",
                "chunk_index": 1,
                "text": "函数没有显式返回值时返回None。",
            }
        ],
    }

    fake_answer.assert_called_once_with(
        "没有return时返回什么？",
        [
            {
                "source": "python.md",
                "chunk_index": 1,
                "text": "函数没有显式返回值时返回None。",
                "score": 1,
            }
        ],
    )


def test_no_hits(tmp_path, monkeypatch):
    (tmp_path / "python.md").write_text("函数基础", encoding="utf-8")

    fake_answer = Mock()
    monkeypatch.setattr(
        rag_service.rag_model_client,
        "generate_rag_answer",
        fake_answer,
    )

    result = rag_service.answer_question(
        "火星基地如何供氧？",
        "火星基地",
        tmp_path,
    )

    assert result == {
        "answer": "未检索到相关资料，请调整关键词。",
        "sources": [],
    }
    fake_answer.assert_not_called()


@pytest.mark.parametrize("question, keywords", [
    ("   ", "函数"),
    ("问题", "   "),
])
def test_blank_input(tmp_path, monkeypatch, question, keywords):
    fake_answer = Mock()
    monkeypatch.setattr(
        rag_service.rag_model_client,
        "generate_rag_answer",
        fake_answer,
    )

    with pytest.raises(ValueError, match="问题和检索关键词不能为空"):
        rag_service.answer_question(question, keywords, tmp_path)

    fake_answer.assert_not_called()


def test_model_timeout(tmp_path, monkeypatch):
    (tmp_path / "python.md").write_text("函数基础", encoding="utf-8")

    fake_answer = Mock(side_effect=requests.exceptions.Timeout("模拟超时"))
    monkeypatch.setattr(
        rag_service.rag_model_client,
        "generate_rag_answer",
        fake_answer,
    )

    with pytest.raises(requests.exceptions.Timeout) as exc_info:
        rag_service.answer_question(
            "函数是什么？",
            "函数",
            tmp_path,
        )

    assert "模拟超时" in str(exc_info.value)
    fake_answer.assert_called_once()
