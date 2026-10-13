import pytest
import task_db
from task_tools import query_tasks

def test_unicode_caseless_title_search(tmp_path):
    db = tmp_path / 'tasks.db'
    task_db.init_db(db)
    expected = task_db.create_task(db, 'Straße vocabulary')
    task_db.create_task(db, 'Other task')
    before = task_db.list_tasks(db)
    assert [t['id'] for t in query_tasks(db, title_query=' STRASSE ')] == [expected]
    assert task_db.list_tasks(db) == before

def test_ascii_blank_default_and_completed(tmp_path):
    db = tmp_path / 'tasks.db'
    task_db.init_db(db)
    task_db.create_task(db, 'Python Basics')
    task_db.create_task(db, 'Python Done', completed=True)
    assert len(query_tasks(db, title_query=' PYTHON ')) == 1
    assert len(query_tasks(db, completed=True, title_query='python')) == 1
    assert len(query_tasks(db, title_query='   ')) == 1
    assert len(query_tasks(db)) == 1
    assert query_tasks(db, title_query='missing') == []
    with pytest.raises(TypeError):
        query_tasks(db, title_query=12)
