"""RAG 检索质量的离线评测。

不调用模型，只评测"检索出的片段是否包含回答问题所需的内容"。
expected_answerable 由人工预先标注，不由程序根据 score 推断。
"""
from pathlib import Path

from knowledge_loader import load_markdown_documents
from knowledge_splitter import split_documents
from knowledge_retriever import search_chunks


EVALUATION_CASES = [
    {
        "id": "Q1",
        "category": "direct_hit",
        "question": "普通函数没有显式return时返回什么？",
        "keywords": "函数 return",
        "expected_source": "python_functions.md",
        "expected_hit": True,
        "expected_answerable": True,
    },
    {
        "id": "Q2",
        "category": "direct_hit",
        "question": "本项目中模型响应超时返回什么状态码？",
        "keywords": "超时 504",
        "expected_source": "http_status.md",
        "expected_hit": True,
        "expected_answerable": True,
    },
    {
        "id": "Q3",
        "category": "direct_hit",
        "question": "工具调用中，谁真正执行数据库查询？",
        "keywords": "Python SQLite",
        "expected_source": "tool_calling.md",
        "expected_hit": True,
        "expected_answerable": True,
    },
    {
        "id": "Q4",
        "category": "synonym_miss",
        "question": "普通函数没有显式return时返回什么？",
        "keywords": "子程序 回传值",
        "expected_source": "python_functions.md",
        "expected_hit": False,
        "expected_answerable": False,
    },
    {
        "id": "Q5",
        "category": "insufficient_hit",
        "question": "如何用装饰器保留原函数元数据？",
        "keywords": "函数",
        "expected_source": "python_functions.md",
        "expected_hit": True,
        "expected_answerable": False,
    },
    {
        "id": "Q6",
        "category": "no_hit",
        "question": "如何建设火星基地？",
        "keywords": "火星基地",
        "expected_source": None,
        "expected_hit": False,
        "expected_answerable": False,
    },
]

CHUNK_SIZE = 200
TOP_K = 2

EMPTY_ANSWER = "未检索到相关资料，请调整关键词。"


def evaluate_retrieval_cases(
    knowledge_dir: Path,
    cases: list[dict] = EVALUATION_CASES,
    chunk_size: int = CHUNK_SIZE,
    top_k: int = TOP_K,
) -> list[dict]:
    """对每个案例执行一次检索，返回评测记录。不调用模型。"""
    documents = load_markdown_documents(knowledge_dir)
    chunks = split_documents(documents, chunk_size=chunk_size)

    results = []
    for case in cases:
        hits = search_chunks(chunks, case["keywords"], top_k=top_k)

        expected_source = case["expected_source"]
        if expected_source is None:
            expected_source_found = None
        else:
            expected_source_found = any(
                hit["source"] == expected_source for hit in hits
            )

        results.append({
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "keywords": case["keywords"],
            "expected_hit": case["expected_hit"],
            "expected_source": expected_source,
            "expected_answerable": case["expected_answerable"],
            "hits": hits,
            "hit_count": len(hits),
            "context_chars": sum(len(hit["text"]) for hit in hits),
            "expected_source_found": expected_source_found,
        })

    return results


def evaluate_answer_cases(
    retrieval_results: list[dict],
    generate_answer,
) -> list[dict]:
    """对每条检索结果生成回答，并记录是否真的调用了模型。

    没有命中片段时不调用模型，回答固定为 EMPTY_ANSWER。
    """
    results = []

    for item in retrieval_results:
        hits = item["hits"]

        if hits:
            answer = generate_answer(item["question"], hits)
            model_called = True
        else:
            answer = EMPTY_ANSWER
            model_called = False

        results.append({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "answer": answer,
            "model_called": model_called,
            "sources": hits,
        })

    return results


def build_evaluation_report(
    results: list[dict],
    chunk_size: int = CHUNK_SIZE,
    top_k: int = TOP_K,
) -> str:
    """把评测记录整理成 Markdown 报告。"""
    lines = [
        "# RAG 检索质量评测",
        "",
        f"固定配置：chunk_size={chunk_size}，top_k={top_k}",
        "本批不调用模型，只评测检索结果。",
        "",
    ]

    for result in results:
        lines.append(f"## {result['id']}（{result['category']}）")
        lines.append("")
        lines.append(f"- 问题：{result['question']}")
        lines.append(f"- 关键词：{result['keywords']}")
        lines.append(f"- 命中数量：{result['hit_count']}")
        lines.append(f"- 参考正文字符数：{result['context_chars']}")

        expected_source = result["expected_source"]
        lines.append(
            f"- 预期来源：{expected_source if expected_source else '（无）'}"
        )
        lines.append(f"- 是否找到预期来源：{result['expected_source_found']}")
        lines.append(f"- 预期是否足以回答：{result['expected_answerable']}")

        if result["hits"]:
            lines.append("- 命中来源及片段编号：")
            for hit in result["hits"]:
                lines.append(
                    f"  - {hit['source']} 片段 {hit['chunk_index']}"
                    f"（得分 {hit['score']}）"
                )
        else:
            lines.append("- 命中来源及片段编号：（无命中）")

        lines.append("")

    lines.append("## 说明")
    lines.append("")
    lines.append(
        "- expected_answerable 来自人工预先标注，不是程序根据 score 自动判断。"
    )
    lines.append(
        "- context_chars 只统计参考正文，不包含来源标签、问题和提示词。"
    )
    lines.append("")

    return "\n".join(lines)
