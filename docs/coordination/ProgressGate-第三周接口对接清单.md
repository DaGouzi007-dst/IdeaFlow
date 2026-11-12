# ProgressGate 第三周接口对接清单

核对日期：2026 年 11 月 12 日。负责人：唐逸飞。依据各远程分支当前提交中的源码静态核对；本文记录第四模块接入需要处理的问题，尚未经全组确认，也不代表其他模块已经运行通过或完成联调。

## 核对依据

- 第一模块 `dev-part1`：`eeb0744`，格式说明及 `sessionhub/demo.py`。
- 第二模块 `dev-part2`：`8290a40`，`backend/contracts.py`、`routers.py`、`adapters/aggregate_mapper.py`。
- 第三模块 `dev-part3`：`392f9f7`，`backend/models.py`、`main.py`。
- 第四模块：本分支 `progressgate/backend/app/` 与功能前端。

## 当前第四模块的输入与接口

- 项目需要 `project_id`、`name`；想法需要 `idea_id`、`project_id`、`title`、`content`，可带来源消息编号。
- 当前项目、想法和来源都由 `app/demo.py` 读取共同样例。`GET /api/projects`、`GET /api/projects/{project_id}/ideas` 与 `GET /api/demo/ideas/{idea_id}/sources` 仍为演示接口。
- 决策通过 `GET/PUT /api/ideas/{idea_id}/decision` 读写；`GET /api/ideas/{idea_id}/decision/events` 读取修改历史。决策状态为 `pending/adopted/rejected`。
- 任务通过 `GET/POST /api/projects/{project_id}/tasks` 查询或创建；通过 `GET/PATCH /api/tasks/{task_id}` 查询或更新；`GET /api/tasks/{task_id}/events` 读取历史。状态为 `todo/in_progress/blocked/done`。
- 关联任务创建要求想法属于当前项目且已采纳；手动任务不需要关联想法。修改决策不会自动改变已有任务。
- 当前相关路由参数要求 UUID。任务截止日期为 `YYYY-MM-DD`，允许清空；页面按使用者本地日历判断逾期，截止日当天不算逾期，已完成任务不报逾期。

## 与第一模块对接

已提供导入格式、模拟样例与读取演示。格式约定内部项目、会话和消息编号由后端生成 UUID；当前读取演示不能直接替代持久化项目列表和会话查询 API。

待确认项目列表及查询接口、项目不存在时的错误行为，以及正式数据由哪个服务保存。第四模块接入时应使用第一模块提供的项目编号，不能另造一个同名项目代替。

## 与第三模块对接

第三模块已增加 `project_id`，11 月 2 日清单中“缺少项目归属”的描述已过时。不过当前 `POST /api/ideas` 仍默认 `project_id="demo-project"`，与第四模块 UUID 校验不同，需要共同确认正式编号；不应为演示编号直接取消项目关联校验。

当前已有 `GET /api/ideas` 和 `GET /api/ideas/{idea_id}`。列表只接收 `q`，没有项目过滤参数；响应包含 `project_id`、`summary`、`sources`。后续适配需按项目过滤，将 `summary` 映射为第四模块展示用的 `content`，并保留原有想法编号。

想法阶段“现在做／以后再说／已放弃”与第四模块的采纳决策含义不同，不能自动将“现在做”视为 `adopted`。决策仍由用户显式确认。

`IdeaSource` 已有 `message_id`、`source_ref` 和 `quote`，但第三模块源码明确标注出处读写接口尚未实现。仅有 `sources` 中的消息编号，还不足以取得完整的项目、会话和原文定位信息。需要先确认出处接口返回结构，第四模块才可替换模拟来源。

## 与第二模块对接

源码中的单条解析是 **`GET /api/trace/resolve`**，通过 `projectId/sessionId/messageId` 等查询参数调用；第二模块更新说明中的 `POST` 写法与代码不一致，联调时需由负责人确认文档。上下文和链接使用 `GET /api/trace/context` 与 `GET /api/trace/link`。

批量解析为 `POST /api/trace/resolve-batch`，请求对象含 `refs` 和 `includeContext`；`SourceRef` 包含项目、会话、消息编号，以及可选码点偏移和片段。返回的缺失、漂移和 `message_only` 降级需要在展示中区别处理，不能一律展示成精确命中。

`AggregateMapper` 当前按 `{conversation_id}-m{seq}` 重新生成消息编号，而第一模块格式约定和共同样例使用已有消息编号。两者可能无法与想法中保存的 `message_id` 对应。建议以同一真实消息编号贯穿导入、想法和溯源，若确需转换则显式保存映射；此项仍待共同确认，本分支没有修改其他成员代码。

## 接入后的验收顺序

1. 使用同一项目和消息编号导入脱敏样例，再创建带出处的想法；核对列表及详情中的项目归属一致。
2. 在第四模块采纳想法并创建关联任务，同时验证跨项目关联被拒绝、手动任务不依赖来源。
3. 将任务设为受阻，填写原因；记录处理结果后恢复，最后填写执行结果并完成，查看变更历史及刷新后的保存结果。
4. 从任务进入想法及原始消息，核对精确定位、仅消息定位和来源缺失三种展示；不以模拟来源展示代替正式联通。
5. 确认服务路由、开发端口和数据库归属后，再决定统一启动方式；目前各模块仍是独立开发成果。
