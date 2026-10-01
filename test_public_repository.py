from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent

PUBLIC_ENTRY_FILES = [
    "start_app.py",
    "14_agent_live_demo.py",
    "15_langchain_live_demo.py",
    "16_rag_live_demo.py",
    "19_weekly_report_demo.py",
    "21_rag_answer_quality_eval.py",
]


@pytest.mark.parametrize("file_name", PUBLIC_ENTRY_FILES)
def test_public_entry_file_does_not_reference_old_week2_path(file_name):
    content = (PROJECT_ROOT / file_name).read_text(encoding="utf-8")
    old_directory_prefix = "week" + "2/"

    assert old_directory_prefix not in content
