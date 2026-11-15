"""检索编排：召回 → 片段截取 → 码点高亮 → 组装 SearchHit → 分页。"""
import time
import jieba
from contracts import SearchQuery, SearchHit, SearchResult, SourceRef

WINDOW = 30  # 命中词前后各取 30 字


def _positions(text: str, word: str) -> list[tuple[int, int]]:
    out, i = [], text.find(word)
    while i != -1:
        out.append((i, i + len(word)))
        i = text.find(word, i + 1)
    return out

def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """合并相邻或重叠的区间，避免分词切碎导致高亮断裂。"""
    if not ranges:
        return []
    sorted_ranges = sorted(set(ranges))
    merged = [list(sorted_ranges[0])]
    for start, end in sorted_ranges[1:]:
        if start <= merged[-1][1]:          # 相邻或重叠
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(r) for r in merged]

def build_snippet(content: str, words: list[str], phrase: str = "") -> tuple[str, list[tuple[int, int]], int]:
    """以首个命中为中心截 ±WINDOW 字。整串能匹配则只高亮整串，否则退化为逐词高亮。"""
    # ① 短语优先：整个查询串在原文能连续找到，就只标这一处
    if phrase:
        pos = _positions(content, phrase)
        if pos:
            s, e = pos[0]
            start = max(0, s - WINDOW)
            end = min(len(content), e + WINDOW)
            return content[start:end], [(s - start, e - start)], start

    # ② 原有逻辑：逐词找位置
    first = None
    for w in words:
        p = _positions(content, w)
        if p:
            first = p[0][0] if first is None else min(first, p[0][0])
    if first is None:
        return content[: WINDOW * 2], [], 0
    start = max(0, first - WINDOW)
    end = min(len(content), first + WINDOW)
    snippet = content[start:end]
    rel = sorted({(s - start, e - start)
                  for w in words for s, e in _positions(snippet, w)})
    return snippet, _merge_ranges(rel), start

class SearchService:
    def __init__(self, retriever, source):
        self.retriever = retriever
        self.source = source

    def search(self, q: SearchQuery) -> SearchResult:
        t0 = time.perf_counter()
        if not q.q.strip():
            return SearchResult(hits=[], total=0, page=q.page, took_ms=0)
        words = [w for w in jieba.lcut(q.q) if w.strip()]
        limit = q.page * q.page_size * 3
        cands = self.retriever.search(q, limit, op="AND")

        relaxed = False
        if not cands and len(words) > 1:
            cands = self.retriever.search(q, limit, op="OR")   # ← 原查询 + OR 语义
            relaxed = True

        hits: list[SearchHit] = []
        for mid, score in cands:
            msg = self.source.get_message(mid)
            if not msg:
                continue
            snippet, hl, start = build_snippet(msg.content, words, phrase=q.q.strip())
            hits.append(SearchHit(
                ref=SourceRef(
                    project_id=msg.project_id, session_id=msg.session_id,
                    message_id=msg.id,
                    char_start=start, char_end=start + len(snippet),
                    snippet=snippet,
                ),
                session_title=msg.session_title, tool=msg.tool,
                role=msg.role, created_at=msg.created_at,
                snippet=snippet, highlights=hl, score=score,
                matched_by="keyword",
            ))
        s = (q.page - 1) * q.page_size
        return SearchResult(
            hits=hits[s: s + q.page_size], total=len(hits),
            page=q.page, took_ms=int((time.perf_counter() - t0) * 1000), relaxed=relaxed
        )