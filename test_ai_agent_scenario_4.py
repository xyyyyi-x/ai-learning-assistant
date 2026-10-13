from weekly_report import format_weekly_summary

def test_summary_counts_and_rate():
    rows = [(1,'Python',1,1),(2,'HTTP',0,2)]
    before = list(rows)
    result = format_weekly_summary(rows)
    for text in ['任务总数：2','已完成：1','未完成：1','完成率：50.0%']:
        assert text in result
    assert rows == before

def test_empty_summary():
    result = format_weekly_summary([])
    assert '任务总数：0' in result
    assert '完成率：0.0%' in result
