const call = async (path, method = 'GET', body) => {
  const res = await fetch('/api' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail = data.detail
    const err = new Error(
      typeof detail === 'string' ? detail : (detail && detail.message) || `请求失败（${res.status}）`,
    )
    err.status = res.status
    err.data = detail
    throw err
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  list: (q) => call('/ideas' + (q ? '?q=' + encodeURIComponent(q) : '')),
  get: (id) => call('/ideas/' + id),
  create: (data) => call('/ideas', 'POST', data),
  fromSource: (data) => call('/ideas/from-source', 'POST', data),
  update: (id, data) => call('/ideas/' + id, 'PATCH', data),
  remove: (id) => call('/ideas/' + id, 'DELETE'),

  sources: (id) => call(`/ideas/${id}/sources`),
  similar: (id, limit = 3) => call(`/ideas/${id}/similar?limit=${limit}`),
  addSource: (id, data) => call(`/ideas/${id}/sources`, 'POST', data),
  removeSource: (id, messageId) => call(`/ideas/${id}/sources/${messageId}`, 'DELETE'),

  // 跳转地址由后端统一生成
  sourceLink: (ref) => {
    const q = new URLSearchParams({ ...ref }).toString()
    return call('/source-link?' + q)
  },

  relations: (id) => call(`/ideas/${id}/relations`),
  pending: () => call('/relations?status=' + encodeURIComponent('待确认')),
  relate: (data) => call('/relations', 'POST', data),
  setRelation: (id, status) => call('/relations/' + id, 'PATCH', { status }),
}
