from unittest.mock import Mock
import pytest
import requests
from fastapi.testclient import TestClient
import api_app


@pytest.fixture
def fake_generate(monkeypatch):
    fake = Mock(return_value=["练习函数参数", "编写三个测试"])
    monkeypatch.setattr(
        api_app.model_client,
        "generate_suggestions",
        fake,
    )
    return fake


@pytest.fixture
def client(monkeypatch, tmp_path, fake_generate):
    monkeypatch.setattr(
        api_app,
        "DB_PATH",
        tmp_path / "test_ai.db",
    )
    with TestClient(api_app.app) as test_client:
        yield test_client


def test_suggestions_success(client, fake_generate):
    response = client.post(
        "/ai/suggestions",
        json={"goal": "  学习Python函数  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "suggestions": fake_generate.return_value,
    }
    fake_generate.assert_called_once_with("学习Python函数")


# ------------------------------
# 测试组1：非法输入，4种情况，全部422，模型函数不允许被调用
# ------------------------------
@pytest.mark.parametrize(
    "req_body",
    [
        {},  # 不传goal字段
        {"goal": ""},  # goal是空字符串
        {"goal": " "},  # goal全空白字符
        {"goal": "a" * 201},  # 超过max_length=200，共201个字符
    ],
)
def test_suggestions_bad_input(client, fake_generate, req_body):
    response = client.post("/ai/suggestions", json=req_body)
    assert response.status_code == 422
    # Pydantic在校验阶段就拦截，不会走到业务函数，mock不能被调用
    fake_generate.assert_not_called()


# ------------------------------
# 测试组2：模型服务超时 Timeout → 504
# ------------------------------
def test_suggestions_timeout(client, fake_generate):
    fake_generate.side_effect = requests.exceptions.Timeout("模拟超时")
    response = client.post("/ai/suggestions", json={"goal": "学习sqlite"})

    assert response.status_code == 504
    assert response.json()["detail"] == "模型服务响应超时，请稍后重试"
    fake_generate.assert_called_once_with("学习sqlite")


# ------------------------------
# 测试组3：其他网络请求失败 HTTPError →502
# ------------------------------
def test_suggestions_request_fail(client, fake_generate):
    fake_generate.side_effect = requests.exceptions.HTTPError("模拟失败")
    response = client.post("/ai/suggestions", json={"goal": "学习pytest"})

    assert response.status_code == 502
    assert response.json()["detail"] == "模型服务请求失败"
    fake_generate.assert_called_once_with("学习pytest")


# ------------------------------
# 测试组4：业务无效回答抛出ValueError →502
# ------------------------------
def test_suggestions_invalid_reply(client, fake_generate):
    fake_generate.side_effect = ValueError("模拟空正文")
    response = client.post("/ai/suggestions", json={"goal": "学习大模型调用"})

    assert response.status_code == 502
    assert response.json()["detail"] == "暂时无法生成有效建议"
    fake_generate.assert_called_once_with("学习大模型调用")
