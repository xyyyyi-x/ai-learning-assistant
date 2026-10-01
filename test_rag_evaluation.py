from rag_evaluation import build_evaluation_report, evaluate_retrieval_cases


def _write_doc(folder, name, text):
    (folder / name).write_text(text, encoding="utf-8")


def test_direct_hit(tmp_path):
    text = "普通函数没有显式返回值时返回None。"
    _write_doc(tmp_path, "python.md", text)

    cases = [
        {
            "id": "T1",
            "category": "direct_hit",
            "question": "没有return时返回什么？",
            "keywords": "函数 return",
            "expected_source": "python.md",
            "expected_hit": True,
            "expected_answerable": True,
        }
    ]

    results = evaluate_retrieval_cases(tmp_path, cases=cases)

    assert len(results) == 1
    result = results[0]
    assert result["hit_count"] == 1
    assert result["hits"][0]["source"] == "python.md"
    assert result["expected_source_found"] is True
    assert result["context_chars"] == len(text)


def test_no_hit(tmp_path):
    _write_doc(tmp_path, "python.md", "普通函数没有显式返回值时返回None。")

    cases = [
        {
            "id": "T2",
            "category": "no_hit",
            "question": "如何建设火星基地？",
            "keywords": "火星基地",
            "expected_source": None,
            "expected_hit": False,
            "expected_answerable": False,
        }
    ]

    results = evaluate_retrieval_cases(tmp_path, cases=cases)

    result = results[0]
    assert result["hits"] == []
    assert result["hit_count"] == 0
    assert result["context_chars"] == 0
    assert result["expected_source_found"] is None


def test_context_boundary(tmp_path):
    _write_doc(tmp_path, "long.md", "函数" * 60)

    cases = [
        {
            "id": "T3",
            "category": "direct_hit",
            "question": "函数是什么？",
            "keywords": "函数",
            "expected_source": "long.md",
            "expected_hit": True,
            "expected_answerable": True,
        }
    ]

    results = evaluate_retrieval_cases(
        tmp_path, cases=cases, chunk_size=10, top_k=2
    )

    result = results[0]
    assert result["hit_count"] <= 2
    assert all(len(hit["text"]) <= 10 for hit in result["hits"])
    assert result["context_chars"] <= 20


def test_expected_source_found_and_missing(tmp_path):
    _write_doc(tmp_path, "python.md", "函数通过return返回结果。")

    base = {
        "category": "direct_hit",
        "question": "函数返回什么？",
        "keywords": "函数 return",
        "expected_hit": True,
        "expected_answerable": True,
    }

    found_cases = [dict(base, id="T4a", expected_source="python.md")]
    missing_cases = [dict(base, id="T4b", expected_source="other.md")]

    found = evaluate_retrieval_cases(tmp_path, cases=found_cases)
    missing = evaluate_retrieval_cases(tmp_path, cases=missing_cases)

    assert found[0]["expected_source_found"] is True
    assert missing[0]["expected_source_found"] is False


def test_report_contents(tmp_path):
    _write_doc(tmp_path, "python.md", "函数通过return返回结果。")

    cases = [
        {
            "id": "T5",
            "category": "direct_hit",
            "question": "函数返回什么？",
            "keywords": "函数 return",
            "expected_source": "python.md",
            "expected_hit": True,
            "expected_answerable": True,
        }
    ]

    results = evaluate_retrieval_cases(tmp_path, cases=cases)
    report = build_evaluation_report(results)

    assert "T5" in report
    assert "python.md" in report
    assert str(results[0]["context_chars"]) in report
    assert "chunk_size=200" in report
    assert "top_k=2" in report
    assert "expected_answerable 来自人工预先标注" in report
    assert "context_chars 只统计参考正文" in report
