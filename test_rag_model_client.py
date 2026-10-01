from unittest.mock import Mock
import pytest
import requests
import rag_model_client


@pytest.fixture
def fake_post(monkeypatch):
    config = {
        "api_key": "test-key",
        "model": "test-model",
        "base_url": "https://example.com",
    }
    monkeypatch.setattr(
        rag_model_client,
        "get_model_config",
        lambda: config,
    )
    post = Mock()
    monkeypatch.setattr(rag_model_client.requests, "post", post)
    return post


def test_generate_rag_answer_success(fake_post):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "  普通函数没有显式返回值时，返回None。[1]  "
                },
                "finish_reason": "stop",
            }
        ]
    }
    fake_post.return_value = response

    chunks = [
        {
            "source": "python.md",
            "chunk_index": 3,
            "text": "普通函数没有显式返回值时，返回None。",
            "score": 1,
        }
    ]

    answer = rag_model_client.generate_rag_answer(
        "函数没有return时返回什么？",
        chunks,
    )

    assert answer == "普通函数没有显式返回值时，返回None。[1]"
    fake_post.assert_called_once()

    kwargs = fake_post.call_args.kwargs
    assert kwargs["url"] == "https://example.com/chat/completions"
    assert kwargs["timeout"] == (30, 60)
    assert kwargs["json"]["model"] == "test-model"

    messages = kwargs["json"]["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]
    assert "函数没有return时返回什么？" in messages[1]["content"]
    assert "[1] 来源：python.md；片段：3" in messages[1]["content"]
    assert chunks[0]["text"] in messages[1]["content"]

    response.raise_for_status.assert_called_once()


@pytest.mark.parametrize("question, chunks, expect_msg_part", [
    (
        "   ",
        [{"source": "a.md", "chunk_index": 1, "text": "正文", "score": 1}],
        "问题不能为空",
    ),
    (
        "问题",
        [],
        "参考资料不能为空",
    ),
])
def test_invalid_input(fake_post, question, chunks, expect_msg_part):
    with pytest.raises(ValueError) as exc_info:
        rag_model_client.generate_rag_answer(question, chunks)

    assert expect_msg_part in str(exc_info.value)
    fake_post.assert_not_called()


def test_request_timeout(fake_post):
    fake_post.side_effect = requests.exceptions.Timeout("模拟超时")

    with pytest.raises(requests.exceptions.Timeout) as exc_info:
        rag_model_client.generate_rag_answer(
            "函数返回什么？",
            [{"source": "a.md", "chunk_index": 1, "text": "正文", "score": 1}],
        )

    assert "模拟超时" in str(exc_info.value)
    fake_post.assert_called_once()


def test_http_error(fake_post):
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("模拟400错误")
    fake_post.return_value = response

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        rag_model_client.generate_rag_answer(
            "函数返回什么？",
            [{"source": "a.md", "chunk_index": 1, "text": "正文", "score": 1}],
        )

    assert "模拟400错误" in str(exc_info.value)
    fake_post.assert_called_once()
    response.json.assert_not_called()


@pytest.mark.parametrize("mock_api_resp, expect_msg_part", [
    ({"choices": []}, "模型响应结构异常"),
    (
        {
            "choices": [
                {"message": {"content": None}, "finish_reason": "stop"}
            ]
        },
        "模型返回正文不是字符串",
    ),
    (
        {
            "choices": [
                {"message": {"content": "   "}, "finish_reason": "stop"}
            ]
        },
        "模型返回正文为空",
    ),
    (
        {
            "choices": [
                {"message": {"content": "被截断的内容"}, "finish_reason": "length"}
            ]
        },
        "回答被截断",
    ),
    (
        {
            "choices": [
                {"message": {"content": "一些内容"}, "finish_reason": "tool_calls"}
            ]
        },
        "模型非正常结束",
    ),
])
def test_invalid_response(fake_post, mock_api_resp, expect_msg_part):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = mock_api_resp
    fake_post.return_value = response

    with pytest.raises(ValueError) as exc_info:
        rag_model_client.generate_rag_answer(
            "函数返回什么？",
            [{"source": "a.md", "chunk_index": 1, "text": "正文", "score": 1}],
        )

    assert expect_msg_part in str(exc_info.value)
    fake_post.assert_called_once()
    response.raise_for_status.assert_called_once()
    response.json.assert_called_once()
