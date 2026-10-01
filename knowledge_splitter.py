def split_documents(
    documents: list[dict],
    chunk_size: int = 400,
) -> list[dict]:
    """将资料按字符数切块，保留来源及文档内片段编号。"""

    if chunk_size <= 0:
        raise ValueError("片段长度必须大于0")

    chunks = []

    for doc in documents:
        source = doc["source"]
        text = doc["text"]

        chunk_index = 1
        for start in range(0, len(text), chunk_size):
            chunks.append({
                "source": source,
                "chunk_index": chunk_index,
                "text": text[start:start + chunk_size],
            })
            chunk_index += 1

    return chunks
