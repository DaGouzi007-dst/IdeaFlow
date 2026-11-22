# sessionhub —— 会话导入与管理（第一模块）

负责人：王语晨
模块职责：项目、会话、消息的创建和查看；解析本组规定的 JSON 导入格式；保存来源信息及原始消息。

## 当前状态

- [x] 《会话导入格式说明》：`docs/requirements/会话导入与管理-格式说明.md`（v1.1，已随接口实现修订）
- [x] 导入格式样例：`docs/样例/会话导入样例.json`
- [x] 会话读取演示脚本：`demo.py`（纯 Python 标准库，无需安装依赖，第一周交付）
- [x] **FastAPI 接口化**（2026-11-14）：`backend/`，项目创建/列表/详情、导入、会话查看五个接口
- [x] **重复导入处理与错误返回细化**（2026-11-14）：同来源 409 + `?overwrite=true` 覆盖导入；422 结构化错误明细
- [x] **导入页面 UI**（2026-11-22）：`frontend/`，Vue 3 + Vite（与第四模块同栈），项目创建/选择、导入表单（内置样例）、422 结构化错误表、409 覆盖导入（含确认弹窗）、会话查看（seq / message_id 一键复制）
- [ ] 会话列表查询接口与页面（当前后端只有单会话查看，列表页待接口补充后做）
- [ ] 跨工具自动去重（立项报告完整规则）——按约定第 2 至 3 周后评估，当前不做、不声称支持

## 快速开始（后端接口）

    cd sessionhub/backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8001

启动后访问 http://127.0.0.1:8001/docs 查看自动生成的接口说明（FastAPI 自带）。
端口用 8001 是为了避开第四模块 progressgate 默认占用的 8000（见组长《第三周接口对接清单》）。

运行测试（20 个用例，全部离线，不依赖其他模块）：

    cd sessionhub/backend
    python -m pytest tests/ -v

## 快速开始（前端页面）

前置：Node.js ≥ 20.19（Vite 7 的要求，建议直接装官网 LTS 版）。检查：`node -v`。

    cd sessionhub/frontend
    npm install        # 首次运行安装依赖；网络慢可先 npm config set registry https://registry.npmmirror.com
    npm run dev        # 开发服务器，固定 http://127.0.0.1:5171

浏览器打开 http://127.0.0.1:5171 。`/api` 请求由 Vite 代理到 8001，所以要先按上文把后端跑起来（两个终端分别跑后端和前端）。
5171 是特意避开第四模块前端默认的 5173，两个模块可以同时开着开发。

页面功能（对应后端五个接口）：

- 项目区：创建项目（`POST /api/projects`）、项目列表选择（`GET /api/projects`），显示当前 `project_id` 可复制。
- 导入表单：title / source / source_conversation_id 三个字段 + messages 编辑区；支持两种粘贴——完整请求体对象（以其中字段为准）或仅 messages 数组（用表单字段组装）；内置「仓库样例」和「409 演示样例」按钮。
- 导入结果：成功面板给 `conversation_id`、`message_ids`（seq 序号 + 一键复制，可直接给第二模块对齐用）；422 按表格一次报出全部问题（第几条消息、字段、原因、收到值）；409 附 `existing_conversation_id` 并提供「覆盖导入」（前端确认弹窗 → 重发 `?overwrite=true`）；404/网络错误各有明确提示。
- 会话查看：`GET /api/conversations/{id}`，按 seq 展示消息、role 徽章、created_at（null 显示"原始记录没有时间"）、message_id 复制。

前端测试（10 个纯逻辑用例，node 自带测试器，无需额外依赖）：

    cd sessionhub/frontend
    npm test

生产构建（产物 `dist/` 不进 Git，`frontend/.gitignore` 已挡）：

    npm run build

需要把页面指到别的后端地址（例如联调时后端跑在别的机器）：

    VITE_API_BASE=http://192.168.x.x:8001 npm run dev

## 接口一览

| 方法与路径 | 作用 | 成功 | 主要错误 |
|---|---|---|---|
| `POST /api/projects` | 创建项目（请求体 `{"name": "..."}`） | `201` 返回 `project_id` | `422` name 为空/类型错 |
| `GET /api/projects` | 项目列表（对接清单"待确认项目列表"项） | `200` | — |
| `GET /api/projects/{project_id}` | 项目详情 | `200` | `404` 项目不存在 |
| `POST /api/projects/{project_id}/conversations/import` | 导入本组约定 JSON 格式会话 | `201` 返回 `conversation_id`、`message_ids` | `404` 项目不存在；`422` 格式错误；`409` 同来源重复 |
| `GET /api/conversations/{conversation_id}` | 查看会话与消息（按导入顺序，带 `seq`） | `200` | `404` 会话不存在 |

导入成功响应示例：

    {
      "project_id": "c9cbe8fb-...",
      "conversation_id": "5d7d8318-...",
      "message_ids": ["2274f7f4-...", "..."],
      "imported_count": 7,
      "overwritten": false
    }

## 错误返回格式（细化后的约定）

`detail` 为字符串（404/409）或结构化数组（422），数组元素定位到"第几条消息的哪个字段"：

    // 404
    {"detail": "项目不存在：00000000-..."}
    // 409（附已有会话编号，供确认或覆盖）
    {"detail": "同来源会话已存在（source_conversation_id=demo-conv-001），如需替换请加 ?overwrite=true",
     "existing_conversation_id": "d039911a-..."}
    // 422（message_index 为 1 起始的消息序号）
    {"detail": [{"message_index": 3, "field": "role", "issue": "role 取值无效（允许：user、assistant、system）", "received": "tool"}]}

前端拿到 422 后可直接渲染"第 N 条消息、字段、原因、原值"，改完一次重传即可（导入页面已按此实现）。

## 重复导入处理（本期实现，待小组确认固化）

- 同一项目下 `source_conversation_id` 相同 → `409` 并附已有会话编号（格式说明第 4 节规则 6）。
- `?overwrite=true` → 原子替换：旧会话连同消息一起删除、新会话写入，同一个事务内完成，不产生半份残留。
- `source_conversation_id` 为 `null` 的会话不参与查重（无来源编号可比对），可多次导入。
- 以上是**同来源**重复处理；跨工具自动去重仍按约定不在本版声称支持。

## 数据持久化与编号

- SQLite 数据库文件 `backend/sessionhub.db`，由后端统一读写；运行产生的数据库不进 Git（`.gitignore` 已含 `*.db`）。可用环境变量 `SESSIONHUB_DB` 换路径（测试即用此机制）。
- `project_id`、`conversation_id`、`message_id` 均由后端生成 UUID 字符串，全链路沿用同一编号——检索与溯源模块引用消息时直接使用导入响应里的 `message_ids`，无需自行重编。
- `GET /api/conversations/{id}` 的 messages 每条带 `seq`（1 起始，按导入顺序），供第二模块契约中的 `seq` 字段使用；消息内容原样保存、不做任何改写。

## 运行演示（第一周交付，仍然可用）

    cd sessionhub
    python demo.py

    # 校验任意一个符合导入格式的 JSON 文件：
    python demo.py --file 路径/xxx.json

脚本会依次：
1. 读取组内聚合样例（`docs/样例/跨模块样例数据.json`），展示项目、会话标题、消息角色和内容；
2. 对导入格式样例（`docs/样例/会话导入样例.json`）逐项执行格式检查，然后展示消息内容。

样例文件优先从仓库 `docs/样例/` 读取；如果该目录还没有文件，会使用本目录 `samples/` 中的副本。正式样例以 `docs/样例/` 为准。

## 目录说明

    demo.py                        会话读取演示（第一周交付，保留）
    samples/                       演示用样例副本（正式样例以 docs/样例/ 为准）
    backend/
      requirements.txt             依赖：fastapi、uvicorn、pytest、httpx
      app/main.py                  FastAPI 应用与五个接口
      app/models.py                请求体模型（pydantic）
      app/validation.py            六条校验规则的语义实现（结构化错误明细）
      app/db.py                    SQLite 存储层（建表、连接、路径配置）
      tests/test_sessionhub.py     20 个接口测试用例
    frontend/                      Vue 3 + Vite 导入页面（第三阶段交付）
      package.json                 vue 3.5 + vite 7（版本与第四模块一致）
      vite.config.js               /api 代理到 8001；dev 固定 5171 避开第四模块 5173
      src/App.vue                  页面骨架与状态编排（项目/导入/结果/查看四区）
      src/api.js                   后端访问封装（支持 VITE_API_BASE 覆盖目标地址）
      src/lib/errors.js            错误归一化、错误表排序、请求体组装（纯函数，被单测覆盖）
      src/sample.js                内置样例：仓库样例原文 + 409 演示变体
      src/components/              ProjectBar / ImportForm / ResultPanel / ConversationViewer
      tests/errors.test.js         10 个纯逻辑单测（node --test）

后端目录结构对齐第四模块 `progressgate/backend/`（app 包 + tests 目录 + requirements.txt）；前端技术栈与 `progressgate/frontend/` 一致（Vue 3 + Vite + node --test），便于后续拼入统一入口。

## 对齐说明

- 字段与接口遵循 `docs/开工方案与接口约定-讨论稿.md` 及组内《公共数据约定》。
- 消息 `role` 只使用 `user`、`assistant`、`system`；`created_at` 可为 `null`，消息顺序由导入顺序保证。
- 接口验证记录见 `docs/testing/会话导入-接口化验证记录.md`（自动化测试 + 真实服务实测）。
- 导入页面验证记录见 `docs/testing/会话导入-导入页面验证记录.md`（前端单测 + 浏览器全流程实测 + 截图）。
- 文件夹名 `sessionhub` 为暂定名，待小组确认；如组会决定并入统一目录，`backend/` 内文件可整体平移，`frontend/` 可作为页面模块接入统一入口。
