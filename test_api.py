import pytest
from fastapi.testclient import TestClient

import api_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    test_db_path = tmp_path / "test_api.db"
    monkeypatch.setattr(api_app, "DB_PATH", test_db_path)

    with TestClient(api_app.app) as test_client:
        yield test_client


def test_create_and_read(client):
    response = client.post(
        "/tasks",
        json={"title": "学习自动化测试"},
    )
    assert response.status_code == 201

    created = response.json()
    assert created == {
        "id": 1,
        "title": "学习自动化测试",
        "completed": False,
        "priority": 1,
    }

    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created

def test_list_starts_empty(client):
    # 首次获取任务列表，是空列表
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert resp.json() == []

    # 创建一个任务
    create_resp = client.post("/tasks", json={"title": "列表测试任务", "priority": 2})
    assert create_resp.status_code == 201
    task = create_resp.json()

    # 创建后列表要包含完整任务
    list_resp = client.get("/tasks")
    task_list = list_resp.json()
    assert task in task_list


def test_update_status(client):
    # 创建任务
    create_resp = client.post("/tasks", json={"title": "修改状态测试", "priority": 2})
    assert create_resp.status_code == 201
    task = create_resp.json()
    task_id = task["id"]

    # PATCH completed=True
    patch1 = client.patch(f"/tasks/{task_id}", json={"completed": True})
    assert patch1.status_code == 200
    get1 = client.get(f"/tasks/{task_id}")
    data1 = get1.json()
    assert data1["completed"] is True
    # 其他字段不变
    assert data1["title"] == task["title"]
    assert data1["priority"] == task["priority"]

    # PATCH改回 False
    patch2 = client.patch(f"/tasks/{task_id}", json={"completed": False})
    assert patch2.status_code == 200
    get2 = client.get(f"/tasks/{task_id}")
    data2 = get2.json()
    assert data2["completed"] is False
    assert data2 == task


def test_invalid_update_keeps_state(client):
    # 创建原始任务
    create_resp = client.post("/tasks", json={"title": "非法更新测试", "priority": 2})
    assert create_resp.status_code == 201
    task = create_resp.json()
    task_id = task["id"]

    # 4组非法PATCH，全部断言422
    r1 = client.patch(f"/tasks/{task_id}", json={})
    assert r1.status_code == 422

    r2 = client.patch(f"/tasks/{task_id}", json={"completed": "true"})
    assert r2.status_code == 422

    r3 = client.patch(f"/tasks/{task_id}", json={"completed": 1})
    assert r3.status_code == 422

    r4 = client.patch(f"/tasks/{task_id}", json={"completed": None})
    assert r4.status_code == 422

    # 全部非法请求结束，统一GET校验数据完全没变化
    final_get = client.get(f"/tasks/{task_id}")
    assert final_get.json() == task


def test_delete_task(client):
    # 创建任务A、B
    resp_a = client.post("/tasks", json={"title": "任务A待删除", "priority": 2})
    assert resp_a.status_code == 201
    task_a = resp_a.json()
    tid_a = task_a["id"]

    resp_b = client.post("/tasks", json={"title": "任务B不能被删", "priority": 3})
    assert resp_b.status_code == 201
    task_b = resp_b.json()
    tid_b = task_b["id"]

    # 删除A，断言200以及约定返回json
    del_resp = client.delete(f"/tasks/{tid_a}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"message": "任务已删除", "id": tid_a}

    # 查询A返回404
    get_a = client.get(f"/tasks/{tid_a}")
    assert get_a.status_code == 404
    assert get_a.json() == {"detail": "任务不存在"}

    # 列表不含A
    list_resp = client.get("/tasks")
    id_list = [item["id"] for item in list_resp.json()]
    assert tid_a not in id_list

    # B仍然完好
    get_b = client.get(f"/tasks/{tid_b}")
    assert get_b.json() == task_b

    # 再次删除已删除的A，返回404
    del_again = client.delete(f"/tasks/{tid_a}")
    assert del_again.status_code == 404
    assert del_again.json() == {"detail": "任务不存在"}

    # 对已删除A执行合法PATCH，也返回404
    patch_del = client.patch(f"/tasks/{tid_a}", json={"completed": True})
    assert patch_del.status_code == 404
    assert patch_del.json() == {"detail": "任务不存在"}


def test_list_filter_priority(client):
    # 创建 A（优先级1）、B（优先级3）、C（优先级1）
    a = client.post("/tasks", json={"title": "任务A", "priority": 1})
    assert a.status_code == 201
    a_data = a.json()

    b = client.post("/tasks", json={"title": "任务B", "priority": 3})
    assert b.status_code == 201
    b_data = b.json()

    c = client.post("/tasks", json={"title": "任务C", "priority": 1})
    assert c.status_code == 201
    c_data = c.json()

    # 不传参数返回全部，按 id 升序 A、B、C
    all_resp = client.get("/tasks")
    assert all_resp.status_code == 200
    assert all_resp.json() == [a_data, b_data, c_data]

    # 筛选1返回 A、C
    p1 = client.get("/tasks", params={"priority": 1})
    assert p1.status_code == 200
    assert p1.json() == [a_data, c_data]

    # 筛选3返回 B
    p3 = client.get("/tasks", params={"priority": 3})
    assert p3.status_code == 200
    assert p3.json() == [b_data]

    # 筛选2返回空列表
    p2 = client.get("/tasks", params={"priority": 2})
    assert p2.status_code == 200
    assert p2.json() == []


def test_list_filter_priority_2(client):
    # 创建 priority=2 的任务
    resp = client.post("/tasks", json={"title": "优先级2任务", "priority": 2})
    assert resp.status_code == 201
    task = resp.json()

    # 筛选2能命中
    p2 = client.get("/tasks", params={"priority": 2})
    assert p2.status_code == 200
    assert p2.json() == [task]


@pytest.mark.parametrize("bad_priority", ["0", "4", "abc", "true", ""])
def test_list_filter_invalid_priority(client, bad_priority):
    # 先创建一条任务
    resp = client.post("/tasks", json={"title": "非法参数测试", "priority": 2})
    assert resp.status_code == 201
    task = resp.json()

    # 非法参数 → 422
    r = client.get("/tasks", params={"priority": bad_priority})
    assert r.status_code == 422

    # 确认任务仍存在且内容不变
    get_resp = client.get(f"/tasks/{task['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json() == task
