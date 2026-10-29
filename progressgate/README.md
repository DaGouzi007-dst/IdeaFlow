# ProgressGate 决策与任务跟踪

这是 IdeaFlow 的独立开发版本，提供方案决策、任务进度和阻塞处理记录。它可使用模拟数据单独运行，用于和其他模块并行开发、展示和联调。

## 目前可以做什么

- 查看模拟项目和想法，查看模拟来源消息及上下文。
- 对想法记录待讨论、已采纳或暂不采纳，以及选择理由。
- 手动创建任务，或将已采纳的想法关联到新任务。
- 记录负责人、截止日期、任务说明和完成条件。
- 更新待开始、进行中、受阻和已完成状态；记录阻塞原因、错误片段、已尝试的方法、下一步、处理结果和执行结果。
- 查看任务状态及字段变更记录，从任务返回想法，也可以从想法查看关联任务。

任务和决策使用 SQLite 保存在本机。当前项目、想法和来源消息来自仓库中的 `docs/样例/跨模块样例数据.json`，不是其他模块的正式数据。页面会明确显示演示数据标记。

## 环境

- Python 3.12。
- Node.js 24（24.12.0 或更高的 24.x 版本）及 npm。
- 首次安装依赖时需要访问 Python 和 npm 软件源。

需要完整的 IdeaFlow 仓库，以便读取模拟样例；仅复制 `progressgate` 目录无法运行演示数据接口。

## 启动后端

在仓库根目录打开终端：

```bash
cd progressgate/backend
python -m venv .venv
```

激活虚拟环境：Linux/macOS 使用 `source .venv/bin/activate`；Windows PowerShell 使用 `.venv\Scripts\Activate.ps1`。

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端接口说明：`http://127.0.0.1:8000/docs`。默认数据库位于 `progressgate/backend/progressgate.db`，已被 Git 忽略。

## 启动前端

另开一个终端，在仓库根目录执行：

```bash
cd progressgate/frontend
npm ci
npm run dev
```

浏览器打开终端显示的本地地址，默认是 `http://127.0.0.1:5173/`。Vite 将 `/api` 请求转发到本机 8000 端口，因此前后端都需要运行。结束时分别在两个终端按 `Ctrl+C`。

## 验证流程

1. 在“方案决策”中选择一条模拟想法，将状态设为“已采纳”并填写理由。
2. 在“进展跟踪”创建任务，选择刚才采纳的想法；也可以直接创建不关联想法的任务。
3. 将任务标记为受阻并填写原因；解决后记录处理结果，完成时填写执行结果。
4. 查看进展记录及字段变更；从任务进入想法，查看模拟原文，再从想法返回关联任务。
5. 刷新网页，确认决策、任务和进展仍保留。

标记为“受阻”时必须填写阻塞原因；标记为“已完成”时必须填写执行结果。关联想法创建任务之前，需要先将该想法设为已采纳。

## 测试与构建

后端的 `requirements.txt` 包含测试依赖。在已激活的后端虚拟环境中运行：

```bash
python -m pytest -q
```

在前端目录运行 `npm run build` 检查生产构建。`backend/uv.lock` 和 `frontend/package-lock.json` 保存依赖版本。

## 与其他模块的接口

- `GET /api/projects` 和 `GET /api/projects/{project_id}/ideas` 当前只返回模拟数据。
- `GET /api/demo/ideas/{idea_id}/sources` 是模拟来源接口，只用于演示查看上下文。
- `GET` / `PUT /api/ideas/{idea_id}/decision` 读取和保存当前决策。
- `GET` / `POST /api/projects/{project_id}/tasks` 查询和创建任务。
- `GET` / `PATCH /api/tasks/{task_id}` 查看和更新任务；`GET /api/tasks/{task_id}/events` 查看变更记录。

正式集成时，需要与项目和想法模块共同替换 `backend/app/demo.py` 中的模拟数据访问，并确认真实项目、想法、来源接口和数据关联。当前不包含会话导入、搜索、想法管理、账号或多用户权限，也不实现外部 Agent 的自动检测与恢复。

当前启动过程只会创建缺失的数据表，不会自动迁移已有数据库结构。正式集成前，需要共同确定数据库迁移方案。
