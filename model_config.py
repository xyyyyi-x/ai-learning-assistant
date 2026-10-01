import os


def read_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise ValueError(f"缺少配置：{name}")

    return value

def get_model_config() -> dict:
    """
    读取AI模型相关必填环境变量，返回配置字典
    环境变量名：
    MODEL_API_KEY → api_key
    MODEL_NAME → model
    MODEL_BASE_URL → base_url
    """
    api_key = read_required_env("MODEL_API_KEY")
    model_name = read_required_env("MODEL_NAME")
    base_url = read_required_env("MODEL_BASE_URL")

    return {
        "api_key": api_key,
        "model": model_name,
        "base_url": base_url
    }
