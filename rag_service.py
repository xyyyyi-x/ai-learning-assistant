from pathlib import Path

import rag_model_client
from knowledge_loader import load_markdown_documents
from knowledge_splitter import split_documents
from knowledge_retriever import search_chunks


def answer_question(
    question: str,
    keywords: str,
    knowledge_dir: Path,
) -> dict:
    """检索资料并生成回答，返回回答及本次提供给模型的资料。"""

    question = question.strip()
    keywords = keywords.strip()

    if not question or not keywords:
        raise ValueError("问题和检索关键词不能为空")

    documents = load_markdown_documents(knowledge_dir)
    chunks = split_documents(documents, chunk_size=200)
    hits = search_chunks(chunks, keywords, top_k=2)

    if not hits:
        return {
            "answer": "未检索到相关资料，请调整关键词。",
            "sources": [],
        }

    answer = rag_model_client.generate_rag_answer(question, hits)

    sources = []
    for reference_id, chunk in enumerate(hits, start=1):
        sources.append({
            "reference_id": reference_id,
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
        })

    return {
        "answer": answer,
        "sources": sources,
    }
