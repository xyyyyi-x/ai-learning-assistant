from weekly_report import calculate_weekly_stats


def test_empty_rows():
    assert calculate_weekly_stats([]) == {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "completion_rate": 0.0,
        "completed_titles": [],
        "pending_titles": [],
    }


def test_mixed_rows():
    rows = [
        (1, "复习HTTP", 1, 1),
        (2, "练习Tool Calling", 0, 3),
        (3, "编写测试", 1, 2),
    ]

    assert calculate_weekly_stats(rows) == {
        "total": 3,
        "completed": 2,
        "pending": 1,
        "completion_rate": 66.7,
        "completed_titles": ["复习HTTP", "编写测试"],
        "pending_titles": ["练习Tool Calling"],
    }


def test_all_completed():
    rows = [
        (1, "任务A", 1, 1),
        (2, "任务B", 1, 2),
    ]

    assert calculate_weekly_stats(rows) == {
        "total": 2,
        "completed": 2,
        "pending": 0,
        "completion_rate": 100.0,
        "completed_titles": ["任务A", "任务B"],
        "pending_titles": [],
    }


def test_all_pending():
    rows = [
        (1, "任务A", 0, 1),
        (2, "任务B", 0, 3),
    ]

    assert calculate_weekly_stats(rows) == {
        "total": 2,
        "completed": 0,
        "pending": 2,
        "completion_rate": 0.0,
        "completed_titles": [],
        "pending_titles": ["任务A", "任务B"],
    }
