import pytest
from pydantic import ValidationError
from tool_schemas import QueryTasksArgs


def test_default_completed():
    args = QueryTasksArgs.model_validate_json("{}")
    assert args.completed is False


def test_accept_completed():
    # 测试 true
    args_true = QueryTasksArgs.model_validate_json('{"completed": true}')
    assert args_true.completed is True

    # 测试 false
    args_false = QueryTasksArgs.model_validate_json('{"completed": false}')
    assert args_false.completed is False


def test_reject_invalid_completed():
    # 字符串"false"
    with pytest.raises(ValidationError):
        QueryTasksArgs.model_validate_json('{"completed": "false"}')
    # 数字0
    with pytest.raises(ValidationError):
        QueryTasksArgs.model_validate_json('{"completed": 0}')
    # null
    with pytest.raises(ValidationError):
        QueryTasksArgs.model_validate_json('{"completed": null}')


def test_reject_extra_field():
    # 多了limit字段，extra="forbid"会拦截
    with pytest.raises(ValidationError):
        QueryTasksArgs.model_validate_json('{"completed": false, "limit": 5}')
