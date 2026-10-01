"""读取本地 .env 并启动应用，不需要手动设置 PowerShell 环境变量。"""
from pathlib import Path

from dotenv import load_dotenv
import uvicorn


def main():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        raise SystemExit("缺少 week2/.env，请先配置模型和数据库路径。")
    # 此启动方式以本地配置文件为准，避免旧终端变量干扰。
    load_dotenv(env_path, override=True, encoding="utf-8-sig")
    uvicorn.run("api_app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
