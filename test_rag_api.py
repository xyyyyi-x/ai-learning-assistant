from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

import api_app


@pytest.fixture
def fake_answer(monkeypatch):
    fake = Mock(return_value={
        "answer": "返回None。[1]",
        "sources": [
            {
                "reference_id": 1,
                "source": "python.md",
                "chunk_index": 1,
                "text": "普通函数没有显式返回值时返回None。",
            }
        ],
    })
    monkeypatch.setattr(
        api_app.rag_service,
        "answer_question",
        fake,
    )
    return fake


@pytest.fixture
def client(monkeypatch, tmp_path, fake_answer):
    monkeypatch.setattr(api_app, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(
        api_app, "KNOWLEDGE_DIR", tmp_path / "knowledge"
    )

    with TestClient(api_app.app) as test_client:
        yield test_client


def test_knowledge_success(client, fake_answer):
    response = client.post(
        "/ai/knowledge",
        json={
            "question": "  函数没有return时返回什么？  ",
            "keywords": "  函数 返回  ",
        },
    )

    assert response.status_code == 200
    assert response.json() == fake_answer.return_value

    fake_answer.assert_called_once_with(
        question="函数没有return时返回什么？",
        keywords="函数 返回",
        knowledge_dir=api_app.KNOWLEDGE_DIR,
    )


def test_knowledge_no_hits(client, fake_answer):
    fake_answer.return_value = {
        "answer": "未检索到相关资料，请调整关键词。",
        "sources": [],
    }

    response = client.post(
        "/ai/knowledge",
        json={"question": "火星基地如何供氧？", "keywords": "火星基地"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "未检索到相关资料，请调整关键词。",
        "sources": [],
    }


@pytest.mark.parametrize("req_json", [
    {},
    {"question": "   ", "keywords": "函数"},
    {"question": "问题", "keywords": "   "},
    {"question": "a" * 501, "keywords": "函数"},
    {"question": "问题", "keywords": "a" * 201},
])
def test_knowledge_invalid_input(client, fake_answer, req_json):
    response = client.post("/ai/knowledge", json=req_json)
    assert response.status_code == 422
    fake_answer.assert_not_called()


@pytest.mark.parametrize("exc_obj, expect_status, expect_detail", [
    (requests.exceptions.Timeout("模拟超时"), 504, "模型服务响应超时，请稍后重试"),
    (requests.exceptions.RequestException("模拟HTTP失败"), 502, "模型服务请求失败"),
    (ValueError("模拟无效回答"), 502, "暂时无法生成有效的资料回答"),
    (FileNotFoundError("资料目录不存在"), 500, "学习资料读取失败"),
])
def test_knowledge_exception(client, fake_answer, exc_obj, expect_status, expect_detail):
    fake_answer.side_effect = exc_obj
    response = client.post(
        "/ai/knowledge",
        json={"question": "函数返回什么？", "keywords": "函数"},
    )
    assert response.status_code == expect_status
    assert response.json()["detail"] == expect_detail
