from pathlib import Path


def test_dockerignore_keeps_knowledge_markdown():
    rules = Path(".dockerignore").read_text(encoding="utf-8").splitlines()

    assert "*.md" in rules
    assert "!knowledge/*.md" in rules
