"""真实生成一次学习周报。

会调用一次模型（产生少量 API 用量），并把周报保存到
generated_reports/weekly_report.md。
"""
import json
from pathlib import Path

from dotenv import load_dotenv
import requests

from config import get_db_path
from task_db import list_tasks
from weekly_report import calculate_weekly_stats
from weekly_report_service import create_weekly_report


def main() -> None:
    base_dir = Path(__file__).resolve().parent

    env_path = base_dir / ".env"
    if not env_path.is_file():
        print(f"缺少配置文件：{env_path}")
        print("请先按照 README 配置 .env（模型密钥和数据库路径）。")
        return

    load_dotenv(env_path, override=True, encoding="utf-8-sig")

    db_path = get_db_path()
    rows = list_tasks(db_path)
    stats = calculate_weekly_stats(rows)

    print("统计结果：")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print()

    output_path = base_dir / "generated_reports" / "weekly_report.md"

    try:
        report = create_weekly_report(db_path, output_path)
    except requests.exceptions.Timeout:
        print("生成周报失败：模型请求超时，请稍后重试。")
        return
    except requests.exceptions.RequestException:
        print("生成周报失败：模型请求失败，请检查网络或配置。")
        return
    except ValueError:
        print("生成周报失败：模型响应无效，请稍后重试。")
        return
    except OSError:
        print("生成周报失败：文件保存失败，请检查输出目录权限。")
        return

    print("周报已保存到：", output_path)
    print()
    print("周报正文：")
    print(report)


if __name__ == "__main__":
    main()
