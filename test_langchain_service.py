from unittest.mock import Mock
import pytest
from langchain_core.messages import AIMessage, ToolMessage

import langchain_service
import httpx2
import requests
from openai import APITimeoutError, APIConnectionError
from langchain.agents.middleware.model_call_limit import (
    ModelCallLimitExceededError,
)

@pytest.fixture
def fake_factory(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(
        langchain_service,
        "create_task_agent",
        factory,
    )
    return factory


def test_returns_final_answer(tmp_path, fake_factory):
    db_path = tmp_path / "tasks.db"
    fake_agent = fake_factory.return_value

    fake_agent.invoke.return_value = {
        "messages": [
            AIMessage(content="  你还有一条未完成任务。  "),
        ]
    }

    answer = langchain_service.run_langchain_assistant(
        "  查看任务  ",
        db_path,
    )

    assert answer == "你还有一条未完成任务。"
    fake_factory.assert_called_once_with(db_path)
    fake_agent.invoke.assert_called_once_with(
        {
            "messages": [
                {"role": "user", "content": "查看任务"},
            ]
        }
    )


# ========= 参数化异常测试 =========
@pytest.mark.parametrize(
    "goal, agent_invoke_return, expected_exc_type, expected_msg",
    [
        # 1. goal=None，类型错误，抛出 TypeError
        (
            None,
            {"messages": [AIMessage(content="ok")]},
            TypeError,
            "学习目标必须是字符串",
        ),
        # 2. goal=" " 空白字符串，抛 ValueError
        (
            "   ",
            {"messages": [AIMessage(content="ok")]},
            ValueError,
            "学习目标不能为空",
        ),
        # 3. agent.invoke返回 None（不是字典）
        (
            "查看任务",
            None,
            ValueError,
            "Agent返回格式异常",
        ),
        # 4. messages是空列表
        (
            "查看任务",
            {"messages": []},
            ValueError,
            "Agent未返回消息",
        ),
        # 5. 最后一条消息是ToolMessage，不是AIMessage
        (
            "查看任务",
            {
                "messages": [
                    ToolMessage(content="[]", tool_call_id="call_001")
                ]
            },
            ValueError,
            "Agent未返回最终模型消息",
        ),
        # 6. AIMessage带有tool_calls，还有待执行工具调用
        (
            "查看任务",
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "query_tasks",
                                "args": {"completed": False},
                                "id": "call_001",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            },
            ValueError,
            "Agent仍有未完成的工具调用",
        ),
        # 7. AIMessage只有空白文字，有效回答为空
        (
            "查看任务",
            {
                "messages": [
                    AIMessage(content="   \n\t  ")
                ]
            },
            ValueError,
            "Agent未返回有效回答",
        ),
    ],
)
def test_run_langchain_assistant_exceptions(
    tmp_path, fake_factory, goal, agent_invoke_return, expected_exc_type, expected_msg
):
    db_path = tmp_path / "tasks.db"
    fake_agent = fake_factory.return_value
    fake_agent.invoke.return_value = agent_invoke_return

    with pytest.raises(expected_exc_type) as exc_info:
        langchain_service.run_langchain_assistant(goal, db_path)

    assert expected_msg in str(exc_info.value)
    # goal校验阶段（goal=None / goal空白）：不应调用create_task_agent，提前拦截
    if isinstance(goal, str) and goal.strip() != "":
        fake_factory.assert_called_once_with(db_path)
    else:
        fake_factory.assert_not_called()


@pytest.mark.parametrize(
    "source_error, expected_error",
    [
        (
            APITimeoutError(
                request=httpx2.Request(
                    "POST", "https://example.com"
                )
            ),
            requests.exceptions.Timeout,
        ),
        (
            APIConnectionError(
                request=httpx2.Request(
                    "POST", "https://example.com"
                )
            ),
            requests.exceptions.RequestException,
        ),
        (
            ModelCallLimitExceededError(
                thread_count=3,
                run_count=3,
                thread_limit=None,
                run_limit=3,
            ),
            RuntimeError,
        ),
    ],
)
def test_framework_error_mapping(
    tmp_path, fake_factory, source_error, expected_error
):
    fake_factory.return_value.invoke.side_effect = source_error

    with pytest.raises(expected_error) as exc_info:
        langchain_service.run_langchain_assistant(
            "查看任务",
            tmp_path / "tasks.db",
        )

    # 确认转换后的异常保留了原始原因
    assert exc_info.value.__cause__ is source_error