from unittest.mock import Mock
import pytest
import requests
import model_client
import json

@pytest.fixture
def fake_post(monkeypatch):
    config = {
        "api_key": "test-key",
        "model": "test-model",
        "base_url": "https://example.com",
    }
    monkeypatch.setattr(
        model_client,
        "get_model_config",
        lambda: config,
    )
    post = Mock()
    monkeypatch.setattr(model_client.requests, "post", post)
    return post


def test_generate_success(fake_post):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "suggestions": [
                                {"title": "  练习函数参数  "},
                                {"title": "编写三个测试"},
                            ]
                        },
                        ensure_ascii=False,
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }
    fake_post.return_value = response

    result = model_client.generate_suggestions("学习Python函数")

    assert result == ["练习函数参数", "编写三个测试"]
    fake_post.assert_called_once()
    kwargs = fake_post.call_args.kwargs
    assert kwargs["json"]["model"] == "test-model"
    assert kwargs["json"]["messages"][-1]["content"] == "学习Python函数"
    assert kwargs["url"] == "https://example.com/chat/completions"
    assert kwargs["timeout"] == (30, 60)
    assert kwargs["json"]["stream"] is False
    assert kwargs["json"]["thinking"] == {"type": "disabled"}
    assert kwargs["json"]["max_tokens"] == 400
    response.raise_for_status.assert_called_once()


# ========= 5组失败测试 =========

# 测试1：非法目标输入：None、空串、全空白；不发起网络请求 fake_post.assert_not_called
@pytest.mark.parametrize("bad_goal, expect_exc_type, expect_msg_part", [
    (None, TypeError, "学习目标必须是字符串"),
    ("", ValueError, "学习目标不能为空"),
    ("   ", ValueError, "学习目标不能为空"),
])
def test_bad_goal_input(fake_post, bad_goal, expect_exc_type, expect_msg_part):
    with pytest.raises(expect_exc_type) as exc_info:
        model_client.generate_suggestions(bad_goal)

    assert expect_msg_part in str(exc_info.value)
    # 参数校验阶段直接抛出，不调用requests.post
    fake_post.assert_not_called()


# 测试2：请求超时，向外抛出 requests.exceptions.Timeout
def test_request_timeout(fake_post):
    fake_post.side_effect = requests.exceptions.Timeout("模拟超时")

    with pytest.raises(requests.exceptions.Timeout) as exc_info:
        model_client.generate_suggestions("学习sqlite")

    assert "模拟超时" in str(exc_info.value)
    fake_post.assert_called_once()


# 测试3：HTTP失败(400/4xx)，raise_for_status抛HTTPError；json()不能被调用
def test_http_error(fake_post):
    resp_mock = Mock()
    # raise_for_status触发HTTPError
    resp_mock.raise_for_status.side_effect = requests.exceptions.HTTPError("模拟400错误")
    fake_post.return_value = resp_mock

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        model_client.generate_suggestions("学习pytest")

    assert "模拟400错误" in str(exc_info.value)
    fake_post.assert_called_once()
    # HTTP异常发生，不应该执行 response.json()
    resp_mock.json.assert_not_called()


# 测试4：无效回答场景：空白正文 / finish_reason=length / choices为空列表，全部抛ValueError
@pytest.mark.parametrize("mock_api_resp, expect_msg_part", [
    # 场景A：正文空白
    (
        {
            "choices": [
                {
                    "message": {"content": "   "},
                    "finish_reason": "stop"
                }
            ]
        },
        "模型返回正文为空"
    ),
    # 场景B：finish_reason = length 截断
    (
        {
            "choices": [
                {
                    "message": {"content": "这里被截断的内容"},
                    "finish_reason": "length"
                }
            ]
        },
        "回答被截断"
    ),
    # 场景C：choices是空列表
    (
        {"choices": []},
        "模型响应结构异常"
    ),
])
def test_invalid_model_reply(fake_post, mock_api_resp, expect_msg_part):
    resp_mock = Mock()
    resp_mock.raise_for_status.return_value = None
    resp_mock.json.return_value = mock_api_resp
    fake_post.return_value = resp_mock

    with pytest.raises(ValueError) as exc_info:
        model_client.generate_suggestions("学习大模型调用")

    assert expect_msg_part in str(exc_info.value)
    fake_post.assert_called_once()
    resp_mock.raise_for_status.assert_called_once()
    resp_mock.json.assert_called_once()

def test_generate_rejects_invalid_task(fake_post):
    response = Mock()

    # 模拟HTTP请求成功：检查状态时不抛异常
    response.raise_for_status.return_value = None

    # 模拟模型正常结束，但生成了不合法的任务标题
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "suggestions": [
                                {"title": "   "}
                            ]
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }

    fake_post.return_value = response

    with pytest.raises(ValueError):
        model_client.generate_suggestions("学习Python函数")

    fake_post.assert_called_once()
    response.raise_for_status.assert_called_once()
    response.json.assert_called_once()