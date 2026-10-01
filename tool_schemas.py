from pydantic import BaseModel, ConfigDict, Field


class QueryTasksArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed: bool = Field(
        default=False,
        strict=True,
        description="false查询未完成任务，true查询已完成任务",
    )