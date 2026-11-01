# 模块3 后端

全部代码在 [main.py](main.py) 一个文件里：一张表 `idea`、四个接口、启动时自动灌 5 条模拟数据。

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

http://127.0.0.1:8000/docs 

## 四个接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/ideas?q=关键词` | 列表，按收藏 + 更新时间排序 |
| POST | `/api/ideas` | 新建，返回 201 |
| PATCH | `/api/ideas/{idea_id}` | 修改，只改传上来的字段 |
| DELETE | `/api/ideas/{idea_id}` | 删除，返回 204 |

## 想法卡片的字段

| 字段 | 意思 |
|---|---|
| `title` | 标题 |
| `summary` | 一句话说明 |
| `tags` | 标签，逗号分隔 |
| `premise` | **适用条件**：这条建议在什么前提下才成立 |
| `stage` | 现在做 / 以后再说 / 已放弃 |
| `favorite` | 收藏 |
| `sources` | 来源消息编号，逗号分隔 |
| `updated_at` | 最后修改时间 |


