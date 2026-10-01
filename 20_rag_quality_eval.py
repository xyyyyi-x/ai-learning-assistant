"""运行一次离线检索质量评测，并把报告保存成 Markdown。

不调用模型。
"""
from pathlib import Path

from rag_evaluation import build_evaluation_report, evaluate_retrieval_cases


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    knowledge_dir = base_dir / "knowledge"

    results = evaluate_retrieval_cases(knowledge_dir)
    report = build_evaluation_report(results)

    output_path = base_dir / "generated_reports" / "rag_quality_eval.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(report)
    print()
    print("报告已保存到：", output_path)


if __name__ == "__main__":
    main()
