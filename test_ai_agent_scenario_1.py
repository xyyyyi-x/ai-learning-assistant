import pytest
import task_db
from task_tools import query_tasks

def test_priority_filter_is_read_only_and_composes(tmp_path):
    db = tmp_path / 'tasks.db'
    task_db.init_db(db)
    a = task_db.create_task(db, 'Python', priority=1)
    b = task_db.create_task(db, 'HTTP', priority=2)
    task_db.create_task(db, 'Done', completed=True, priority=2)
    before = task_db.list_tasks(db)
    assert [t['id'] for t in query_tasks(db)] == [a, b]
    assert [t['id'] for t in query_tasks(db, priority=2)] == [b]
    assert len(query_tasks(db, completed=True, priority=2)) == 1
    assert len(query_tasks(db, priority=None)) == 2
    assert query_tasks(db, priority=3) == []
    assert task_db.list_tasks(db) == before

@pytest.mark.parametrize('priority,error', [(True, TypeError), ('1', TypeError), (0, ValueError), (4, ValueError)])
def test_invalid_priority(tmp_path, priority, error):
    db = tmp_path / 'tasks.db'
    task_db.init_db(db)
    with pytest.raises(error):
        query_tasks(db, priority=priority)
