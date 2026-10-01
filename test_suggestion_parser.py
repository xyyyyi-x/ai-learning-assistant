# test_suggestion_parser.py
import json
import pytest
from pydantic import ValidationError
from suggestion_parser import parse_suggestions


def test_parse_success():
    raw = json.dumps(
        {
            "suggestions": [
                {"title": "  练习函数参数  "},
                {"title": "编写三个测试"},
            ]
        },
        ensure_ascii=False,
    )

    result = parse_suggestions(raw)

    assert result == ["练习函数参数", "编写三个测试"]


# 测试组1：参数类型错误：None、整数123 → 抛出 TypeError
@pytest.mark.parametrize("bad_input", [None, 123])
def test_parse_type_error(bad_input):
    with pytest.raises(TypeError, match="模型正文必须是字符串"):
        parse_suggestions(bad_input)


# 测试组2：JSON或结构错误："不是JSON"、"{}"、'{"suggestions":[]}' → ValidationError
@pytest.mark.parametrize("bad_raw", [
    "不是JSON",
    "{}",
    json.dumps({"suggestions": []})
])
def test_parse_json_or_struct_error(bad_raw):
    with pytest.raises(ValidationError):
        parse_suggestions(bad_raw)


# 测试组3：建议内容错误：标题纯空白、标题51字符、标题为整数、建议数量6条 → ValidationError
@pytest.mark.parametrize("bad_data", [
    # 1.标题纯空白
    {"suggestions": [{"title": "    "}]},
    # 2.标题51个字符
    {"suggestions": [{"title": "a" * 51}]},
    # 3.标题为整数
    {"suggestions": [{"title": 999}]},
    # 4.建议一共6条
    {"suggestions": [{"title": f"task{i}"} for i in range(6)]}
])
def test_parse_content_invalid(bad_data):
    # 先构造字典，再 dumps 得到json字符串
    raw = json.dumps(bad_data, ensure_ascii=False)
    with pytest.raises(ValidationError):
        parse_suggestions(raw)
