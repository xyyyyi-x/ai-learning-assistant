import pytest
from playwright.sync_api import sync_playwright, expect
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


DIST_DIR = Path(__file__).resolve().parent / "vue-frontend" / "dist"


@pytest.fixture(scope="session")
def vue_url():
    if not (DIST_DIR / "index.html").is_file():
        raise RuntimeError(
            "未找到 vue-frontend/dist，请先在 vue-frontend 目录执行 npm run build"
        )

    handler = partial(SimpleHTTPRequestHandler, directory=str(DIST_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def page(vue_url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        test_page = context.new_page()

        # 页面挂载时会读取任务列表，默认给空列表
        test_page.route("**/tasks", lambda route: route.fulfill(json=[]))
        test_page.route(
            "**/ai/suggestions",
            lambda route: route.fulfill(status=200, json={"suggestions": []}),
        )

        try:
            test_page.goto(vue_url)
            yield test_page
        finally:
            context.close()
            browser.close()


def test_generate_edit_remove(page):
    sent_bodies = []

    def handle_ai(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            json={"suggestions": ["练习函数参数", "编写三个测试"]},
        )

    page.route("**/ai/suggestions", handle_ai)

    page.get_by_label("学习目标").fill("  学习Python函数  ")
    page.get_by_role("button", name="生成建议").click()

    inputs = page.locator(".suggestion-title")
    expect(inputs).to_have_count(2)

    # 请求体中的目标已去掉首尾空格
    assert sent_bodies == [{"goal": "学习Python函数"}]

    # 修改第一条
    inputs.nth(0).fill("改过的第一条")
    expect(inputs.nth(0)).to_have_value("改过的第一条")

    # 删除第二条，不影响第一条的编辑结果
    page.locator(".suggestion-item").nth(1).get_by_role(
        "button", name="移除"
    ).click()
    expect(page.locator(".suggestion-item")).to_have_count(1)
    expect(inputs.nth(0)).to_have_value("改过的第一条")

    # 全部删除
    page.locator(".suggestion-item").nth(0).get_by_role(
        "button", name="移除"
    ).click()
    expect(page.locator(".suggestion-item")).to_have_count(0)
    expect(page.get_by_test_id("ai-message")).to_have_text(
        "候选任务已全部移除"
    )


def test_save_edited_title(page):
    submitted = []
    saved_tasks = []

    def handle_ai(route):
        route.fulfill(status=200, json={"suggestions": ["原始AI标题"]})

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": 1,
                "title": body["title"],
                "completed": False,
                "priority": body["priority"],
            }
            saved_tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            route.fulfill(status=200, json=saved_tasks)

    page.route("**/ai/suggestions", handle_ai)
    page.route("**/tasks", handle_tasks)

    page.get_by_label("学习目标").fill("学习Python")
    page.get_by_role("button", name="生成建议").click()

    input_box = page.locator(".suggestion-title")
    expect(input_box).to_have_count(1)
    input_box.nth(0).fill("用户编辑后的标题")

    page.get_by_role("button", name="保存为任务").click()

    expect(page.get_by_test_id("ai-message")).to_have_text("任务已保存")
    expect(page.locator(".suggestion-item")).to_have_count(0)
    expect(page.get_by_test_id("task-list")).to_contain_text("用户编辑后的标题")

    assert submitted == [
        {"title": "用户编辑后的标题", "priority": 1}
    ]


def test_blank_suggestion_title(page):
    submitted = []

    def handle_tasks(route):
        if route.request.method == "POST":
            submitted.append(route.request.post_data_json)
            route.fulfill(
                status=201,
                json={"id": 1, "title": "x", "completed": False, "priority": 1},
            )
        else:
            route.fulfill(status=200, json=[])

    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(status=200, json={"suggestions": ["原始标题"]}),
    )
    page.route("**/tasks", handle_tasks)

    page.get_by_label("学习目标").fill("学习Python")
    page.get_by_role("button", name="生成建议").click()

    input_box = page.locator(".suggestion-title")
    expect(input_box).to_have_count(1)
    input_box.nth(0).fill("   ")

    page.get_by_role("button", name="保存为任务").click()

    expect(page.get_by_test_id("ai-message")).to_have_text(
        "任务标题必须为1到50个字符"
    )
    expect(page.locator(".suggestion-item")).to_have_count(1)
    assert submitted == []


def test_save_post_failure(page):
    submitted = []

    def handle_tasks(route):
        if route.request.method == "POST":
            submitted.append(route.request.post_data_json)
            route.fulfill(status=500, json={"detail": "服务器内部错误"})
        else:
            route.fulfill(status=200, json=[])

    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(status=200, json={"suggestions": ["原始标题"]}),
    )
    page.route("**/tasks", handle_tasks)

    page.get_by_label("学习目标").fill("学习Python")
    page.get_by_role("button", name="生成建议").click()

    input_box = page.locator(".suggestion-title")
    expect(input_box).to_have_count(1)
    input_box.nth(0).fill("编辑后保留")

    page.get_by_role("button", name="保存为任务").click()

    expect(page.get_by_test_id("ai-message")).to_have_text(
        "保存任务失败：HTTP 500"
    )
    expect(page.locator(".suggestion-item")).to_have_count(1)
    expect(input_box.nth(0)).to_have_value("编辑后保留")
    expect(input_box.nth(0)).to_be_enabled()
    expect(page.get_by_role("button", name="保存为任务")).to_be_enabled()
    expect(page.get_by_role("button", name="移除")).to_be_enabled()

    assert submitted == [{"title": "编辑后保留", "priority": 1}]


def test_save_ok_but_refresh_fails(page):
    submitted = []
    post_done = False

    def handle_tasks(route):
        nonlocal post_done
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            post_done = True
            route.fulfill(
                status=201,
                json={
                    "id": 1,
                    "title": body["title"],
                    "completed": False,
                    "priority": body["priority"],
                },
            )
        else:
            if post_done:
                # 保存之后的刷新
                route.fulfill(status=500, json={"detail": "模拟列表读取失败"})
            else:
                # 页面首次加载
                route.fulfill(status=200, json=[])

    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(status=200, json={"suggestions": ["原始标题"]}),
    )
    page.route("**/tasks", handle_tasks)

    page.get_by_label("学习目标").fill("学习Python")
    page.get_by_role("button", name="生成建议").click()

    input_box = page.locator(".suggestion-title")
    expect(input_box).to_have_count(1)
    input_box.nth(0).fill("保存后刷新失败")

    page.get_by_role("button", name="保存为任务").click()

    expect(page.get_by_test_id("ai-message")).to_have_text(
        "任务已保存，但列表刷新失败，请刷新页面查看"
    )
    # 候选已移除，且不恢复
    expect(page.locator(".suggestion-item")).to_have_count(0)
    # 生成按钮恢复可用
    expect(page.get_by_role("button", name="生成建议")).to_be_enabled()

    assert submitted == [{"title": "保存后刷新失败", "priority": 1}]


def test_save_default_priority(page):
    submitted = []
    saved_tasks = []

    def handle_ai(route):
        route.fulfill(status=200, json={"suggestions": ["原始标题"]})

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": 1,
                "title": body["title"],
                "completed": False,
                "priority": body["priority"],
            }
            saved_tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            route.fulfill(status=200, json=saved_tasks)

    page.route("**/ai/suggestions", handle_ai)
    page.route("**/tasks", handle_tasks)

    page.get_by_label("学习目标").fill("学习Python")
    page.get_by_role("button", name="生成建议").click()

    expect(page.locator(".suggestion-item")).to_have_count(1)

    # 不修改优先级，直接保存
    page.get_by_role("button", name="保存为任务").click()

    expect(page.get_by_test_id("ai-message")).to_have_text("任务已保存")
    expect(page.get_by_test_id("task-list")).to_contain_text("原始标题 · 普通")

    assert submitted == [{"title": "原始标题", "priority": 1}]


def test_save_urgent_priority(page):
    submitted = []
    saved_tasks = []

    def handle_ai(route):
        route.fulfill(status=200, json={"suggestions": ["原始AI标题"]})

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": 1,
                "title": body["title"],
                "completed": False,
                "priority": body["priority"],
            }
            saved_tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            route.fulfill(status=200, json=saved_tasks)

    page.route("**/ai/suggestions", handle_ai)
    page.route("**/tasks", handle_tasks)

    page.get_by_label("学习目标").fill("学习Python")
    page.get_by_role("button", name="生成建议").click()

    input_box = page.locator(".suggestion-title")
    expect(input_box).to_have_count(1)
    input_box.nth(0).fill("用户编辑后的标题")

    # 把候选改成"紧急"
    page.locator(".suggestion-priority").select_option("3")

    page.get_by_role("button", name="保存为任务").click()

    expect(page.get_by_test_id("ai-message")).to_have_text("任务已保存")
    expect(page.get_by_test_id("task-list")).to_contain_text(
        "用户编辑后的标题 · 紧急"
    )

    assert submitted == [
        {"title": "用户编辑后的标题", "priority": 3}
    ]
