---
AIGC: {"Label":"1","ContentProducer":"001191110108MA01KP2T5U00000","ProduceID":"5bf71972-2e10-47e9-9f74-1d34f77c6166","ReservedCode1":"","ContentPropagator":"001191110108MA01KP2T5U00000","PropagateID":"5bf71972-2e10-47e9-9f74-1d34f77c6166","ReservedCode2":""}
---

# sessionhub —— 会话导入与管理（第一模块）

负责人：王语晨
模块职责：项目、会话、消息的创建和查看；解析本组规定的 JSON 导入格式；保存来源信息及原始消息。

## 当前状态（第一周交付）

- [x] 《会话导入格式说明》：`docs/requirements/会话导入与管理-格式说明.md`
- [x] 导入格式样例：`docs/样例/会话导入样例.json`
- [x] 会话读取演示脚本：`demo.py`（纯 Python 标准库，无需安装依赖）
- [ ] FastAPI 接口化（`POST /api/projects`、导入接口、会话查看接口）——第 2 至 3 周
- [ ] 重复导入处理、格式检查错误返回细化——第 2 至 3 周
- [ ] 前端页面（项目列表、会话列表、导入页、会话查看）

## 运行演示

    cd sessionhub
    python demo.py

    # 校验任意一个符合导入格式的 JSON 文件：
    python demo.py --file 路径/xxx.json

脚本会依次：
1. 读取组内聚合样例（`docs/样例/跨模块样例数据.json`），展示项目、会话标题、消息角色和内容；
2. 对导入格式样例（`docs/样例/会话导入样例.json`）逐项执行格式检查，然后展示消息内容。

样例文件优先从仓库 `docs/样例/` 读取；如果该目录还没有文件，会使用本目录 `samples/` 中的副本。正式样例以 `docs/样例/` 为准。

## 目录说明

    demo.py                  会话读取演示（第一周交付）
    samples/                 演示用样例副本（正式样例以 docs/样例/ 为准）
    backend/                 （计划）FastAPI 后端，结构对齐 progressgate/backend
    frontend/                （计划）Vue 3 页面

## 对齐说明

- 字段与接口遵循 `docs/开工方案与接口约定-讨论稿.md` 及组内《公共数据约定》。
- 消息 `role` 只使用 `user`、`assistant`、`system`；`created_at` 可为 `null`，消息顺序由导入顺序保证。
- 文件夹名 `sessionhub` 为暂定名，待小组确认。

---
*智谱AI生成*
