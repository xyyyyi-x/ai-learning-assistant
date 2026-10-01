from unittest.mock import Mock
import pytest
import requests
import agent_model_client
import logging

@pytest.fixture
def fake_post(monkeypatch):
    monkeypatch.setattr(
        agent_model_client,
        "get_model_config",
        lambda: {
            "api_key": "test-key",
            "model": "test-model",
            "base_url": "https://example.com",
        },
    )

    post = Mock()
    monkeypatch.setattr(
        agent_model_client.requests,
        "post",
        post,
    )
    return post


def test_plain_answer(fake_post):
    message = {
        "role": "assistant",
        "content": "你好",
    }

    response = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": message,
                "finish_reason": "stop",
            }
        ]
    }
    fake_post.return_value = response

    messages = [{"role": "user", "content": "你好"}]
    result = agent_model_client.call_agent_model(messages)

    assert result == message
    fake_post.assert_called_once()
    response.raise_for_status.assert_called_once()

    payload = fake_post.call_args.kwargs["json"]
    assert payload["tools"][0]["function"]["name"] == "query_tasks"
    assert payload["messages"][0]["role"] == "system"

    # 原始对话没有被插入系统消息
    assert messages == [{"role": "user", "content": "你好"}]


def test_tool_call_success(fake_post):
    """测试：工具调用成功，finish_reason=tool_calls，content=None"""
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_001",
                "type": "function",
                "function": {
                    "name": "query_tasks",
                    "arguments": '{"completed": false}',
                },
            }
        ]
    }
    response = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": message,
                "finish_reason": "tool_calls",
            }
        ]
    }
    fake_post.return_value = response

    messages = [{"role": "user", "content": "查看未完成任务"}]
    result = agent_model_client.call_agent_model(messages)
    assert result == message
    fake_post.assert_called_once()


def test_finish_reason_length_raise(fake_post):
    """测试：回答被截断 finish_reason="length"，抛 ValueError"""
    message = {
        "role": "assistant",
        "content": "部分回答",
    }
    response = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": message,
                "finish_reason": "length",
            }
        ]
    }
    fake_post.return_value = response

    messages = [{"role": "user", "content": "查看任务"}]
    with pytest.raises(ValueError, match="模型回答被截断"):
        agent_model_client.call_agent_model(messages)


def test_request_timeout(fake_post):
    """测试：请求超时，向外抛出requests.exceptions.Timeout"""
    fake_post.side_effect = requests.exceptions.Timeout("模拟超时")

    messages = [{"role": "user", "content": "查看任务"}]
    with pytest.raises(requests.exceptions.Timeout):
        agent_model_client.call_agent_model(messages)

def test_logs_usage(fake_post, caplog):
    response = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "你好",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
        },
    }
    fake_post.return_value = response

    with caplog.at_level(
        logging.INFO,
        logger=agent_model_client.__name__,
    ):
        result = agent_model_client.call_agent_model(
            [{"role": "user", "content": "你好"}]
        )

    assert result["content"] == "你好"
    assert "total_tokens=30" in caplog.text
    assert "elapsed_seconds=" in caplog.text
    assert "test-key" not in caplog.text


def test_logs_usage_missing(fake_post, caplog):
    # 场景：返回的json没有usage字段，验证日志打印 total_tokens=None
    response = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "收到",
                },
                "finish_reason": "stop",
            }
        ]
        # 这里故意不写usage
    }
    fake_post.return_value = response

    with caplog.at_level(
        logging.INFO,
        logger=agent_model_client.__name__,
    ):
        result = agent_model_client.call_agent_model(
            [{"role": "user", "content": "嗨"}]
        )

    assert result["content"] == "收到"
    assert "total_tokens=None" in caplog.text
    assert "elapsed_seconds=" in caplog.text
    assert "test-key" not in caplog.text
