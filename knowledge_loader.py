from pathlib import Path


def load_markdown_documents(folder: Path) -> list[dict]:
    """读取目录中的Markdown资料，保留文件名与正文。"""

    if not folder.exists():
        raise FileNotFoundError("资料目录不存在")

    if not folder.is_dir():
        raise NotADirectoryError("资料路径必须是目录")

    documents = []

    for path in sorted(folder.glob("*.md")):
        if not path.is_file():
            continue

        text = path.read_text(encoding="utf-8-sig").strip()
        if not text:
            continue

        documents.append({
            "source": path.name,
            "text": text,
        })

    return documents
