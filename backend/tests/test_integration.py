# backend/tests/test_integration.py
import json, os, sqlite3
import pytest
from contracts import SearchQuery, SourceRef
from indexer import Indexer, init_db
from retriever import KeywordRetriever
from source import LocalSource
from search_service import SearchService
from trace_service import TraceService
from adapters.aggregate_mapper import AggregateMapper

AGGREGATE_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures/aggregate_sample.json")


@pytest.fixture
def svc():
    data = json.load(open(AGGREGATE_FIXTURE, encoding="utf-8"))
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    Indexer(conn).rebuild(AggregateMapper().to_dtos(data))
    source = LocalSource(conn)
    return SearchService(KeywordRetriever(conn), source), TraceService(source)


def test_part1_mapper_produces_valid_dtos(svc):
    """第一部分数据能转成 MessageDTO，字段齐全。"""
    s, _ = svc
    r = s.search(SearchQuery(q="幂等"))
    assert r.total >= 1
    hit = r.hits[0]
    assert hit.ref.message_id.startswith(hit.ref.session_id + "-m")
    assert hit.tool and hit.session_title


def test_part3_source_ref_json_roundtrip(svc):
    """模拟第三部分存 SourceRef JSON，能反序列化并 resolve。"""
    _, t = svc
    ref = SourceRef(projectId="P1", sessionId="S2", messageId="S2-m2",
                    charStart=0, charEnd=4, snippet="用状态机")
    stored = ref.model_dump_json(by_alias=True)          # 模拟写入 IdeaSource.source_ref
    reloaded = SourceRef.model_validate_json(stored)     # 模拟读出
    r = t.resolve(reloaded)
    assert r is not None and r.available and r.precision == "exact"
    assert r.excerpt == "用状态机"


def test_part3_message_id_only_degrades_gracefully(svc):
    """第三部分只传 message_id（无偏移），应返回整条消息 + precision=message_only。"""
    _, t = svc
    r = t.resolve(SourceRef(projectId="P1", sessionId="S2", messageId="S2-m2"))
    assert r is not None and r.precision == "message_only"
    assert r.available


def test_batch_resolve_with_context(svc):
    """批量解析 + 上下文，给第三部分列表页用。"""
    from contracts import BatchResolveRequest
    _, t = svc
    req = BatchResolveRequest(
        refs=[SourceRef(projectId="P1", sessionId="S2", messageId="S2-m2")],
        include_context=True,
    )
    out = t.resolve_batch(req)
    assert out[0]["status"] == "ok"
    assert "resolved" in out[0]
    assert "context" in out[0]