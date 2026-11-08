# 第二部分：内容检索与来源追溯

跨 AI 会话的想法整理系统 — 检索溯源模块。

解决"记得以前讨论过某个问题，但找不到具体在哪段对话里"：在项目内检索历史会话，展示命中片段与来源，点击可跳回原文并定位到具体消息；同时为想法卡片提供出处解析服务。

## 一、模块架构（设计）

第二部分内部按"适配器 → 服务 → 端口 → 契约"单向分层，核心逻辑只依赖抽象端口，不依赖具体数据源与框架。

```
┌──────────────────────────────────────────────┐
│          入站适配器（FastAPI 路由）            │
│  /api/search   /api/trace/*   /viewer/*      │
└──────────────┬───────────────┬───────────────┘
               │               │
     ┌─────────▼───────┐ ┌─────▼───────────┐
     │  SearchService  │ │  TraceService   │
     │ 召回→片段→高亮   │ │ resolve/deepLink│
     └─────────┬───────┘ └─────┬───────────┘
               │               │
       ┌───────▼─────┐  ┌──────▼────────────┐
       │  Retriever  │  │ MessageSourcePort │
       │ (关键词实现) │  │  (LocalSource)    │
       └───────┬─────┘  └──────┬────────────┘
               │               │
       ┌───────▼───────────────▼───────────┐
       │  Indexer：jieba + FTS5 索引表      │
       │  Source ：本地业务表（可替换）      │
       └───────────────────────────────────┘
```

**模块职责**

| 模块 | 职责 |
|---|---|
| `contracts` | DTO、检索请求/响应、端口 Protocol；三部分共用的契约 |
| `indexer` | 建索引：jieba 分词写 FTS5，全量重建幂等 |
| `retriever` | 检索实现：关键词（FTS5 + bm25），`Retriever` 端口可替换 |
| `search_service` | 编排：召回 → 片段截取 → 码点高亮 → 组装 `SearchHit` |
| `trace_service` | 溯源：`resolve` / `getContext` / `validateMany` / `deepLink` |
| `source` | `MessageSourcePort` 实现，读本地 SQLite |
| `container` | 组合根：换数据源/检索器只改此处 |
| `routers` | REST 路由 + 临时查看器，只做校验与转换 |

**关键契约**

- `SourceRef`：`projectId / sessionId / messageId / charStart / charEnd / snippet`，全系统唯一追溯坐标
- `MessageDTO`：`id / sessionId / projectId / seq / role / content / createdAt / tool / contentHash`
- `SearchQuery` / `SearchHit` / `SearchResult`：检索出入口
- 端口：`MessageSourcePort` / `Retriever` / `TracePort`
- **偏移单位约定为 Unicode 码点**，前端 DOM 高亮时做 UTF-16 换算

**扩展预留**

- `Retriever` 端口 + `SearchQuery.mode`：语义/混合检索接入点
- `Indexer` 全量重建 → 增量 upsert 的替换点
- `DEEP_LINK_TEMPLATE`：落地页由临时查看器切到正式会话页的唯一常量

## 二、已实现功能（代码就位，待联调验证）

### 检索

- 关键词检索：jieba 分词 + FTS5，AND 语义，bm25 排序
- 筛选：项目 / 会话 / 来源工具 / 角色，SQL 层下推
- 结果片段：以首个命中为中心截取前后各 30 字
- 命中高亮：返回码点偏移区间，覆盖中文与 emoji
- 结果信息：片段 + 会话标题 + 来源工具 + 角色 + 时间
- 分页与耗时：`page / pageSize / total / tookMs`

### 溯源

- 单条解析 `resolve`：`SourceRef` → 原文消息与片段
- 上下文窗口 `getContext`：目标消息前后各 N 条
- 批量校验 `validateMany`：返回 `ok / missing / drifted` 三态
- 漂移检测：片段比对识别"出处内容已变更"
- 深链生成 `deepLink`：输出可跳转 URL

### 落地与接口

- REST：`/api/search`、`/api/trace/resolve`、`/api/trace/resolve-batch`、`/api/trace/context`、`/api/trace/link`
- 临时查看器：`/viewer/projects/{pid}/sessions/{sid}?msg=&hl=`，滚动到目标消息并按片段高亮
- 样例数据初始化：从 fixture JSON 一键入库建索引

## 三、待实现功能

### 对接第 1 部分（换适配器，核心逻辑不改）

- 从真实会话表读取数据（替换 `LocalSource`，改 `container.py` 一处）
- 订阅导入事件增量建索引（替换全量 `rebuild`）
- 落地页从临时查看器换成正式会话页（改 `DEEP_LINK_TEMPLATE` 一个常量）

### 对接第 3 部分

- 想法卡片保存 `SourceRef` 并调用溯源（契约已就绪）
- 出处变更主动通知（`SourceEvents` 接口预留）

### 效果与体验

- 语义检索：`Retriever` 端口 + `mode='semantic'` 已预留
- 混合排序：`mode='hybrid'` + RRF 融合
- 增量索引：`Indexer._upsert_one`
- 手工录入表单：粘贴 → 预览 → 导入
- 前端搜索页：结果卡片 UI
- 长消息精确锚定：折叠展开 + 滚到片段
- 性能压测：1 万条消息基线

## 四、运行方式

```bash
pip install -r requirements.txt

# 从样例数据初始化索引
python -m container

# 启动服务
uvicorn app:app --reload

# 单元测试
pytest tests -q
```

## 五、目录结构

```
backend/
├── contracts.py          # 契约：DTO / SearchQuery / 端口 Protocol
├── source.py             # LocalSource 实现 MessageSourcePort + JSON 初始化
├── indexer.py            # 本地表 + FTS5 索引，全量重建
├── retriever.py          # 关键词检索器（jieba + FTS5 + bm25）
├── search_service.py     # 检索编排：片段 + 码点高亮
├── trace_service.py      # 溯源：resolve / context / validateMany / deepLink
├── container.py          # 组合根
├── routers.py            # REST 路由 + 临时查看器
├── app.py                # FastAPI 实例
└── tests/
    ├── fixtures/sessions.json
    └── test_search_trace.py
```