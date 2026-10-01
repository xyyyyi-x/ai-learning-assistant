from pydantic import BaseModel, Field, field_validator


class SuggestedTask(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=50,
        strict=True,
    )

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class SuggestionBatch(BaseModel):
    suggestions: list[SuggestedTask] = Field(
        min_length=1,
        max_length=5,
    )

def parse_suggestions(raw: str) -> list[str]:
    # 1. 检查raw是否为字符串，否则抛TypeError
    if not isinstance(raw, str):
        raise TypeError("模型正文必须是字符串")

    # 2. model_validate_json：解析JSON字符串 + 按SuggestionBatch做全部校验
    # 解析/校验失败会自动抛出ValidationError，不捕获，直接向外抛出
    batch = SuggestionBatch.model_validate_json(raw)

    # 3. 创建空列表
    result = []
    # 4. 遍历batch.suggestions
    for task in batch.suggestions:
        # 取出每个对象的title，加入列表
        result.append(task.title)

    # 5. 返回列表
    return result