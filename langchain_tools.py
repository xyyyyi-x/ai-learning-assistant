from pathlib import Path

from langchain.tools import tool

from task_tools import query_tasks
from tool_schemas import QueryTasksArgs


def create_query_tool(db_path: Path):
    @tool("query_tasks", args_schema=QueryTasksArgs)
    def query_task_tool(completed: bool = False) -> list[dict]:
        """查询学习任务：false查询未完成，true查询已完成。"""
        return query_tasks(db_path, completed=completed)

    return query_task_tool