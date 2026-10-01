from rag_evaluation import EMPTY_ANSWER, evaluate_answer_cases


def _retrieval_result(case_id, category, question, hits):
    return {
        "id": case_id,
        "category": category,
        "question": question,
        "hits": hits,
    }


HIT_A = {
    "source": "python_functions.md",
    "chunk_index": 1,
    "text": "没有显式返回值时，普通函数返回None。",
    "score": 2,
}

HIT_B = {
    "source": "http_status.md",
    "chunk_index": 2,
    "text": "504 表示模型服务响应超时。",
    "score": 2,
}


def test_calls_model_when_hits_exist():
    calls = []

    def fake_generate(question, hits):
        calls.append((question, hits))
        return "回答内容"

    retrieval = [_retrieval_result("Q1", "direct_hit", "问题一", [HIT_A])]

    results = evaluate_answer_cases(retrieval, fake_generate)

    assert len(calls) == 1
    assert calls[0][0] == "问题一"
    assert calls[0][1] == [HIT_A]
    assert results[0]["model_called"] is True
    assert results[0]["answer"] == "回答内容"


def test_does_not_call_model_without_hits():
    calls = []

    def fake_generate(question, hits):
        calls.append(question)
        return "不该出现"

    retrieval = [_retrieval_result("Q6", "no_hit", "如何建设火星基地？", [])]

    results = evaluate_answer_cases(retrieval, fake_generate)

    assert calls == []
    assert results[0]["model_called"] is False
    assert results[0]["answer"] == EMPTY_ANSWER


def test_records_answer_and_sources():
    def fake_generate(question, hits):
        return "返回None。[1]"

    retrieval = [_retrieval_result("Q1", "direct_hit", "问题一", [HIT_A])]

    results = evaluate_answer_cases(retrieval, fake_generate)

    result = results[0]
    assert result["id"] == "Q1"
    assert result["category"] == "direct_hit"
    assert result["question"] == "问题一"
    assert result["answer"] == "返回None。[1]"
    assert result["sources"] == [HIT_A]


def test_multiple_cases_do_not_mix():
    def fake_generate(question, hits):
        return f"回答：{question}"

    retrieval = [
        _retrieval_result("Q1", "direct_hit", "问题一", [HIT_A]),
        _retrieval_result("Q6", "no_hit", "问题六", []),
        _retrieval_result("Q2", "direct_hit", "问题二", [HIT_B]),
    ]

    results = evaluate_answer_cases(retrieval, fake_generate)

    assert [r["id"] for r in results] == ["Q1", "Q6", "Q2"]
    assert results[0]["answer"] == "回答：问题一"
    assert results[1]["answer"] == EMPTY_ANSWER
    assert results[2]["answer"] == "回答：问题二"
    assert results[0]["model_called"] is True
    assert results[1]["model_called"] is False
    assert results[2]["model_called"] is True
    assert results[0]["sources"] == [HIT_A]
    assert results[2]["sources"] == [HIT_B]
