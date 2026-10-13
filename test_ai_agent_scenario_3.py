from weekly_report import calculate_weekly_stats

def test_interleaved_titles_preserve_order_and_input():
    rows = [(1,'A',0,1),(2,'B',1,2),(3,'C',0,3),(4,'D',1,1)]
    before = list(rows)
    stats = calculate_weekly_stats(rows)
    assert stats['completed_titles'] == ['B','D']
    assert stats['pending_titles'] == ['A','C']
    assert stats['completion_rate'] == 50.0
    assert rows == before
