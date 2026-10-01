from pathlib import Path
from task_tools import query_tasks
from tool_schemas import QueryTasksArgs

# 工具注册表：工具名字映射到实际函数
TOOL_FUNCTIONS = {
    "query_tasks": query_tasks,
}


def execute_tool(
    tool_name: str,
    arguments_json: str,
    db_path: Path,
) -> list[dict]:
    """根据工具名称，校验参数并执行查询。"""
    # 1. 检查工具名称，不存在时抛出ValueError
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError("未知工具")

    # 2. 使用QueryTasksArgs校验arguments_json
    args = QueryTasksArgs.model_validate_json(arguments_json)

    # 3. 从TOOL_FUNCTIONS取出对应函数
    selected_function = TOOL_FUNCTIONS[tool_name]

    # 4. 调用函数，传入db_path 和校验后的参数，返回结果
    result = selected_function(db_path, completed=args.completed)
    return result
