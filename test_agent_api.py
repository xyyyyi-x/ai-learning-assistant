from unittest.mock import Mock
import pytest
import requests
from fastapi.testclient import TestClient

import api_app


@pytest.fixture
def fake_run(monkeypatch):
    fake = Mock(return_value="你还有一条未完成任务。")
    monkeypatch.setattr(
        api_app.langchain_service,
        "run_langchain_assistant",
        fake,
    )
    return fake


@pytest.fixture
def client(monkeypatch, tmp_path, fake_run):
    # 替换全局DB_PATH，放在TestClient前面
    monkeypatch.setattr(
        api_app,
        "DB_PATH",
        tmp_path / "test_agent.db",
    )
    with TestClient(api_app.app) as test_client:
        yield test_client


# 1. 正常请求测试
def test_assistant_success(client, fake_run):
    response = client.post(
        "/ai/assistant",
        json={"goal": "  查看未完成任务  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "你还有一条未完成任务。",
    }

    fake_run.assert_called_once_with(
        goal="查看未完成任务",
        db_path=api_app.DB_PATH,
    )


# A. 参数化：非法输入，不执行run_assistant，返回422
@pytest.mark.parametrize(
    "req_json",
    [
        {},
        {"goal": ""},
        {"goal": "   "},
        {"goal": "a" * 201},
    ],
)
def test_assistant_invalid_input(client, fake_run, req_json):
    response = client.post("/ai/assistant", json=req_json)
    assert response.status_code == 422
    fake_run.assert_not_called()


# B. 参数化：run_assistant抛出各类异常，转为对应HTTP错误
@pytest.mark.parametrize(
    "exc_obj, expect_status, expect_detail",
    [
        (requests.exceptions.Timeout("模拟超时"), 504, "模型服务响应超时，请稍后重试"),
        (requests.exceptions.RequestException("模拟HTTP失败"), 502, "模型服务请求失败"),
        (ValueError("模拟无效回答"), 502, "暂时无法完成任务查询"),
        (RuntimeError("超过模型调用次数上限"), 502, "任务查询超过调用次数上限"),
    ],
)
def test_assistant_exception(client, fake_run, exc_obj, expect_status, expect_detail):
    fake_run.side_effect = exc_obj
    response = client.post("/ai/assistant", json={"goal": "查看任务"})
    assert response.status_code == expect_status
    resp_data = response.json()
    assert resp_data["detail"] == expect_detail
