import pytest
from playwright.sync_api import sync_playwright, expect, Page
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse, parse_qs


@pytest.fixture(scope="session")
def frontend_url():
    # 使用绝对目录，不依赖执行 pytest 时所在的位置。
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    handler = partial(SimpleHTTPRequestHandler, directory=str(frontend_dir))
    # 端口0让系统分配空闲端口，避免依赖8001或与现有服务冲突。
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
def page(frontend_url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        test_page = context.new_page()

        # 页面启动时会读取任务列表，返回模拟的空列表
        test_page.route(
            "**/tasks",
            lambda route: route.fulfill(json=[]),
        )

        try:
            test_page.goto(frontend_url)
            yield test_page
        finally:
            context.close()
            browser.close()


def test_ai_success(page):
    sent_bodies = []

    def handle_request(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            json={"suggestions": ["1. 练习参数", "2. 练习返回值"]},
        )

    page.route("**/ai/suggestions", handle_request)

    page.locator("#ai-goal").fill("  学习Python函数  ")
    page.locator("#ai-submit").click()

    inputs = page.locator("#ai-result .suggestion-title")
    expect(inputs).to_have_count(2)
    expect(inputs.nth(0)).to_have_value("1. 练习参数")
    expect(inputs.nth(1)).to_have_value("2. 练习返回值")

    expect(page.locator("#ai-message")).to_have_text("建议已生成")
    expect(page.locator("#ai-submit")).to_be_enabled()
    expect(page.locator("#ai-submit")).to_have_text("生成建议")

    assert sent_bodies == [{"goal": "学习Python函数"}]


# 测试A：空白输入不发送请求
def test_ai_empty_input(page):
    sent_bodies = []

    def handle_request(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            json={"suggestions": ["随便的内容"]},
        )

    page.route("**/ai/suggestions", handle_request)

    # 输入全空格
    page.locator("#ai-goal").fill(" ")
    page.locator("#ai-submit").click()

    expect(page.locator("#ai-message")).to_have_text("请输入学习目标")
    expect(page.locator("#ai-submit")).to_be_enabled()

    # 没有发出网络请求
    assert sent_bodies == []


# 测试B：后端返回502
def test_ai_backend_502(page):
    def handle_request(route):
        route.fulfill(
            status=502,
            json={"detail": "暂时无法生成有效建议"},
        )

    page.route("**/ai/suggestions", handle_request)

    page.locator("#ai-goal").fill("学习Python函数")
    page.locator("#ai-submit").click()

    expect(page.locator("#ai-message")).to_have_text("暂时无法生成有效建议")
    expect(page.locator("#ai-message")).to_have_class("error")
    expect(page.locator("#ai-submit")).to_be_enabled()
    expect(page.locator("#ai-submit")).to_have_text("生成建议")
    # 输入框保留原来内容
    expect(page.locator("#ai-goal")).to_have_value("学习Python函数")


# 测试C：网络失败，route.abort()模拟断网
def test_ai_network_fail(page):
    # abort 直接中断网络请求，模拟网络异常
    page.route(
        "**/ai/suggestions",
        lambda route: route.abort(),
    )

    page.locator("#ai-goal").fill("学习Python函数")
    page.locator("#ai-submit").click()

    expect(page.locator("#ai-message")).not_to_have_text("")
    expect(page.locator("#ai-message")).to_have_class("error")
    expect(page.locator("#ai-submit")).to_be_enabled()
    expect(page.locator("#ai-submit")).to_have_text("生成建议")
    expect(page.locator("#ai-goal")).to_have_value("学习Python函数")

def test_ai_loading_state(page):
    pending_routes = []

    def hold_request(route):
        pending_routes.append(route)

    page.route("**/ai/suggestions", hold_request)

    page.locator("#ai-goal").fill("学习Python函数")
    page.locator("#ai-submit").click()

    # 这些检查发生在响应返回之前
    expect(page.locator("#ai-submit")).to_be_disabled()
    expect(page.locator("#ai-submit")).to_have_text("生成中……")
    expect(
        page.locator("#ai-result .suggestion-item")
    ).to_have_count(0)

    assert len(pending_routes) == 1

    # 现在才让请求成功返回
    pending_routes[0].fulfill(
        status=200,
        json={"suggestions": ["练习函数参数"]},
    )

    expect(page.locator("#ai-submit")).to_be_enabled()
    expect(page.locator("#ai-submit")).to_have_text("生成建议")

    expect(
        page.locator("#ai-result .suggestion-title")
    ).to_have_value("练习函数参数")


def test_ai_clears_old_result(page):
    pending_routes = []

    def handle_request(route):
        pending_routes.append(route)
        if len(pending_routes) == 1:
            # 第一次请求立刻返回旧建议
            route.fulfill(
                status=200,
                json={"suggestions": ["这是旧建议"]},
            )
        # 第二次请求：只append，不fulfill，保持pending

    page.route("**/ai/suggestions", handle_request)

    # 提交第一个目标
    page.locator("#ai-goal").fill("第一个学习目标")
    page.locator("#ai-submit").click()
    # 断言显示旧建议
    inputs = page.locator("#ai-result .suggestion-title")
    expect(inputs.nth(0)).to_have_value("这是旧建议")

    # 输入第二个目标，再次提交
    page.locator("#ai-goal").fill("第二个学习目标")
    page.locator("#ai-submit").click()

    # 第二次请求已经发出，但是还没有给响应
    # 新请求发起时，前端清空旧结果，结果区域为空；按钮禁用
    expect(page.locator("#ai-submit")).to_be_disabled()
    expect(
        page.locator("#ai-result .suggestion-item")
    ).to_have_count(0)

    # 给第二次请求返回502错误
    pending_routes[1].fulfill(
        status=502,
        json={"detail": "暂时无法生成有效建议"},
    )

    # 请求失败：结果依旧为空，错误提示出现，按钮恢复
    expect(page.locator("#ai-message")).to_have_text("暂时无法生成有效建议")
    expect(page.locator("#ai-message")).to_have_class("error")
    expect(
        page.locator("#ai-result .suggestion-item")
    ).to_have_count(0)

    expect(page.locator("#ai-submit")).to_be_enabled()
    expect(page.locator("#ai-submit")).to_have_text("生成建议")


def test_ai_blocks_duplicate_submit(page):
    pending_routes = []

    def hold_request(route):
        pending_routes.append(route)

    page.route("**/ai/suggestions", hold_request)

    # 填入内容，点击提交，请求被卡住
    page.locator("#ai-goal").fill("学习Python基础")
    page.locator("#ai-submit").click()

    # 确认按钮已经被禁用
    expect(page.locator("#ai-submit")).to_be_disabled()
    assert len(pending_routes) == 1

    # 直接dispatch submit事件，模拟重复提交（绕过click，直接触发表单submit事件）
    page.locator("#ai-form").dispatch_event("submit")

    # 此时还没有放行第一个请求；不应该产生第二个网络请求
    assert len(pending_routes) == 1

    # 放行第一个请求，完成请求流程
    pending_routes[0].fulfill(
        status=200,
        json={"suggestions": ["练习基础语法"]},
    )

    # 等待页面渲染完成
    inputs = page.locator("#ai-result .suggestion-title")
    expect(inputs.nth(0)).to_have_value("练习基础语法")

    expect(page.locator("#ai-submit")).to_be_enabled()

    # 最终仍然只有1次请求，证明重复提交被JS的 if(aiSubmit.disabled) 拦截住
    assert len(pending_routes) == 1

def test_ai_edit_and_remove(page: Page):
    # 1. mock接口，模拟返回 ["练习函数参数", "编写三个测试"]
    page.route("**/ai/suggestions", lambda route: route.fulfill(
        json={
            "suggestions": ["练习函数参数", "编写三个测试"]
        }
    ))

    # 2. 输入目标并点击生成（和现有成功测试逻辑保持一致）
    page.locator("#ai-goal").fill("随便一个目标")
    page.locator("#ai-submit").click()

    # 等待渲染完成，确认一开始两条都存在
    inputs = page.locator("#ai-result .suggestion-title")
    expect(inputs).to_have_count(2)
    expect(inputs.nth(0)).to_have_value("练习函数参数")
    expect(inputs.nth(1)).to_have_value("编写三个测试")

    # 3. 将第一个候选输入框改为 "练习默认参数"，断言修改后的值
    inputs.nth(0).fill("练习默认参数")
    expect(inputs.nth(0)).to_have_value("练习默认参数")

    # 4. 移除第二条（nth(1)）
    page.locator(".suggestion-item").nth(1).get_by_role(
        "button",
        name="移除",
    ).click()

    # 断言只剩一条，第一条修改后的内容仍然保留
    expect(page.locator(".suggestion-item")).to_have_count(1)
    expect(inputs.nth(0)).to_have_value("练习默认参数")

    # 5. 移除最后一条
    page.locator(".suggestion-item").nth(0).get_by_role(
        "button",
        name="移除",
    ).click()

    # 断言候选行数量为0，并且 aiMessage 提示 “候选任务已全部移除”
    expect(page.locator(".suggestion-item")).to_have_count(0)
    expect(page.locator("#ai-message")).to_have_text("候选任务已全部移除")


def test_ai_save_edited_task(page):
    saved_tasks = []
    submitted = []

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)

            task = {
                "id": 1,
                "title": body["title"],
                "priority": body["priority"],
                "completed": False,
            }
            saved_tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            route.fulfill(status=200, json=saved_tasks)

    page.route("**/tasks", handle_tasks)
    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(
            json={"suggestions": ["练习函数参数"]}
        ),
    )

    page.locator("#ai-goal").fill("学习Python")
    page.locator("#ai-submit").click()

    row = page.locator(".suggestion-item")
    expect(row).to_have_count(1)

    row.locator(".suggestion-title").fill("练习默认参数")
    row.get_by_role("button", name="保存为任务").click()

    expect(page.locator("#ai-message")).to_have_text("任务已保存")
    expect(page.locator(".suggestion-item")).to_have_count(0)
    expect(page.locator("#task-list .task-text")).to_have_text(
        "练习默认参数 · 普通"
    )
    expect(page.locator("#ai-submit")).to_be_enabled()

    assert submitted == [
        {"title": "练习默认参数", "priority": 1}
    ]

def test_ai_save_empty_title(page):
    """场景：空白/全空格标题，提示错误，不发POST，候选行保留"""
    submitted = []

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": 1,
                "title": body["title"],
                "priority": body["priority"],
                "completed": False,
            }
            route.fulfill(status=201, json=task)
        else:
            route.fulfill(status=200, json=[])

    page.route("**/tasks", handle_tasks)
    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(json={"suggestions": ["练习函数参数"]}),
    )

    # 生成候选
    page.locator("#ai-goal").fill("学习Python")
    page.locator("#ai-submit").click()
    row = page.locator(".suggestion-item")
    expect(row).to_have_count(1)

    # 修改为全空格
    row.locator(".suggestion-title").fill("   ")
    row.get_by_role("button", name="保存为任务").click()

    # 断言
    expect(page.locator("#ai-message")).to_have_text("任务标题必须为1到50个字符")
    expect(row).to_have_count(1)  # 候选仍然存在，没有消失
    assert submitted == []  # 没有发出POST请求


def test_ai_save_post_500_error(page):
    """场景：POST /tasks 返回500保存失败；提示错误，编辑内容保留，候选仍在，控件恢复可用"""
    submitted = []

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            # POST直接返回500服务器错误
            route.fulfill(status=500, json={"detail": "服务器内部错误"})
        else:
            route.fulfill(status=200, json=[])

    page.route("**/tasks", handle_tasks)
    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(json={"suggestions": ["练习函数参数"]}),
    )

    page.locator("#ai-goal").fill("学习Python")
    page.locator("#ai-submit").click()
    row = page.locator(".suggestion-item")
    expect(row).to_have_count(1)

    # 修改标题，点击保存
    row.locator(".suggestion-title").fill("练习异常处理")
    row.get_by_role("button", name="保存为任务").click()

    # 断言
    expect(page.locator("#ai-message")).to_have_text("保存任务失败：HTTP 500")
    expect(row).to_have_count(1)  # 候选行保留，没有移除
    # 输入框内容保留
    expect(row.locator(".suggestion-title")).to_have_value("练习异常处理")
    # 生成按钮恢复可用
    expect(page.locator("#ai-submit")).to_be_enabled()
    expect(row.locator(".suggestion-title")).to_be_enabled()
    expect(row.get_by_role("button", name="保存为任务")).to_be_enabled()
    expect(row.get_by_role("button", name="移除")).to_be_enabled()
    assert submitted == [{"title": "练习异常处理", "priority": 1}]


def test_ai_save_ok_but_refresh_fail(page):
    """场景：POST成功201，但后续GET /tasks返回500刷新列表失败
    提示：任务已保存，但列表刷新失败，请刷新页面查看；候选移除，生成按钮恢复"""
    saved_tasks = []
    submitted = []

    def handle_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": 1,
                "title": body["title"],
                "priority": body["priority"],
                "completed": False,
            }
            saved_tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            # GET请求返回500，模拟loadTasks刷新失败
            route.fulfill(
                status=500,
                json={"detail": "模拟列表读取失败"},
            )

    page.route("**/tasks", handle_tasks)
    page.route(
        "**/ai/suggestions",
        lambda route: route.fulfill(json={"suggestions": ["练习函数参数"]}),
    )

    page.locator("#ai-goal").fill("学习Python")
    page.locator("#ai-submit").click()
    row = page.locator(".suggestion-item")
    expect(row).to_have_count(1)

    row.locator(".suggestion-title").fill("练习接口异常")
    row.get_by_role("button", name="保存为任务").click()

    # 断言
    expect(page.locator("#ai-message")).to_have_text(
        "任务已保存，但列表刷新失败，请刷新页面查看"
    )
    expect(page.locator(".suggestion-item")).to_have_count(0)  # 候选行已经删掉
    expect(page.locator("#ai-submit")).to_be_enabled()  # 生成按钮恢复
    assert submitted == [{"title": "练习接口异常", "priority": 1}]


def test_edit_title_trim_space(page):
    submitted = []
    saved_tasks = []

    # 同一个地址按请求方法区分：POST保存，GET读取列表。
    def route_tasks(route):
        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": 1,
                "title": body["title"],
                "priority": body["priority"],
                "completed": False,
            }
            saved_tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            route.fulfill(status=200, json=saved_tasks)

    page.route("**/tasks", route_tasks)

    # 先模拟AI返回建议，渲染出候选标题输入框（参考已有test_ai_save_edited_task）
    def route_ai_suggest(route):
        route.fulfill(status=200, json={"suggestions": ["练习默认参数"]})
    page.route("**/ai/suggestions", route_ai_suggest)

    # 输入学习目标，提交AI生成建议
    page.locator("#ai-goal").fill("学习python默认参数")
    page.locator("#ai-submit").click()
    # 等待候选标题区域渲染出来
    row = page.locator(".suggestion-item")
    expect(row).to_have_count(1)

    # ✅候选标题输入框 .suggestion-title，填入带前后空格文本
    row.locator(".suggestion-title").fill("  练习默认参数  ")

    # ✅按按钮文字定位：“保存为任务”
    row.get_by_role("button", name="保存为任务").click()

    # 等待异步保存和列表刷新完成，再检查实际发送的请求体。
    expect(page.locator("#ai-message")).to_have_text("任务已保存")
    expect(row).to_have_count(0)
    expect(page.locator("#task-list .task-text")).to_have_text(
        "练习默认参数 · 普通"
    )
    # 断言请求发送，并且标题已经trim掉首尾空格
    assert len(submitted) == 1
    assert submitted == [
        {"title": "练习默认参数", "priority": 1}
    ]



# 在 test_ai_frontend.py 文件末尾追加下面全部代码
def test_assistant_success(page):
    sent_bodies = []

    def handle_request(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            json={"answer": "你还有一条未完成任务：练习函数。"},
        )

    page.route("**/ai/assistant", handle_request)

    page.locator("#assistant-goal").fill("  查看未完成任务  ")
    page.locator("#assistant-submit").click()

    expect(page.locator("#assistant-result")).to_have_text(
        "你还有一条未完成任务：练习函数。"
    )
    expect(page.locator("#assistant-message")).to_have_text("查询完成")
    expect(page.locator("#assistant-submit")).to_be_enabled()
    expect(page.locator("#assistant-submit")).to_have_text("查询任务")

    assert sent_bodies == [{"goal": "查看未完成任务"}]


def test_assistant_empty_input(page):
    sent_bodies = []

    def handle_request(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(status=200, json={"answer": "随便"})

    page.route("**/ai/assistant", handle_request)

    page.locator("#assistant-goal").fill("   ")
    page.locator("#assistant-submit").click()

    expect(page.locator("#assistant-message")).to_have_text("请输入查询问题")
    expect(page.locator("#assistant-result")).to_have_text("")
    expect(page.locator("#assistant-submit")).to_be_enabled()
    expect(page.locator("#assistant-submit")).to_have_text("查询任务")

    # 没有发起网络请求，数组为空
    assert sent_bodies == []


def test_assistant_http_error(page):
    def handle_request(route):
        route.fulfill(
            status=502,
            json={"detail": "暂时无法完成任务查询"},
        )

    page.route("**/ai/assistant", handle_request)

    page.locator("#assistant-goal").fill("查看任务")
    page.locator("#assistant-submit").click()

    expect(page.locator("#assistant-message")).to_have_text("暂时无法完成任务查询")
    expect(page.locator("#assistant-result")).to_have_text("")
    expect(page.locator("#assistant-submit")).to_be_enabled()
    expect(page.locator("#assistant-submit")).to_have_text("查询任务")


def test_assistant_waiting_state(page):
    pending_routes = []

    def hold_request(route):
        pending_routes.append(route)
        # 暂时不 fulfill，请求挂起

    page.route("**/ai/assistant", hold_request)

    # 预先填入旧回答
    page.locator("#assistant-result").evaluate(
        "(element) => element.textContent = '上一次的回答'"
    )

    page.locator("#assistant-goal").fill("查看未完成任务")
    with page.expect_request("**/ai/assistant"):
        page.locator("#assistant-submit").click()

    # A. 检查等待中的状态（请求还没返回）
    expect(page.locator("#assistant-submit")).to_be_disabled()
    expect(page.locator("#assistant-submit")).to_have_text("查询中……")
    expect(page.locator("#assistant-result")).to_have_text("")

    # B. 手动返回响应
    assert len(pending_routes) == 1
    pending_routes[0].fulfill(
        status=200,
        json={"answer": "这是新的查询结果。"},
    )

    # C. 请求完成后的状态
    expect(page.locator("#assistant-result")).to_have_text("这是新的查询结果。")
    expect(page.locator("#assistant-message")).to_have_text("查询完成")
    expect(page.locator("#assistant-submit")).to_be_enabled()
    expect(page.locator("#assistant-submit")).to_have_text("查询任务")


def test_knowledge_success(page):
    sent_bodies = []

    def handle_request(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            json={
                "answer": "返回None。[1]",
                "sources": [
                    {
                        "reference_id": 1,
                        "source": "python.md",
                        "chunk_index": 3,
                        "text": "普通函数没有显式返回值时返回None。",
                    }
                ],
            },
        )

    page.route("**/ai/knowledge", handle_request)

    page.locator("#knowledge-question").fill("  函数返回什么？  ")
    page.locator("#knowledge-keywords").fill("  函数 返回  ")
    page.locator("#knowledge-submit").click()

    expect(page.locator("#knowledge-answer")).to_have_text("返回None。[1]")
    expect(page.locator("#knowledge-sources")).to_contain_text(
        "[1] python.md · 片段 3"
    )
    expect(page.locator("#knowledge-sources")).to_contain_text(
        "普通函数没有显式返回值时返回None。"
    )
    expect(page.locator("#knowledge-message")).to_have_text("查询完成")
    expect(page.locator("#knowledge-submit")).to_be_enabled()
    expect(page.locator("#knowledge-submit")).to_have_text("查询资料")

    assert sent_bodies == [
        {
            "question": "函数返回什么？",
            "keywords": "函数 返回",
        }
    ]


@pytest.mark.parametrize("question, keywords", [
    ("   ", "函数"),
    ("函数是什么？", "   "),
])
def test_knowledge_empty_input(page, question, keywords):
    sent_bodies = []

    def handle_request(route):
        sent_bodies.append(route.request.post_data_json)
        route.fulfill(status=200, json={"answer": "随便", "sources": []})

    page.route("**/ai/knowledge", handle_request)

    page.locator("#knowledge-question").fill(question)
    page.locator("#knowledge-keywords").fill(keywords)
    page.locator("#knowledge-submit").click()

    expect(page.locator("#knowledge-message")).to_have_text(
        "问题和检索关键词不能为空"
    )
    expect(page.locator("#knowledge-submit")).to_be_enabled()
    expect(page.locator("#knowledge-submit")).to_have_text("查询资料")

    # 没有发请求
    assert sent_bodies == []


def test_knowledge_no_hits(page):
    page.route(
        "**/ai/knowledge",
        lambda route: route.fulfill(
            status=200,
            json={
                "answer": "未检索到相关资料，请调整关键词。",
                "sources": [],
            },
        ),
    )

    # 先放入旧回答和旧来源，否则无法证明清空逻辑有效
    page.locator("#knowledge-answer").evaluate(
        "(element) => element.textContent = '旧回答'"
    )
    page.locator("#knowledge-sources").evaluate(
        """(element) => {
            const item = document.createElement('p');
            item.textContent = '旧来源';
            element.appendChild(item);
        }"""
    )

    page.locator("#knowledge-question").fill("火星基地如何供氧？")
    page.locator("#knowledge-keywords").fill("火星基地")
    page.locator("#knowledge-submit").click()

    expect(page.locator("#knowledge-answer")).to_have_text(
        "未检索到相关资料，请调整关键词。"
    )
    expect(page.locator("#knowledge-sources > *")).to_have_count(0)
    expect(page.locator("#knowledge-message")).to_have_text("查询完成")
    expect(page.locator("#knowledge-submit")).to_be_enabled()
    expect(page.locator("#knowledge-submit")).to_have_text("查询资料")


def test_knowledge_http_error(page):
    page.route(
        "**/ai/knowledge",
        lambda route: route.fulfill(
            status=502,
            json={"detail": "暂时无法生成有效的资料回答"},
        ),
    )

    # 先放入旧回答和旧来源
    page.locator("#knowledge-answer").evaluate(
        "(element) => element.textContent = '旧回答'"
    )
    page.locator("#knowledge-sources").evaluate(
        """(element) => {
            const item = document.createElement('p');
            item.textContent = '旧来源';
            element.appendChild(item);
        }"""
    )

    page.locator("#knowledge-question").fill("函数是什么？")
    page.locator("#knowledge-keywords").fill("函数")
    page.locator("#knowledge-submit").click()

    expect(page.locator("#knowledge-message")).to_have_text(
        "暂时无法生成有效的资料回答"
    )
    expect(page.locator("#knowledge-answer")).to_have_text("")
    expect(page.locator("#knowledge-sources > *")).to_have_count(0)
    expect(page.locator("#knowledge-submit")).to_be_enabled()
    expect(page.locator("#knowledge-submit")).to_have_text("查询资料")


def test_knowledge_waiting_state(page):
    pending_routes = []

    def hold_request(route):
        pending_routes.append(route)
        # 不 fulfill，请求挂起

    page.route("**/ai/knowledge", hold_request)

    # 先放入旧回答和旧来源
    page.locator("#knowledge-answer").evaluate(
        "(element) => element.textContent = '旧回答'"
    )
    page.locator("#knowledge-sources").evaluate(
        """(element) => {
            const item = document.createElement('p');
            item.textContent = '旧来源';
            element.appendChild(item);
        }"""
    )

    page.locator("#knowledge-question").fill("函数是什么？")
    page.locator("#knowledge-keywords").fill("函数")
    with page.expect_request("**/ai/knowledge"):
        page.locator("#knowledge-submit").click()

    # 等待中的状态（响应还没返回）
    expect(page.locator("#knowledge-submit")).to_be_disabled()
    expect(page.locator("#knowledge-submit")).to_have_text("查询中……")
    expect(page.locator("#knowledge-answer")).to_have_text("")
    expect(page.locator("#knowledge-sources > *")).to_have_count(0)

    assert len(pending_routes) == 1

    # 放行请求
    pending_routes[0].fulfill(
        status=200,
        json={
            "answer": "返回None。[1]",
            "sources": [
                {
                    "reference_id": 1,
                    "source": "python.md",
                    "chunk_index": 3,
                    "text": "普通函数没有显式返回值时返回None。",
                }
            ],
        },
    )

    expect(page.locator("#knowledge-answer")).to_have_text("返回None。[1]")
    expect(page.locator("#knowledge-sources")).to_contain_text(
        "[1] python.md · 片段 3"
    )
    expect(page.locator("#knowledge-message")).to_have_text("查询完成")
    expect(page.locator("#knowledge-submit")).to_be_enabled()
    expect(page.locator("#knowledge-submit")).to_have_text("查询资料")


def test_priority_filter_requests_and_results(page):
    task_a = {"id": 1, "title": "普通任务A", "completed": False, "priority": 1}
    task_b = {"id": 2, "title": "紧急任务B", "completed": False, "priority": 3}

    captured = []

    def handle_all(route):
        captured.append(
            parse_qs(urlparse(route.request.url).query, keep_blank_values=True)
        )
        route.fulfill(json=[task_a, task_b])

    def handle_filtered(route):
        query = parse_qs(
            urlparse(route.request.url).query, keep_blank_values=True
        )
        captured.append(query)
        priority = query.get("priority", [""])[0]
        if priority == "1":
            route.fulfill(json=[task_a])
        elif priority == "3":
            route.fulfill(json=[task_b])
        else:
            route.fulfill(json=[])

    page.route("**/tasks", handle_all)
    page.route("**/tasks?*", handle_filtered)

    # 普通
    page.locator("#priority-filter").select_option("1")
    expect(page.locator("#task-list .task-text")).to_have_text(
        ["普通任务A · 普通"]
    )

    # 紧急
    page.locator("#priority-filter").select_option("3")
    expect(page.locator("#task-list .task-text")).to_have_text(
        ["紧急任务B · 紧急"]
    )

    # 重要（空）
    page.locator("#priority-filter").select_option("2")
    expect(page.locator("#task-list .task-text")).to_have_count(0)

    # 全部
    page.locator("#priority-filter").select_option("")
    expect(page.locator("#task-list .task-text")).to_have_text(
        ["普通任务A · 普通", "紧急任务B · 紧急"]
    )

    # 检查请求参数：普通、紧急、重要、全部
    assert captured[0] == {"priority": ["1"]}
    assert captured[1] == {"priority": ["3"]}
    assert captured[2] == {"priority": ["2"]}
    assert captured[3] == {}  # 全部是 {}，不是 {"priority": [""]}


def test_priority_filter_loading(page):
    pending_routes = []
    request_count = 0

    def handle_filtered(route):
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            route.fulfill(
                json=[{"id": 1, "title": "旧任务", "completed": False, "priority": 1}]
            )
        else:
            pending_routes.append(route)

    page.route("**/tasks?*", handle_filtered)

    # 第一次筛选：显示旧任务
    page.locator("#priority-filter").select_option("1")
    expect(page.locator("#task-list .task-text")).to_have_text(["旧任务 · 普通"])

    # 第二次筛选：请求挂起
    page.locator("#priority-filter").select_option("3")

    expect(page.locator("#priority-filter")).to_be_disabled()
    expect(page.locator("#task-list .task-text")).to_have_count(0)
    expect(page.locator("#message")).to_have_text("正在筛选任务……")

    # 返回新任务
    assert len(pending_routes) == 1
    pending_routes[0].fulfill(
        json=[{"id": 2, "title": "新任务", "completed": False, "priority": 3}]
    )

    expect(page.locator("#task-list .task-text")).to_have_text(["新任务 · 紧急"])
    expect(page.locator("#priority-filter")).to_be_enabled()


def test_priority_filter_empty(page):
    def handle_filtered(route):
        query = parse_qs(
            urlparse(route.request.url).query, keep_blank_values=True
        )
        priority = query.get("priority", [""])[0]
        if priority == "1":
            route.fulfill(
                json=[{"id": 1, "title": "旧任务", "completed": False, "priority": 1}]
            )
        else:
            route.fulfill(json=[])

    page.route("**/tasks?*", handle_filtered)

    # 先显示旧任务
    page.locator("#priority-filter").select_option("1")
    expect(page.locator("#task-list .task-text")).to_have_text(["旧任务 · 普通"])

    # 切换到空结果
    page.locator("#priority-filter").select_option("2")
    expect(page.locator("#task-list .task-text")).to_have_count(0)
    expect(page.locator("#task-count")).to_have_text("当前显示0条任务，已完成0条")
    expect(page.locator("#message")).to_be_empty()
    expect(page.locator("#priority-filter")).to_be_enabled()


@pytest.mark.parametrize("fail_mode", ["http_500", "abort"])
def test_priority_filter_failure(page, fail_mode):
    request_count = 0

    def handle_filtered(route):
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            route.fulfill(
                json=[{"id": 1, "title": "旧任务", "completed": False, "priority": 1}]
            )
        else:
            if fail_mode == "http_500":
                route.fulfill(status=500, json={"detail": "服务器错误"})
            else:
                route.abort()

    page.route("**/tasks?*", handle_filtered)

    # 先显示旧任务
    page.locator("#priority-filter").select_option("1")
    expect(page.locator("#task-list .task-text")).to_have_text(["旧任务 · 普通"])

    # 下一次筛选失败
    page.locator("#priority-filter").select_option("3")

    expect(page.locator("#message")).to_contain_text("筛选失败")
    expect(page.locator("#task-list .task-text")).to_have_count(0)
    expect(page.locator("#priority-filter")).to_be_enabled()


def test_priority_filter_kept_after_create(page):
    tasks = [
        {"id": 1, "title": "普通任务A", "completed": False, "priority": 1}
    ]
    submitted = []
    requests_log = []
    next_id = 2

    def handle_tasks(route):
        nonlocal next_id
        query = parse_qs(
            urlparse(route.request.url).query, keep_blank_values=True
        )
        requests_log.append((route.request.method, query))

        if route.request.method == "POST":
            body = route.request.post_data_json
            submitted.append(body)
            task = {
                "id": next_id,
                "title": body["title"],
                "completed": False,
                "priority": body["priority"],
            }
            next_id += 1
            tasks.append(task)
            route.fulfill(status=201, json=task)
        else:
            priority = query.get("priority", [None])[0]
            if priority is None:
                route.fulfill(json=tasks)
            else:
                route.fulfill(
                    json=[t for t in tasks if str(t["priority"]) == priority]
                )

    page.route("**/tasks", handle_tasks)
    page.route("**/tasks?*", handle_tasks)

    # 1. 选择"普通"筛选，确认显示普通任务A
    page.locator("#priority-filter").select_option("1")
    expect(page.locator("#task-list .task-text")).to_have_text(["普通任务A · 普通"])

    # 2. 创建表单填写"紧急任务B"，优先级选紧急（3）
    page.locator("#task-title").fill("紧急任务B")
    page.locator("#task-priority").select_option("3")

    # 3. 点击添加任务
    page.locator("#task-form").get_by_role("button", name="添加任务").click()

    # 4. 等待添加成功提示
    expect(page.locator("#message")).to_have_text("任务已添加")

    # POST 正文确实是紧急任务
    assert submitted == [{"title": "紧急任务B", "priority": 3}]

    # 请求顺序：筛选GET → POST → 刷新GET，刷新时仍带 priority=1
    assert requests_log == [
        ("GET", {"priority": ["1"]}),
        ("POST", {}),
        ("GET", {"priority": ["1"]}),
    ]

    # 筛选框仍为"普通"
    assert page.input_value("#priority-filter") == "1"

    # 列表仍只有普通任务A，没混入紧急任务B
    expect(page.locator("#task-list .task-text")).to_have_text(["普通任务A · 普通"])

    # 5. 切换到紧急，能看到刚创建的B
    page.locator("#priority-filter").select_option("3")
    expect(page.locator("#task-list .task-text")).to_have_text(["紧急任务B · 紧急"])
