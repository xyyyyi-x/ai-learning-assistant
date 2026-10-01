from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, model_validator, ValidationError
from contextlib import asynccontextmanager
from pathlib import Path
import task_db
from config import get_db_path
from fastapi.staticfiles import StaticFiles
import requests
import model_client
import agent_loop
import agent_model_client
import langchain_service
import rag_service

# =========在这里新增你的SuggestionRequest=========
class SuggestionRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=200)


class RagRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    keywords: str = Field(min_length=1, max_length=200)

DB_PATH = get_db_path()

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"


@asynccontextmanager
async def lifespan(app: FastAPI):
    task_db.init_db(DB_PATH)
    yield

app = FastAPI(lifespan=lifespan)

# ----- 新增：数据库元组转接口字典 -----
def task_to_dict(row: tuple) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "completed": bool(row[2]),
        "priority": row[3],
    }

# ----- 下面才是各个 @app.get / @app.post 接口 -----



# ----- 原有模型，不动 -----
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    completed: bool = False
    priority: int = Field(default=1, ge=1, le=3, strict=True)


# ✅新增：PATCH局部更新专用模型 TaskUpdate
class TaskUpdate(BaseModel):
    completed: bool = Field(strict=True)






@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    task_id = task_db.create_task(
        DB_PATH,
        task.title,
        completed=task.completed,
        priority=task.priority,
    )
    row = task_db.get_task(DB_PATH, task_id)
    return task_to_dict(row)


@app.get("/tasks")
def list_tasks(priority: int | None = Query(default=None, ge=1, le=3)):
    rows = task_db.list_tasks(DB_PATH, priority=priority)
    return [task_to_dict(row) for row in rows]


@app.get("/tasks/{task_id}")
def read_task(task_id: int):
    row = task_db.get_task(DB_PATH, task_id)

    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task_to_dict(row)



@app.patch("/tasks/{task_id}")
def update_task(task_id: int, update_data: TaskUpdate):
    ok = task_db.update_completed(DB_PATH, task_id, update_data.completed)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    row = task_db.get_task(DB_PATH, task_id)
    return task_to_dict(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    ok = task_db.delete_task(DB_PATH, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "任务已删除", "id": task_id}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/double/{number}")
def get_double(number: int):
    return {"number": number, "result": number * 2}

@app.get("/greet")
def greet(name: str = "同学"):
    return {"message": f"您好, {name}!"}

# ✅ POST，不是 get！
@app.post("/tasks/preview")
def task_preview(task: TaskCreate):
    return task.model_dump()


FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

@app.post("/ai/suggestions")
def create_suggestions(body: SuggestionRequest):
    goal = body.goal.strip()
    if not goal:
        raise HTTPException(
            status_code=422,
            detail="学习目标不能为空",
        )

    try:
        suggestions = model_client.generate_suggestions(goal)

        # ①超时，优先捕获（子类放前面）
    except requests.exceptions.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail="模型服务响应超时，请稍后重试",
        ) from exc

        # ②其他网络类异常（HTTPError、连接错误等，RequestException是父类）
    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="模型服务请求失败",
        ) from exc

        # ③业务异常：ValueError（空回答、截断、结构异常等）
    except ValueError as exc:
        # 具体原因仅输出到服务终端；校验错误不打印模型原文。
        if isinstance(exc, ValidationError):
            details = exc.errors(
                include_input=False, include_context=False, include_url=False
            )
            print("生成建议失败：模型输出校验未通过", details, flush=True)
        else:
            print("生成建议失败：", str(exc), flush=True)
        raise HTTPException(
            status_code=502,
            detail="暂时无法生成有效建议",
        ) from exc

        # try‑except全部处理完毕，正常返回结果
    return {"suggestions": suggestions}



app.mount(
    "/ui",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)



# ========= api_app.py末尾，app.mount(...) 之前新增这个路由 =========
@app.post("/ai/assistant")
def ask_assistant(body: SuggestionRequest):
    goal = body.goal.strip()
    if not goal:
        raise HTTPException(
            status_code=422,
            detail="学习目标不能为空",
        )

    try:
        answer = langchain_service.run_langchain_assistant(
            goal=goal,
            db_path=DB_PATH,
        )
    except requests.exceptions.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail="模型服务响应超时，请稍后重试"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="模型服务请求失败"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="暂时无法完成任务查询"
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="任务查询超过调用次数上限"
        ) from exc

    return {"answer": answer}


@app.post("/ai/knowledge")
def ask_knowledge(body: RagRequest):
    question = body.question.strip()
    keywords = body.keywords.strip()

    if not question or not keywords:
        raise HTTPException(
            status_code=422,
            detail="问题和检索关键词不能为空",
        )

    try:
        result = rag_service.answer_question(
            question=question,
            keywords=keywords,
            knowledge_dir=KNOWLEDGE_DIR,
        )
    except requests.exceptions.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail="模型服务响应超时，请稍后重试",
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="模型服务请求失败",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="暂时无法生成有效的资料回答",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="学习资料读取失败",
        ) from exc

    return result
