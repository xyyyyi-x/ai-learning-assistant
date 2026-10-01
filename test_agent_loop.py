import json
import pytest
import task_db
from agent_loop import run_assistant


def test_direct_answer(tmp_path):
    """测试：模型直接返回文字回答，不调用工具"""
    def fake_model(messages):
        assert messages == [
            {"role": "user", "content": "你好"},
        ]
        return {
            "role": "assistant",
            "content": "你好，有什么学习目标？",
        }

    result = run_assistant(
        "你好",
        tmp_path / "tasks.db",
        fake_model,
    )
    assert result == "你好，有什么学习目标？"


def test_tool_call_then_answer(tmp_path):
    """测试一：第一轮返回工具调用，拿到结果后第二轮返回回答"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)
    task_id = task_db.create_task(db_path, "练习函数", completed=False)

    calls = []
    def fake_model(messages):
        calls.append(1)
        if len(calls) == 1:
            # 第一轮：模型返回工具调用指令
            return {
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
        # 第二次调用模型
        # 校验消息顺序：倒数第2是assistant工具调用消息，最后一条是tool结果
        assert messages[-2]["role"] == "assistant"
        assert messages[-1]["role"] == "tool"
        assert messages[-1]["tool_call_id"] == "call_001"
        tasks = json.loads(messages[-1]["content"])
        assert tasks == [
            {
                "id": task_id,
                "title": "练习函数",
                "completed": False,
                "priority": 1,
            }
        ]
        # 第二轮返回最终文字回答
        return {
            "role": "assistant",
            "content": "你还有一条未完成任务。",
        }

    result = run_assistant(
        goal="查看未完成任务",
        db_path=db_path,
        model_call=fake_model
    )
    assert result == "你还有一条未完成任务。"
    assert len(calls) == 2


def test_loop_exceed_max_turns(tmp_path):
    """测试二：模型一直返回工具调用，达到max_turns上限抛出RuntimeError"""
    db_path = tmp_path / "tasks.db"
    task_db.init_db(db_path)

    calls = []
    def fake_model(messages):
        calls.append(1)
        # 每次都返回工具调用，永不给出最终回答
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{len(calls)}",
                    "type": "function",
                    "function": {
                        "name": "query_tasks",
                        "arguments": '{"completed": false}',
                    },
                }
            ]
        }

    with pytest.raises(RuntimeError, match="超过模型调用次数上限"):
        run_assistant(
            goal="查看任务",
            db_path=db_path,
            model_call=fake_model,
            max_turns=2
        )
    # 模拟模型刚好被调用2次
    assert len(calls) == 2


def test_no_valid_answer(tmp_path):
    """测试三：无工具调用，content是空空白字符串，抛出ValueError"""
    db_path = tmp_path / "tasks.db"

    def fake_model(messages):
        return {
            "role": "assistant",
            "content": "   ",
        }

    with pytest.raises(ValueError, match="模型未返回有效回答"):
        run_assistant(
            goal="你好",
            db_path=db_path,
            model_call=fake_model
        )
