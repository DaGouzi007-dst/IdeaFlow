"""组合根：唯一装配点。换数据源 / 换检索器只改此文件。"""
import sqlite3
from indexer import Indexer, init_db
from retriever import KeywordRetriever
from source import LocalSource, load_from_json
from search_service import SearchService
from trace_service import TraceService

_conn = sqlite3.connect("search.db", check_same_thread=False)
init_db(_conn)
_source = LocalSource(_conn)
_search = SearchService(KeywordRetriever(_conn), _source)
_trace = TraceService(_source)


def get_db() -> sqlite3.Connection:
    return _conn

def get_source() -> LocalSource:
    return _source

def get_search_service() -> SearchService:
    return _search

def get_trace_service() -> TraceService:
    return _trace

def init_from_json(path: str) -> int:
    return Indexer(_conn).rebuild(load_from_json(_conn, path))


if __name__ == "__main__":
    n = init_from_json("tests/fixtures/sessions.json")
    print(f"已入库并重建索引：{n} 条消息")

# container.py 末尾新增

def init_from_aggregate(path: str) -> int:
    """从第一部分聚合样例（projects/conversations/messages）初始化。"""
    import json
    from adapters.aggregate_mapper import AggregateMapper
    data = json.load(open(path, encoding="utf-8"))
    return Indexer(_conn).rebuild(AggregateMapper().to_dtos(data))


def init_from_part1_db(db_path: str, project_id: str | None = None) -> int:
    """直读第一模块 sessionhub.db 并重建索引（临时方案，待其提供列表接口后改 HTTP）。"""
    from adapters.part1_source import load_from_part1_db
    return Indexer(_conn).rebuild(load_from_part1_db(db_path, project_id))


def init_from_plugin_exports(paths: list[str], project_id: str = "imported") -> int:
    """从 AI-Chat-Toolkit 导出的多个 JSON 初始化索引（测试用）。"""
    import json
    from adapters.plugin_export_mapper import to_dtos
    dtos = []
    for p in paths:
        dtos.extend(to_dtos(json.load(open(p, encoding="utf-8")), project_id))
    return Indexer(_conn).rebuild(dtos)
