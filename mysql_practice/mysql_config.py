"""MySQL 练习环境的连接配置。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

REQUIRED_KEYS = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
]


def load_config() -> dict:
    """读取同目录 .env，返回可直接传给 connect(**config) 的字典。"""
    env_path = BASE_DIR / ".env"
    if not env_path.is_file():
        raise FileNotFoundError(f"缺少配置文件：{env_path}")

    load_dotenv(env_path, override=True, encoding="utf-8-sig")

    raw = {}
    for key in REQUIRED_KEYS:
        value = os.getenv(key, "").strip()
        if not value:
            raise ValueError(f"缺少配置：{key}")
        raw[key] = value

    try:
        port = int(raw["MYSQL_PORT"])
    except ValueError as exc:
        raise ValueError("MYSQL_PORT 必须是整数") from exc

    return {
        "host": raw["MYSQL_HOST"],
        "port": port,
        "user": raw["MYSQL_USER"],
        "password": raw["MYSQL_PASSWORD"],
        "database": raw["MYSQL_DATABASE"],
        # 本机安装的 26.7.0 版本 C 扩展连接时报
        # "RuntimeError: Failed raising error."，改用纯 Python 实现。
        "use_pure": True,
    }
