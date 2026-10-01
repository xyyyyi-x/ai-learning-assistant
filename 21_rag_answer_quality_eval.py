"""真实评测模型是否正确使用检索到的资料。

只评测 Q1、Q3、Q5 三个案例，最多产生三次模型调用。
"""
from pathlib import Path

from dotenv import load_dotenv

from rag_evaluation import (
    EVALUATION_CASES,
    evaluate_answer_cases,
    evaluate_retrieval_cases,
)
from rag_model_client import generate_rag_answer

SELECTED_IDS = ["Q1", "Q3", "Q5"]


def build_answer_report(answer_results: list[dict], model_call_count: int) -> str:
    """把回答评测结果整理成 Markdown 报告。"""
    lines = [
        "# RAG 模型回答质量评测",
        "",
        "评测目标：模型是否正确使用检索到的资料。",
        f"实际模型调用次数：{model_call_count}",
        "",
    ]

    for result in answer_results:
        lines.append(f"## {result['id']}（{result['category']}）")
        lines.append("")
        lines.append(f"- 问题：{result['question']}")
        lines.append(f"- 是否调用模型：{result['model_called']}")

        if result["sources"]:
            lines.append("- 命中来源：")
            for hit in result["sources"]:
                lines.append(
                    f"  - {hit['source']} 片段 {hit['chunk_index']}"
                    f"（得分 {hit['score']}）"
                )
        else:
            lines.append("- 命中来源：（无命中）")

        lines.append("")
        lines.append("模型回答：")
        lines.append("")
        lines.append(result["answer"])
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    base_dir = Path(__file__).resolve().parent

    env_path = base_dir / ".env"
    if not env_path.is_file():
        print(f"缺少配置文件：{env_path}")
        print("请先按照 README 配置 week2/.env。")
        return

    load_dotenv(env_path, override=True, encoding="utf-8-sig")

    cases = [case for case in EVALUATION_CASES if case["id"] in SELECTED_IDS]

    retrieval_results = evaluate_retrieval_cases(
        base_dir / "knowledge",
        cases=cases,
    )

    model_call_count = 0

    def counted_generate_answer(question, hits):
        nonlocal model_call_count
        model_call_count += 1
        return generate_rag_answer(question, hits)

    answer_results = evaluate_answer_cases(
        retrieval_results,
        counted_generate_answer,
    )

    report = build_answer_report(answer_results, model_call_count)

    output_path = base_dir / "generated_reports" / "rag_answer_quality_eval.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(report)
    print()
    print("报告已保存到：", output_path)


if __name__ == "__main__":
    main()
