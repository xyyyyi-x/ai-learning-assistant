from model_config import get_model_config
import pytest

def test_model_config_success(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1")

    assert get_model_config() == {
        "api_key": "test-key",
        "model": "test-model",
        "base_url": "https://example.com/v1",
    }

# --------------------------
# 1. 缺少配置：参数化，分别缺失其中一项，抛ValueError，消息包含变量名
# --------------------------
@pytest.mark.parametrize(
    "drop_env_name",
    [
        "MODEL_API_KEY",
        "MODEL_NAME",
        "MODEL_BASE_URL",
    ]
)
def test_model_config_missing_one(monkeypatch, drop_env_name):
    # 先全部设置假值
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1")

    # 删除其中一项环境变量
    monkeypatch.delenv(drop_env_name, raising=False)

    with pytest.raises(ValueError, match=drop_env_name):
        get_model_config()

# --------------------------
# 2. 空配置：参数化，某一项为 "" 或者 " "，其余合法，抛ValueError
# --------------------------
@pytest.mark.parametrize(
    "env_name, bad_value",
    [
        ("MODEL_API_KEY", ""),
        ("MODEL_API_KEY", "   "),
        ("MODEL_NAME", ""),
        ("MODEL_NAME", "  "),
        ("MODEL_BASE_URL", ""),
        ("MODEL_BASE_URL", "    "),
    ]
)
def test_model_config_empty_or_blank(monkeypatch, env_name, bad_value):
    # 其余两项给合法假值
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1")
    # 把其中一项覆盖成空/全空格
    monkeypatch.setenv(env_name, bad_value)

    with pytest.raises(ValueError, match=env_name):
        get_model_config()

# --------------------------
# 3. 首尾空格：三项都带前后空格，校验返回已经strip去除空格
# --------------------------
def test_model_config_strip_whitespace(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "  my‑api‑key  ")
    monkeypatch.setenv("MODEL_NAME", "  my‑model‑001   ")
    monkeypatch.setenv("MODEL_BASE_URL", "  https://demo.test/v1  ")

    cfg = get_model_config()
    assert cfg["api_key"] == "my‑api‑key"
    assert cfg["model"] == "my‑model‑001"
    assert cfg["base_url"] == "https://demo.test/v1"