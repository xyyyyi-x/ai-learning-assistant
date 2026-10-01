from pathlib import Path

from knowledge_loader import load_markdown_documents
from knowledge_splitter import split_documents
from knowledge_retriever import search_chunks


def main():
    folder = Path(__file__).resolve().parent / "knowledge"
    documents = load_markdown_documents(folder)
    chunks = split_documents(documents, chunk_size=200)

    cases = [
        {
            "id": "Q1",
            "question": "普通函数没有显式return时返回什么？",
            "keywords": "函数 return",
        },
        {
            "id": "Q2",
            "question": "本项目中模型响应超时返回什么状态码？",
            "keywords": "超时 504",
        },
        {
            "id": "Q3",
            "question": "工具调用中，谁真正执行数据库查询？",
            "keywords": "Python SQLite",
        },
        {
            "id": "Q4",
            "question": "普通函数没有显式return时返回什么？",
            "keywords": "子程序 回传值",
        },
        {
            "id": "Q5",
            "question": "如何用装饰器保留原函数元数据？",
            "keywords": "函数",
        },
        {
            "id": "Q6",
            "question": "如何建设火星基地？",
            "keywords": "火星基地",
        },
    ]

    for case in cases:
        print(f"\n{case['id']}：{case['question']}")
        print("关键词：", case["keywords"])
        hits = search_chunks(chunks, case["keywords"], top_k=2)

        if not hits:
            print("未命中")
            continue

        for hit in hits:
            print(
                f"来源：{hit['source']}，"
                f"片段：{hit['chunk_index']}，"
                f"得分：{hit['score']}"
            )
            print(hit["text"])


if __name__ == "__main__":
    main()
