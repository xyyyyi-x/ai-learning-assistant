from unittest.mock import Mock

import pytest
import requests

import weekly_report_model

STATS = {
    "total": 4,
    "completed": 3,
    "pending": 1,
    "completion_rate": 75.0,
    "completed_titles": ["任务A", "任务B", "任务C"],
    "pending_titles": ["任务D"],
}


@pytest.fixture
def fake_post(monkeypatch):
    config = {
        "api_key": "fake-key",
        "model": "fake-model",
        "base_url": "https://example.com",
    }
    monkeypatch.setattr(
        weekly_report_model,
        "get_model_config",
        lambda: config,
    )
    post = Mock()
    monkeypatch.setattr(weekly_report_model.requests, "post", post)
    return post


def _ok_response(fake_post, content, finish_reason="stop"):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": finish_reason,
            }
        ]
    }
    fake_post.return_value = response
    return response


def test_generate_weekly_report_text_success(fake_post):
    markdown = "# 本周学习周报\n\n## 本周概况\n共 4 条任务，完成率 75.0%。"
    response = _ok_response(fake_post, f"\n   {markdown}  \n")

    result = weekly_report_model.generate_weekly_report_text(STATS)

    # 返回值去掉了首尾空白，正文没有被破坏
    assert result == markdown

    # 只调用了一次模拟的 requests.post，没有真实网络请求
    fake_post.assert_called_once()
    kwargs = fake_post.call_args.kwargs
    assert kwargs["url"] == "https://example.com/chat/completions"
    assert kwargs["timeout"] == (30, 60)
    assert kwargs["json"]["model"] == "fake-model"
    assert kwargs["json"]["stream"] is False

    messages = kwargs["json"]["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]

    # 统计数据确实放进了用户消息
    user_content = messages[1]["content"]
    assert '"total": 4' in user_content
    assert '"completed": 3' in user_content
    assert '"completion_rate": 75.0' in user_content
    assert "任务A" in user_content
    assert "任务D" in user_content

    response.raise_for_status.assert_called_once()


def test_blank_content(fake_post):
    _ok_response(fake_post, "   ")

    with pytest.raises(ValueError, match="模型返回正文为空"):
        weekly_report_model.generate_weekly_report_text(STATS)


def test_truncated_content(fake_post):
    _ok_response(fake_post, "被截断的周报", finish_reason="length")

    with pytest.raises(ValueError, match="周报被截断"):
        weekly_report_model.generate_weekly_report_text(STATS)


def test_bad_response_structure(fake_post):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"choices": []}
    fake_post.return_value = response

    with pytest.raises(ValueError, match="模型响应结构异常"):
        weekly_report_model.generate_weekly_report_text(STATS)


def test_http_error_propagates(fake_post):
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "模拟500错误"
    )
    fake_post.return_value = response

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        weekly_report_model.generate_weekly_report_text(STATS)

    assert "模拟500错误" in str(exc_info.value)
    fake_post.assert_called_once()
    # HTTP 失败后不应该再读 JSON
    response.json.assert_not_called()


def test_network_error_propagates(fake_post):
    fake_post.side_effect = requests.exceptions.Timeout("模拟超时")

    with pytest.raises(requests.exceptions.Timeout) as exc_info:
        weekly_report_model.generate_weekly_report_text(STATS)

    assert "模拟超时" in str(exc_info.value)
    fake_post.assert_called_once()
