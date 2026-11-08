import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from contracts import SearchQuery, SourceRef
from indexer import Indexer, init_db
from retriever import KeywordRetriever
from source import LocalSource, load_from_json
from search_service import SearchService
from trace_service import TraceService

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures/sessions.json")


@pytest.fixture
def svc():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    Indexer(conn).rebuild(load_from_json(conn, FIXTURE))
    source = LocalSource(conn)
    return SearchService(KeywordRetriever(conn), source), TraceService(source)


@pytest.mark.parametrize("q,filters,expect", [
    ("JWT", {"project_id": "P1"}, {"S3-m1", "S3-m2"}),      # C2 项目筛选
    ("缓存击穿", {}, {"S1-m4"}),                             # C4 中文短语
    ("幂等", {}, {"S2-m2"}),                                 # C6 核心
    ("乐观锁和悲观锁的区别", {}, {"S2-m4"}),                 # C5 长查询
    ("blockchain", {}, set()),                               # C10 空结果
])
def test_search(svc, q, filters, expect):
    s, _ = svc
    r = s.search(SearchQuery(q=q, **filters))
    assert {h.ref.message_id for h in r.hits} == expect


def test_cross_project(svc):
    s, _ = svc
    r = s.search(SearchQuery(q="JWT"))
    assert {h.ref.message_id for h in r.hits} == {"S3-m1", "S3-m2", "S4-m1"}  # C1


def test_tool_filter_empty(svc):
    s, _ = svc
    r = s.search(SearchQuery(q="Redis", tools=["Claude"]))
    assert r.total == 0                                                         # C3


def test_highlight_ranges(svc):
    s, _ = svc
    hit = s.search(SearchQuery(q="幂等")).hits[0]
    assert hit.highlights
    for a, b in hit.highlights:
        assert hit.snippet[a:b] == "幂等"


def test_deep_link_and_resolve(svc):
    _, t = svc
    ref = SourceRef(projectId="P1", sessionId="S2", messageId="S2-m2",
                    charStart=0, charEnd=4, snippet="用状态机")
    r = t.resolve(ref)
    assert r is not None and r.available and r.excerpt == "用状态机"
    assert "/viewer/" in t.deep_link(ref) and "hl=0-4" in t.deep_link(ref)      # C7


def test_emoji_offset(svc):
    """emoji 是单个码点，长度按码点计。"""                                    # C8
    _, t = svc
    full = t.resolve(SourceRef(projectId="P1", sessionId="S1", messageId="S1-m4")).message.content
    last = len(full) - 1
    r = t.resolve(SourceRef(projectId="P1", sessionId="S1", messageId="S1-m4",
                            charStart=last, charEnd=last + 1, snippet="😀"))
    assert r.available and r.excerpt == "😀"


def test_drift_and_missing(svc):
    _, t = svc
    drift = SourceRef(projectId="P1", sessionId="S2", messageId="S2-m2",
                      charStart=0, charEnd=4, snippet="错误内容")
    missing = SourceRef(projectId="P1", sessionId="XX", messageId="XX-m1")
    res = t.validate_many([drift, missing])
    assert res["S2-m2"] == "drifted" and res["XX-m1"] == "missing"             # C9