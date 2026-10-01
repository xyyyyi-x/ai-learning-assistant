import argparse
from pathlib import Path

from dotenv import load_dotenv

from knowledge_loader import load_markdown_documents
from knowledge_splitter import split_documents
from knowledge_retriever import search_chunks
from rag_model_client import generate_rag_answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--keywords", required=True)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent

    question = args.question.strip()
    keywords = args.keywords.strip()

    if not question or not keywords:
        print("问题和检索关键词不能为空")
        return

    documents = load_markdown_documents(base_dir / "knowledge")
    chunks = split_documents(documents, chunk_size=200)
    hits = search_chunks(chunks, keywords, top_k=2)

    print(f"问题：{question}")
    print(f"检索关键词：{keywords}")

    for reference_id, chunk in enumerate(hits, start=1):
        print(
            f"[{reference_id}] 来源：{chunk['source']}；"
            f"片段：{chunk['chunk_index']}；得分：{chunk['score']}"
        )
        print(chunk["text"])
        print()

    if not hits:
        print("未检索到相关资料，本次不调用模型。")
        return

    env_path = base_dir / ".env"
    if not env_path.is_file():
        raise ValueError("缺少 .env 配置文件")

    load_dotenv(
        env_path,
        override=True,
        encoding="utf-8-sig",
    )

    answer = generate_rag_answer(question, hits)
    print("\n模型回答：")
    print(answer)


if __name__ == "__main__":
    main()
