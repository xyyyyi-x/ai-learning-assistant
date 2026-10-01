# 常见的中英文列表分隔符。
# split() 不传参数时只按空白字符切分，不先把这些符号换成空格的话，
# "函数，return" 会被当成一个关键词，无法分别匹配"函数"和"return"。
KEYWORD_SEPARATORS = "，,、；;"
_SEPARATOR_TABLE = str.maketrans(
    KEYWORD_SEPARATORS,
    " " * len(KEYWORD_SEPARATORS),
)


def search_chunks(
    chunks: list[dict],
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """根据关键词命中数量，返回得分最高的资料片段。"""

    if top_k <= 0:
        raise ValueError("返回数量必须大于0")

    keywords = set(query.lower().translate(_SEPARATOR_TABLE).split())
    if not keywords:
        return []

    results = []

    for chunk in chunks:
        text = chunk["text"].lower()

        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1

        if score == 0:
            continue

        result = dict(chunk)
        result["score"] = score
        results.append(result)

    results.sort(key=lambda item: item["score"], reverse=True)

    return results[:top_k]
