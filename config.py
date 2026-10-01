import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def get_db_path() -> Path:
    raw_path = os.getenv("TASK_DB_PATH","").strip()

    if not raw_path:
        return BASE_DIR / "tasks.db"

    path = Path(raw_path)

    if not path.is_absolute():
        path = BASE_DIR / path

    return path.resolve()