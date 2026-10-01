import config


def test_default_db_path(monkeypatch):
    monkeypatch.delenv("TASK_DB_PATH", raising=False)

    assert config.get_db_path() == config.BASE_DIR / "tasks.db"


def test_absolute_path_env(monkeypatch, tmp_path):
    # 测试：环境变量设置绝对路径
    custom_db = tmp_path / "custom.db"
    monkeypatch.setenv("TASK_DB_PATH", str(custom_db))
    result = config.get_db_path()
    # 返回应当等于该绝对路径（resolve规范化）
    assert result == custom_db.resolve()

def test_relative_path_env(monkeypatch):
    # 测试：环境变量设置相对路径 "tasks_dev.db"
    monkeypatch.setenv("TASK_DB_PATH", "tasks_dev.db")
    result = config.get_db_path()
    expected = config.BASE_DIR / "tasks_dev.db"
    assert result == expected.resolve()

def test_empty_or_blank_env(monkeypatch):
    # 测试：空字符串、全空格，都回退到默认路径
    test_values = ["", " "]
    for val in test_values:
        monkeypatch.setenv("TASK_DB_PATH", val)
        assert config.get_db_path() == config.BASE_DIR / "tasks.db"