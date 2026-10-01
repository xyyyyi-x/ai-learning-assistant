# AI学习任务管理与资料问答应用

使用Python、FastAPI、SQLite和原生HTML/CSS/JavaScript实现学习任务管理，接入DeepSeek生成可编辑的学习建议，并通过LangChain工具调用查询已有任务。

支持基于Markdown学习资料的关键词检索问答：读取资料、分块、检索相关片段，再请求模型回答，并在网页展示回答和参考来源。未命中资料时直接返回提示，不调用模型。

项目还包含两个独立练习工程，以及学习周报工作流和RAG质量评测模块：

- `vue-frontend/`：用 Vue 3 + Vite 重写任务页面的练习。它通过 Vite 开发代理连接同一个 FastAPI 后端。**目前只在开发环境可用，生产构建产物尚未接入后端**。FastAPI 在 `/ui/` 提供并展示的仍然是原生 HTML/CSS/JavaScript 页面。
- `mysql_practice/`：独立的 MySQL 学习练习，使用自己的数据库 `ai_learning_practice` 和练习账号。**它不是本项目的正式数据库**，主项目的数据仍然存放在 SQLite 中。
- 学习周报模块（`weekly_report.py`、`weekly_report_model.py`、`weekly_report_service.py`）：由 Python 计算确定性统计，再由模型组织周报文字。离线测试使用模拟模型响应；运行 `19_weekly_report_demo.py` 会调用真实模型。
- RAG 质量评测（`rag_evaluation.py`）：支持固定案例的检索和回答质量评测。`20_rag_quality_eval.py` 只做离线检索评测，不调用模型；`21_rag_answer_quality_eval.py` 会调用真实模型并产生 API 用量。

## 环境与安装

开发环境为 Windows PowerShell、Python 3.14.2。SQLite 随 Python 提供，无需另装数据库服务。以下命令均从本仓库根目录执行。

```powershell
python -m venv .venv-langchain
.\.venv-langchain\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-langchain\Scripts\python.exe -m pip check
```

已有 `.venv-langchain` 时跳过创建步骤。`pip check` 只检查依赖兼容性，不验证业务代码。

运行浏览器测试还需要下载 Playwright 使用的 Chromium，仅安装 Python 依赖不够：

```powershell
.\.venv-langchain\Scripts\python.exe -m playwright install chromium
```

首次使用时，将 `.env.example` 复制为 `.env`，在本地填写自己的密钥，再运行 `start_app.py`。已有 `.env` 时不要覆盖。

在仓库根目录执行以下命令，仅当 `.env` 不存在时才创建它：

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

随后在编辑器中打开本地 `.env`，填写 `MODEL_API_KEY`，检查模型、基础地址和数据库路径后保存。`.env.example` 是可提交的配置模板，密钥保持空白；真实 `.env` 仅保存在本地，不提交 Git。

## 模型配置与启动

### 本机便捷启动

已配置本地 `.env` 时，在仓库根目录执行：

```powershell
.\.venv-langchain\Scripts\python.exe .\start_app.py
```

`start_app.py` 会从自身目录读取 `.env`，并以文件中的值覆盖当前进程中的同名环境变量，再启动8000端口的服务。配置文件包含 `MODEL_API_KEY`、`MODEL_NAME`、`MODEL_BASE_URL` 和 `TASK_DB_PATH`；本机使用 `tasks_dev.db`。文件已被 Git 忽略，不要提交真实密钥。其他人获取项目后需要自行配置自己的 `.env`，或使用下面的手动配置方式。

启动前先停止已占用8000端口的旧服务。此脚本不启用自动重载，修改代码或 `.env` 后需要停止并重新运行。

### 手动配置方式

| 环境变量 | 用途 | 示例 |
| --- | --- | --- |
| `MODEL_API_KEY` | 模型服务密钥 | 通过隐藏输入设置 |
| `MODEL_NAME` | 请求使用的模型 | `deepseek-v4-pro` |
| `MODEL_BASE_URL` | 模型服务基础地址 | `https://api.deepseek.com` |

基础地址不要包含 `/chat/completions`，调用函数会自动拼接。模型名称应与账户实际可调用的模型一致。

在准备启动服务的 PowerShell 中执行：

```powershell
$env:MODEL_BASE_URL = "https://api.deepseek.com"
$env:MODEL_NAME = "deepseek-v4-pro"
$secureKey = Read-Host "请输入DeepSeek API Key" -AsSecureString
$env:MODEL_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
Remove-Variable secureKey

.\.venv-langchain\Scripts\python.exe -m uvicorn api_app:app --reload --host 127.0.0.1 --port 8000
```

输入密钥时内容会被隐藏，不要把真实密钥写入代码、README 或 Git。

`$env:...` 属于当前 PowerShell 进程，从同一窗口启动的 Python 才能继承这些设置。新开终端通常需要重新配置；修改启动终端中的配置后，需要重启服务。直接运行上述 uvicorn 命令不会自动读取 `.env`；只有 `start_app.py` 会显式加载它。

仅使用任务管理功能可以不配置模型；调用 AI 接口前必须补齐配置。真实生成建议需要网络并产生 API 用量，自动化测试无需密钥。

启动后访问：

- [前端页面](http://127.0.0.1:8000/ui/)
- [接口文档](http://127.0.0.1:8000/docs)
- [健康检查](http://127.0.0.1:8000/health)

在服务终端按 `Ctrl+C` 停止。应用首页在 `/ui/`，根路径 `/` 返回404是正常的。

## Docker本机运行

前提：安装并启动 Docker Desktop，使用 Linux 容器。按前面的模型配置说明准备 `.env`。Docker 使用 `KEY=value` 格式读取变量，值不要额外加引号。以下命令从仓库根目录执行。

构建镜像：

```powershell
docker build -t ai-learning-app:d16 .
```

准备数据目录并启动：

```powershell
New-Item -ItemType Directory -Path "..\docker-practice-data" -Force
$practiceData = (Resolve-Path "..\docker-practice-data").Path

docker run --rm -d --name ai-learning-web-d16 -p 127.0.0.1:8002:8000 --mount "type=bind,source=$practiceData,target=/data" --env-file .env --env TASK_DB_PATH=/data/web_tasks.db ai-learning-app:d16
```

检查与停止：

```powershell
docker logs ai-learning-web-d16
Invoke-RestMethod "http://127.0.0.1:8002/health"
docker stop ai-learning-web-d16
```

- 页面地址：http://127.0.0.1:8002/ui/。
- 日志出现启动完成后再访问；健康检查应返回 `{"status":"ok"}`。
- 数据库保存在 Windows 的 `docker-practice-data/web_tasks.db`。
- 停止后容器自动删除；重新执行启动命令、使用相同挂载目录和数据库路径，可读取已有任务。
- `.env` 在运行时注入，不复制进镜像、不提交 Git。
- 本次验证范围为本机 Docker 运行，未验证公网部署。

修改代码或配置后如何生效：

- 修改 Python 代码：需要停止并删除旧容器，重新构建包含新代码的镜像，再用新镜像启动容器，运行中的应用才会使用新代码。
- 只修改 `.env`：不需要重新构建镜像；先停止并删除旧容器，再用带 `--env-file .env` 的 `docker run` 创建新容器，即可应用新配置。

## 自动化测试

### 后端测试

不需要启动 uvicorn，也不需要模型密钥。数据库相关测试使用临时路径，模型调用使用模拟响应。

```powershell
.\.venv-langchain\Scripts\python.exe -m pytest -q `
  --ignore=test_ai_frontend.py `
  --ignore=test_vue_frontend.py `
  --ignore=mysql_practice
```

排除范围与 GitHub Actions 的后端 CI 保持一致：不跑需要浏览器的前端测试，也不跑需要独立 MySQL 服务的集成测试。通过数量以实际输出为准。模拟测试通过不代表真实模型服务或密钥当前可用。

### 前端浏览器测试

测试真实 HTML 和 JavaScript，拦截任务列表与 AI 请求并返回模拟数据。测试会自动启动临时静态服务，使用系统分配的空闲端口，并在结束时自动关闭。无需另开终端，不需要 FastAPI，也不会请求真实模型。

在仓库根目录执行：

```powershell
.\.venv-langchain\Scripts\python.exe -m pytest test_ai_frontend.py -q
```

截至2026年10月1日，在一个干净的 Python 3.14.2 环境里实测：后端离线测试（与 CI 相同范围）201 项通过，原生前端浏览器测试 29 项通过，Vue 浏览器测试 7 项通过。后续数量以实际运行输出为准。浏览器测试覆盖建议生成、候选编辑保存、任务查询助手、资料问答、优先级筛选和 Vue 页面的任务 CRUD，包括正常结果、非法输入、错误提示及等待状态。

模拟测试验证程序处理逻辑，不证明真实模型服务可用，也不保证模型回答与引用正确。真实模型验证需要自行配置密钥并单独运行，同时人工核对回答、引用和用量。

测试页面使用临时端口，应用页面仍为 `http://127.0.0.1:8000/ui/`。测试静态服务没有真实 AI 接口，模拟响应由 Playwright 提供。

不带过滤条件运行 `pytest` 会同时运行前后端测试，静态服务同样自动启动和关闭。编号06～09的客户端练习脚本则需要 FastAPI 运行，不能用静态服务代替。

### GitHub Actions后端CI

仓库包含 `.github/workflows/backend-tests.yml`，在影响后端、前端、知识库或工作流的 push 和 pull request 中运行离线检查。

CI 使用 Python 3.14，并从根目录 `requirements.txt` 安装依赖。当前范围不需要模型密钥，不调用真实模型 API，也不连接真实 MySQL；独立前端任务还会执行 Vue 的非修改式 lint 和生产构建。

当前 CI 排除：

- `test_ai_frontend.py`：需要 Playwright 和 Chromium；
- `test_vue_frontend.py`：需要 Vue 生产构建及浏览器；
- `mysql_practice`：需要独立 MySQL 服务及测试配置。

这些测试被排除表示本 CI 不验证相应能力，不能把后端 CI 通过理解成浏览器、MySQL、真实模型或生产部署均可用。

### Vue 前端的开发、构建与部署边界

`vue-frontend/` 目前只走通了开发环境，三件事要分开看：

| 环节 | 当前状态 |
| --- | --- |
| 开发代理 | `npm run dev` 时，Vite 把 `/tasks` 和 `/ai` 代理到 `127.0.0.1:8000`，浏览器访问 5173 即可连到真实后端。**已验证可用。** |
| 生产构建 | `npm run build` 能生成 `vue-frontend/dist/`。**已验证能构建。** |
| 正式部署 | FastAPI 的 `/ui/` 挂载的是 `frontend`（原生页面），**并没有挂载 `vue-frontend/dist`**，也没有配置反向代理。因此 Vue 生产产物**尚未被正式提供**，只能在开发服务器上访问。 |

所以：`npm run build` 成功，只说明代码能编译成静态文件，**不等于 Vue 已经部署上线**。当前对外可访问的正式页面仍然是 `/ui/` 的原生页面。

截至 2026 年 9 月 30 日，本地 Windows 干净虚拟环境验证结果以实际测试记录为准。当前仓库已经发布到 GitHub。2026年10月1日，GitHub Actions 首次真实运行成功：后端离线测试、Vue ESLint检查和Vue生产构建均通过。该工作流不验证浏览器测试、MySQL集成测试、真实模型调用或公网部署。

## 文件说明

| 文件 | 职责 |
| --- | --- |
| `api_app.py` | FastAPI 接口、请求校验、异常转换及静态页面挂载 |
| `task_db.py` | SQLite 初始化及增删改查，不处理 HTTP 异常 |
| `config.py` | 数据库路径配置 |
| `model_config.py` | 读取模型环境变量并检查必填项 |
| `model_client.py` | 请求模型，校验正文和结束原因，返回建议或抛出异常 |
| `suggestion_parser.py` | 解析模型正文中的JSON，校验建议数量、标题类型和长度，返回标题列表 |
| `start_app.py` | 从本地 `.env` 加载配置并启动应用 |
| `langchain_agent.py`、`langchain_tools.py` | 创建查询Agent及绑定数据库的工具 |
| `langchain_service.py` | 执行Agent、检查最终回答及转换异常 |
| `knowledge_loader.py` | 读取Markdown资料 |
| `knowledge_splitter.py` | 分块并保留来源与编号 |
| `knowledge_retriever.py` | 关键词评分与检索 |
| `rag_prompt.py` | 构造问题及参考资料消息 |
| `rag_model_client.py` | 请求模型并检查响应 |
| `rag_service.py` | 串联检索、模型回答和来源整理 |
| `16_rag_live_demo.py` | 命令行真实资料问答演示 |
| `rag_evaluation.py` | RAG 检索质量与模型回答质量的离线评测 |
| `20_rag_quality_eval.py` | 离线运行固定案例的检索质量评测，不调用模型 |
| `21_rag_answer_quality_eval.py` | 运行真实模型回答质量评测，会产生 API 用量 |
| `weekly_report.py` | 学习周报的确定性统计（由 Python 计算数字） |
| `weekly_report_model.py` | 把统计事实交给模型组织成中文周报文字 |
| `weekly_report_service.py` | 串联查询、统计、模型和保存周报 |
| `19_weekly_report_demo.py` | 命令行生成一次真实周报 |
| `frontend/index.html` | 原生页面结构（FastAPI 在 `/ui/` 提供） |
| `frontend/style.css` | 原生页面样式及提示颜色 |
| `frontend/app.js` | 原生页面的任务交互、AI 请求、结果展示及按钮状态管理 |
| `vue-frontend/` | Vue 3 + Vite 前端练习，含 Vue 组件、页面状态和浏览器测试；通过 Vite 开发代理连接 FastAPI，**目前未接入后端正式提供** |
| `mysql_practice/` | 独立的 MySQL 练习目录，含建表脚本、Python CRUD 模块、错误分类和集成测试；使用自己的库 `ai_learning_practice`，**不是主项目数据库** |
| `test_task_db.py`、`test_config.py` | 数据库操作及路径配置测试 |
| `test_api.py` | 使用 TestClient 的任务接口测试 |
| `test_model_config.py`、`test_model_client.py` | 模型配置与调用的离线测试 |
| `test_ai_api.py` | AI 接口的成功、输入校验与异常映射测试 |
| `test_suggestion_parser.py` | 建议JSON格式、数据结构和标题业务规则测试 |
| `test_ai_frontend.py` | 原生页面的 Playwright 浏览器自动化测试 |
| `test_vue_frontend.py` | Vue 页面的 Playwright 浏览器测试，读取 `vue-frontend/dist`，需先执行 `npm run build` |
| `test_knowledge_*.py`、`test_rag_*.py` | 资料读取、分块、检索、问答和 RAG 评测的离线测试 |
| `test_weekly_report*.py` | 周报统计、模型客户端和完整工作流的离线测试 |
| `requirements.txt` | Python 依赖及版本清单 |
| `.env.example` | 不含真实密钥的配置模板 |

编号开头的 Python 文件属于学习练习脚本，真实模型调用脚本会产生 API 用量。

## 接口清单

| HTTP 方法 | 路径 | 作用 | 成功状态码 |
| --- | --- | --- | --- |
| POST | `/tasks` | 创建任务 | 201 |
| GET | `/tasks` | 获取任务列表 | 200 |
| GET | `/tasks/{task_id}` | 获取指定任务 | 200 |
| PATCH | `/tasks/{task_id}` | 修改完成状态 | 200 |
| DELETE | `/tasks/{task_id}` | 删除任务 | 200 |
| POST | `/ai/suggestions` | 根据学习目标生成建议 | 200 |
| POST | `/ai/assistant` | 根据SQLite任务进行只读问答 | 200 |
| POST | `/ai/knowledge` | 根据学习资料回答问题并返回参考来源 | 200 |
| GET | `/health` | 健康检查 | 200 |
| GET | `/double/{number}` | 数字翻倍练习 | 200 |
| GET | `/greet` | 问候练习 | 200 |
| POST | `/tasks/preview` | 仅校验并预览任务，不存入数据库 | 200 |

AI 请求示例为 `{"goal": "学习Python函数"}`，成功响应为 `{"suggestions": ["练习函数参数", "编写三个测试"]}`。目标长度为1～200个字符，纯空白目标也会被拒绝。

AI 接口校验失败返回422，模型超时返回504，其他模型请求失败或无法生成有效建议返回502。

生成的候选仅保存在页面中，刷新后消失。用户可以编辑标题、移除候选，或点击“保存为任务”，通过 `POST /tasks` 将其写入SQLite；已保存任务在刷新页面或重启服务后仍保留。移除未保存的候选不调用任务删除接口。

保存成功后页面会刷新正式任务列表。如果保存已成功但列表刷新失败，页面会提示“任务已保存，但列表刷新失败，请刷新页面查看”，并移除已保存候选，避免用户误以为保存失败而重复提交。

### 任务查询助手

请求示例：

```json
{"goal": "我还有哪些任务没完成？"}
```

成功返回 `{"answer": "回答内容"}`，其中 `answer` 为字符串。内部使用LangChain调用只读任务查询工具，不支持通过该助手修改任务。

### 学习资料问答

请求示例：

```json
{
  "question": "Python函数没有return时返回什么？",
  "keywords": "函数 返回"
}
```

成功返回answer和sources。sources包含reference_id、source、chunk_index和text，表示本次提供给模型的参考片段，不代表每个片段都被实际引用或回答已被验证。

问题长度为1—500字符，关键词为1—200字符，纯空白输入返回422。未命中返回200、提示文本及空sources；模型超时返回504，模型请求失败或无效结果返回502，资料读取失败返回500。

资料位于项目的knowledge目录，只读取该目录直接包含的非空.md文件。当前按200字符分块，关键词用空格或中英文逗号、顿号、分号分隔（例如"函数 return"和"函数，return"效果相同），按命中的不同关键词数量排序，最多返回2个片段。

当前限制：
- 关键词需要手动输入，不支持自动中文分词或向量检索。
- 固定字符分块可能切断句子。
- 关键词命中不保证片段包含答案。
- 提示词不能保证模型不编造；引用编号与回答依据仍需人工核对。

## 数据库配置与数据说明

默认数据库为 `tasks.db`，与 `api_app.py` 同级。启动时创建缺失的数据表，已有任务会保留，正常写入的任务在服务重启后仍然存在。

使用 `TASK_DB_PATH` 切换数据库。在设置好模型配置的启动终端执行：

```powershell
$env:TASK_DB_PATH = "tasks_dev.db"
.\.venv-langchain\Scripts\python.exe -m uvicorn api_app:app --reload --host 127.0.0.1 --port 8000
```

- 相对路径以仓库根目录为基准；绝对路径直接解析使用。
- 未设置或值为空白时使用默认数据库。
- 数据库路径在应用导入时读取，修改后需要重启服务。
- 停止原服务后再运行新的启动命令，避免端口冲突；浏览器测试使用独立的临时端口。

使用手动 uvicorn 启动方式时，删除当前终端的自定义配置并重启服务，可恢复默认路径：

```powershell
Remove-Item Env:TASK_DB_PATH -ErrorAction SilentlyContinue
```

使用 `start_app.py` 时，以 `.env` 中的值为准；需要修改该文件里的 `TASK_DB_PATH` 并重启。若希望恢复默认数据库，可以将该项设为空值。

这不会删除磁盘数据库文件。根目录 `.gitignore` 会忽略所有 `.db`、`.sqlite` 和 `.sqlite3` 数据库文件及常见附属文件，避免把本地运行数据提交到Git。

数据库测试使用临时路径，pytest 可能保留近期临时目录；前端测试使用模拟响应，不读写真实任务数据库。

## 常见问题

- **页面提示“暂时无法生成有效建议”**：后端将配置缺失、空正文、截断等 ValueError 统一转换成此提示，仅凭页面文字不能确定原因。先检查配置，再查看具体异常，不要打印密钥或整个请求头。
- **检查终端环境变量是否存在**：以下命令只显示布尔值，不显示密钥。

```powershell
.\.venv-langchain\Scripts\python.exe -c "import os; names=['MODEL_API_KEY','MODEL_NAME','MODEL_BASE_URL']; print({name: bool(os.getenv(name, '').strip()) for name in names})"
```

这条命令不会读取 `.env`，只检查该 Python 进程从终端继承的环境变量。`start_app.py` 加载的配置仅作用于它自己的进程，不会回写父级 PowerShell；因此，即使以上结果为 `False`，也不能据此认定 `.env` 配置失效。使用便捷启动方式时，应检查本地配置文件及服务终端的具体错误。

- **浏览器测试提示缺少可执行文件**：执行 `playwright install chromium` 安装浏览器。
- **浏览器测试页面无法打开**：测试现在自动启动临时静态服务，请使用最新的 `test_ai_frontend.py`，并确认 `frontend` 目录及页面文件存在。
