"""入站适配器：REST + 临时查看器。只做校验和 DTO 转换，无业务逻辑。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from contracts import (
    SearchQuery, SearchResult, SourceRef,
    ResolvedSource, ContextWindow,
)
from container import get_search_service, get_trace_service, get_source
# routers.py 修改 /api/trace/resolve-batch

from contracts import BatchResolveRequest   # ← 新增 import


router = APIRouter()


@router.post("/api/search", response_model=SearchResult)
def search(q: SearchQuery, svc=Depends(get_search_service)):
    return svc.search(q)


@router.get("/api/trace/resolve", response_model=ResolvedSource | None)
def resolve(projectId: str, sessionId: str, messageId: str,
            charStart: int | None = None, charEnd: int | None = None,
            snippet: str | None = None,
            svc=Depends(get_trace_service)):
    ref = SourceRef(projectId=projectId, sessionId=sessionId, messageId=messageId,
                    charStart=charStart, charEnd=charEnd, snippet=snippet)
    return svc.resolve(ref)


@router.post("/api/trace/resolve-batch")
def resolve_batch(req: BatchResolveRequest, svc=Depends(get_trace_service)):
    return svc.resolve_batch(req)


@router.get("/api/trace/context", response_model=ContextWindow | None)
def context(projectId: str, sessionId: str, messageId: str,
            before: int = 2, after: int = 2,
            svc=Depends(get_trace_service)):
    ref = SourceRef(projectId=projectId, sessionId=sessionId, messageId=messageId)
    return svc.get_context(ref, before, after)


@router.get("/api/trace/link")
def link(projectId: str, sessionId: str, messageId: str,
         charStart: int | None = None, charEnd: int | None = None,
         svc=Depends(get_trace_service)):
    return {"link": svc.deep_link(SourceRef(
        projectId=projectId, sessionId=sessionId, messageId=messageId,
        charStart=charStart, charEnd=charEnd))}


@router.get("/api/viewer/session/{session_id}")
def viewer_data(session_id: str):
    msgs = [m for m in get_source().list_all_messages() if m.session_id == session_id]
    if not msgs:
        raise HTTPException(404, "会话不存在")
    return {
        "sessionId": session_id, "sessionTitle": msgs[0].session_title,
        "projectId": msgs[0].project_id, "tool": msgs[0].tool,
        "messages": [m.model_dump(by_alias=True) for m in msgs],
    }


VIEWER_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>会话查看器</title>
<style>
 body{font-family:system-ui;max-width:900px;margin:20px auto;padding:20px;line-height:1.6}
 .msg{border-left:3px solid #ccc;padding:10px 14px;margin:12px 0;background:#fafafa}
 .msg.user{border-color:#4a90e2;background:#f0f7ff}
 .msg.assistant{border-color:#6cbf6c;background:#f4fbf4}
 .msg.focused{box-shadow:0 0 0 3px #ffd700;animation:fade 1.5s ease}
 @keyframes fade{0%{background:#fff8b0}100%{background:inherit}}
 .role{font-size:12px;color:#888;text-transform:uppercase;margin-bottom:4px}
 mark{background:#fff8b0;padding:2px}
 .meta{color:#666;font-size:14px;margin-bottom:20px}
</style></head><body>
<h2 id="title">加载中...</h2>
<div id="meta" class="meta"></div>
<div id="messages"></div>
<script>
const p = new URLSearchParams(location.search);
const targetMsg = p.get('msg');
const hl = p.get('hl');
const sid = location.pathname.split('/')[5];
const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function cpSlice(str, start, end) {
  // 码点切片（后端偏移是码点，前端 DOM 是 UTF-16；此处用 Array.from 做码点切）
  const cps = Array.from(str);
  return {pre: cps.slice(0, start).join(''),
          hit: cps.slice(start, end).join(''),
          post: cps.slice(end).join('')};
}
fetch('/api/viewer/session/' + sid).then(r => r.json()).then(data => {
  document.getElementById('title').textContent = data.sessionTitle;
  document.getElementById('meta').textContent =
    '项目 ' + data.projectId + ' · 来源 ' + data.tool;
  const container = document.getElementById('messages');
  data.messages.forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg ' + m.role;
    div.id = 'msg-' + m.id;
    let html;
    if (m.id === targetMsg && hl) {
      const [s, e] = hl.split('-').map(Number);
      const {pre, hit, post} = cpSlice(m.content, s, e);
      html = esc(pre) + '<mark>' + esc(hit) + '</mark>' + esc(post);
    } else {
      html = esc(m.content);
    }
    div.innerHTML = '<div class="role">' + esc(m.role) + '</div><div>' + html + '</div>';
    container.appendChild(div);
  });
  const target = document.getElementById('msg-' + targetMsg);
  if (target) {
    target.classList.add('focused');
    target.scrollIntoView({behavior:'smooth', block:'center'});
  }
});
</script></body></html>"""


@router.get("/viewer/projects/{pid}/sessions/{sid}", response_class=HTMLResponse)
def viewer_page(pid: str, sid: str):
    return VIEWER_HTML