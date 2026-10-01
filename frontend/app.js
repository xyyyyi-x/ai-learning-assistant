let tasks = [];

const taskList = document.querySelector("#task-list");
const taskCount = document.querySelector("#task-count");
const taskForm = document.querySelector("#task-form");
const taskTitle = document.querySelector("#task-title");
const message = document.querySelector("#message");
const taskPriority = document.querySelector("#task-priority");
const priorityFilter = document.querySelector("#priority-filter");


function showMessage(text, type = "") {
    message.textContent = text;
    message.className = type;
}


function renderTasks() {
    taskList.replaceChildren();

    for (const task of tasks) {
        const item = document.createElement("li");
        item.className = "task-item";
        // 根据任务completed状态，自动添加/移除done类
        item.classList.toggle("done", task.completed);

        // 创建切换完成状态按钮【练习B新增】
        const toggleButton = document.createElement("button");
        toggleButton.type = "button";
        // 根据状态设置按钮文字
        if (task.completed) {
            toggleButton.textContent = "取消完成";
        } else {
            toggleButton.textContent = "标记完成";
        }


        // 按钮点击事件：改造为 async，发送PATCH
        toggleButton.addEventListener("click", async function () {
            // 禁用当前按钮，防止重复点击
            toggleButton.disabled = true;
            message.textContent = "";

            try {
                const response = await fetch(`/tasks/${task.id}`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        completed: !task.completed
                    })
                });
                if (!response.ok) {
                    throw new Error(`更新任务失败：${response.status}`);
                }
                await loadTasks();
                showMessage("任务状态已更新", "success");
            } catch (error) {
                showMessage(`操作失败：${error.message}`, "error");
            } finally {
                toggleButton.disabled = false;
            }

        });


                // 创建删除按钮
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.textContent = "删除";

        // 删除按钮点击异步事件
        deleteButton.addEventListener("click", async function () {
            // 弹出确认框，点取消直接return，什么都不做
            const confirmed = window.confirm(`确定删除任务“${task.title}”吗？`);
            if (!confirmed) {
                return;
            }

            // 获取当前这条任务的两个按钮
            const togBtn = toggleButton;
            const delBtn = deleteButton;

            // 两个按钮全部禁用，清空提示
            togBtn.disabled = true;
            delBtn.disabled = true;
            showMessage("");

            try {
                const response = await fetch(`/tasks/${task.id}`, {
                    method: "DELETE"
                });

                if (!response.ok) {
                    throw new Error(`删除任务失败：${response.status}`);
                }

                // 删除成功，重新拉取列表
                await loadTasks();
                // loadTasks完成之后才展示成功提示
                showMessage("任务已删除", "success");

            } catch (error) {
                showMessage(`操作失败：${error.message}`, "error");
            } finally {
                // 无论成功失败，恢复两个按钮
                togBtn.disabled = false;
                delBtn.disabled = false;
            }
        });




        const text = document.createElement("span");
        text.className = "task-text";
        // 在renderTasks函数内部，for (const task of tasks) 循环里面
        // 增加映射
        let priorityText;
        if(task.priority === 1){
            priorityText = "普通";
        }else if(task.priority === 2){
            priorityText = "重要";
        }else if(task.priority === 3){
            priorityText = "紧急";
        }
        // 拼接显示文字
        text.textContent = `${task.title} · ${priorityText}`;


        // 把按钮、文字span都放到li里面
        item.append(toggleButton);
        item.append(text);
        item.append(deleteButton);
        taskList.append(item);


    }

    // =========练习C开始：统计已完成数量=========
    let completedCount = 0;
    for (const t of tasks) {
        if (t.completed) {
            completedCount += 1;
        }
    }
    taskCount.textContent = `当前显示${tasks.length}条任务，已完成${completedCount}条`;
}


// 添加任务：表单提交事件
taskForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const title = taskTitle.value.trim();
    // 在 const title = taskTitle.value.trim(); 下面新增
    const priority = Number(taskPriority.value);


    // 校验：标题为空
    if (!title) {
        showMessage("请输入任务标题", "error");
        return;
    }

    const submitButton = taskForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    message.textContent = "";

    try {
        const response = await fetch("/tasks", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ title: title ,priority: priority})
        });

        if (!response.ok) {
            throw new Error(`创建任务失败：${response.status}`);
        }
        taskTitle.value = "";
        taskPriority.value = "1"; // 恢复默认普通
        await loadTasks();
        showMessage("任务已添加", "success");
    } catch (error) {
        showMessage(`操作失败：${error.message}`, "error");
    } finally {
        submitButton.disabled = false;
    }

});


async function loadTasks() {
    let url = "/tasks";
    if (priorityFilter.value === "1") {
        url = "/tasks?priority=1";
    } else if (priorityFilter.value === "2") {
        url = "/tasks?priority=2";
    } else if (priorityFilter.value === "3") {
        url = "/tasks?priority=3";
    }

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`读取任务失败：${response.status}`);
    }

    tasks = await response.json();
    renderTasks();
}


priorityFilter.addEventListener("change", async function () {
    priorityFilter.disabled = true;
    tasks = [];
    renderTasks();
    showMessage("正在筛选任务……");

    try {
        await loadTasks();
        showMessage("");
    } catch (error) {
        showMessage(`筛选失败：${error.message}`, "error");
    } finally {
        priorityFilter.disabled = false;
    }
});

async function init() {
    showMessage("正在加载任务……");

    try {
        await loadTasks();
        showMessage("");
    } catch (error) {
        showMessage(`加载失败：${error.message}`, "error");
    }
}

init();

async function requestSuggestions(goal) {
    const response = await fetch("/ai/suggestions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ goal: goal })
    });

    const data = await response.json();

    if (!response.ok) {
        const detail = typeof data.detail === "string"
            ? data.detail
            : `生成失败：HTTP ${response.status}`;

        throw new Error(detail);
    }

    if (
        !Array.isArray(data.suggestions) ||
        data.suggestions.length === 0 ||
        !data.suggestions.every(
            item => typeof item === "string" && item.trim().length > 0
        )
    ) {
        throw new Error("服务器没有返回有效建议");
    }

    return data.suggestions;
}

// 获取页面元素
const aiForm = document.querySelector("#ai-form");
const aiGoal = document.querySelector("#ai-goal");
const aiSubmit = document.querySelector("#ai-submit");
const aiMessage = document.querySelector("#ai-message");
const aiResult = document.querySelector("#ai-result");


// aiForm 表单提交事件
aiForm.addEventListener("submit", async function (event) {
    // 阻止表单默认提交刷新页面
    event.preventDefault();

    // 防止重复提交，如果按钮已经禁用直接返回
    if (aiSubmit.disabled) {
        return;
    }

    // 获取并去除首尾空白
    const goal = aiGoal.value.trim();

    // 目标为空，提示直接返回，不发请求
    if (!goal) {
        aiMessage.textContent = "请输入学习目标";
        aiMessage.className = "error";
        return;
    }

    // 禁用按钮，修改文字；清空旧结果、清除错误样式
    aiSubmit.disabled = true;
    aiSubmit.textContent = "生成中……";
    aiResult.replaceChildren();
    aiMessage.textContent = "";
    aiMessage.className = "";

    try {
        // 调用请求函数，等待后端返回AI建议
        const suggestions = await requestSuggestions(goal);
        // 使用 textContent 设置文本，安全展示，不会解析HTML
        renderSuggestions(suggestions);
        aiMessage.textContent = "建议已生成";
        aiMessage.className = "";

    } catch (error) {
        // 捕获异常，展示错误信息，加上error类变红
        aiMessage.textContent = error.message;
        aiMessage.className = "error";

    } finally {
        // 无论成功失败，都恢复按钮状态
        aiSubmit.disabled = false;
        aiSubmit.textContent = "生成建议";
    }
});

let savingSuggestion = false;

function renderSuggestions(suggestions) {
    aiResult.replaceChildren();

    for (const title of suggestions) {
        const row = document.createElement("div");
        row.className = "suggestion-item";

        const input = document.createElement("input");
        input.type = "text";
        input.className = "suggestion-title";
        input.maxLength = 50;
        input.value = title;
        input.setAttribute("aria-label", "候选任务标题");

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = "移除";
        const saveButton = document.createElement("button");
        saveButton.type = "button";
        saveButton.textContent = "保存为任务";


        saveButton.addEventListener("click", async () => {
            // 1. 开始前检查：正在保存中就直接返回，防止并发
            if (savingSuggestion) {
                return;
            }

            // 读取输入框当前编辑后的值，trim去除首尾空格
            const editedTitle = input.value.trim();

            // 校验标题：1‑50字符
            if (editedTitle.length === 0 || editedTitle.length > 50) {
                aiMessage.textContent = "任务标题必须为1到50个字符";
                aiMessage.className = "error";
                return;
            }

            // 2. 进入保存流程，设置加载状态，全部禁用
            savingSuggestion = true;
            saveButton.disabled = true;
            removeButton.disabled = true;
            input.disabled = true;
            aiSubmit.disabled = true;
            saveButton.textContent = "保存中……";
            aiMessage.textContent = "";
            aiMessage.className = "";

            try {
                // 调用保存接口，提交编辑后的标题
                await saveSuggestedTask(editedTitle);

                // POST成功：移除当前候选行
                row.remove();

                // 刷新正式任务列表，单独try‑catch：保存成功但刷新失败不回滚保存结果
                try {
                    await loadTasks();
                    aiMessage.textContent = "任务已保存";
                    aiMessage.className = "";
                } catch (error) {
                    aiMessage.textContent = "任务已保存，但列表刷新失败，请刷新页面查看";
                    aiMessage.className = "error";
                }

            } catch (error) {
                // POST /tasks 保存失败的异常捕获
                aiMessage.textContent = error.message;
                aiMessage.className = "error";

            } finally {
                // 无论成功失败，一定会执行：恢复状态
                savingSuggestion = false;
                aiSubmit.disabled = false;   // 恢复生成按钮可用

                // 如果row已经被row.remove()，操作DOM元素不会报错，只是无效
                saveButton.disabled = false;
                removeButton.disabled = false;
                input.disabled = false;
                saveButton.textContent = "保存为任务";
            }
        });

        removeButton.addEventListener("click", function () {
            row.remove();
            if (aiResult.children.length === 0) {
                aiMessage.textContent = "候选任务已全部移除";
            }
        });

        row.append(input, saveButton, removeButton);
        aiResult.append(row);
    }
}

async function saveSuggestedTask(title) {
    const response = await fetch("/tasks", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            title: title,
            priority: 1
        })
    });

    if (!response.ok) {
        throw new Error(`保存任务失败：HTTP ${response.status}`);
    }
}


async function requestAssistant(goal) {
    // POST 请求 /ai/assistant
    const response = await fetch("/ai/assistant", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ goal: goal }),
    });

    const data = await response.json();

    // HTTP不成功，抛出错误，优先读取detail
    if (!response.ok) {
        if (typeof data.detail === "string") {
            throw new Error(data.detail);
        } else {
            throw new Error(`任务查询失败：HTTP ${response.status}`);
        }
    }

    // 校验返回的answer是非空字符串
    if (
        typeof data.answer !== "string" ||
        data.answer.trim().length === 0
    ) {
        throw new Error("服务器没有返回有效回答");
    }

    // 返回去除首尾空白的回答
    return data.answer.trim();
}


// 获取页面DOM元素
const assistantForm = document.querySelector("#assistant-form");
const assistantGoal = document.querySelector("#assistant-goal");
const assistantSubmit = document.querySelector("#assistant-submit");
const assistantMessage = document.querySelector("#assistant-message");
const assistantResult = document.querySelector("#assistant-result");


assistantForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (assistantSubmit.disabled) {
    return;
}

    // B.读取输入，去除空格
    const goal = assistantGoal.value.trim();
    if (!goal) {
        assistantMessage.textContent = "请输入查询问题";
        return;
    }

    // C.清空旧结果，禁用按钮防止重复提交
    assistantResult.textContent = "";
    assistantMessage.textContent = "";
    assistantMessage.style.color = "";  // 清除上一次错误留下的红色
    assistantSubmit.disabled = true;
    assistantSubmit.textContent = "查询中……";

    try {
        // D 调用接口拿到回答
        const answer = await requestAssistant(goal);
        assistantResult.textContent = answer;
        assistantMessage.textContent = "查询完成";
    } catch (error) {
        // E 捕获错误展示
        assistantMessage.textContent = error.message;
        assistantMessage.style.color = "#dc2626";
    } finally {
        // F 无论成功失败，都恢复按钮
        assistantSubmit.disabled = false;
        assistantSubmit.textContent = "查询任务";
    }
});


async function requestKnowledge(question, keywords) {
    const response = await fetch("/ai/knowledge", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, keywords }),
    });

    const data = await response.json();

    if (!response.ok) {
        if (typeof data.detail === "string") {
            throw new Error(data.detail);
        } else {
            throw new Error(`资料查询失败：HTTP ${response.status}`);
        }
    }

    if (
        typeof data !== "object" ||
        data === null ||
        typeof data.answer !== "string" ||
        data.answer.trim().length === 0 ||
        !Array.isArray(data.sources)
    ) {
        throw new Error("服务器没有返回有效的资料回答");
    }

    return data;
}

const knowledgeForm = document.querySelector("#knowledge-form");
const knowledgeQuestion = document.querySelector("#knowledge-question");
const knowledgeKeywords = document.querySelector("#knowledge-keywords");
const knowledgeSubmit = document.querySelector("#knowledge-submit");
const knowledgeMessage = document.querySelector("#knowledge-message");
const knowledgeAnswer = document.querySelector("#knowledge-answer");
const knowledgeSources = document.querySelector("#knowledge-sources");

function renderKnowledge(data) {
    knowledgeAnswer.textContent = data.answer.trim();
    knowledgeSources.replaceChildren();

    if (data.sources.length === 0) {
        return;
    }

    const title = document.createElement("p");
    title.textContent = "本次参考资料（请核对是否支持回答）";
    knowledgeSources.appendChild(title);

    for (const source of data.sources) {
        const item = document.createElement("div");

        const heading = document.createElement("p");
        heading.textContent =
            `[${source.reference_id}] ${source.source} · 片段 ${source.chunk_index}`;

        const text = document.createElement("p");
        text.textContent = source.text;

        item.append(heading, text);
        knowledgeSources.appendChild(item);
    }
}

knowledgeForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (knowledgeSubmit.disabled) {
        return;
    }

    const question = knowledgeQuestion.value.trim();
    const keywords = knowledgeKeywords.value.trim();

    if (!question || !keywords) {
        knowledgeMessage.textContent = "问题和检索关键词不能为空";
        knowledgeMessage.style.color = "#dc2626";
        return;
    }

    knowledgeAnswer.textContent = "";
    knowledgeSources.replaceChildren();
    knowledgeMessage.textContent = "";
    knowledgeMessage.style.color = "";

    knowledgeSubmit.disabled = true;
    knowledgeSubmit.textContent = "查询中……";

    try {
        const data = await requestKnowledge(question, keywords);
        renderKnowledge(data);
        knowledgeMessage.textContent = "查询完成";
    } catch (error) {
        knowledgeMessage.textContent = error.message;
        knowledgeMessage.style.color = "#dc2626";
    } finally {
        knowledgeSubmit.disabled = false;
        knowledgeSubmit.textContent = "查询资料";
    }
});
