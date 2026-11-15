const call = async (path, method = 'GET', body) => {
  const res = await fetch('/api' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : `请求失败（${res.status}）`)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  list: (q) => call('/ideas' + (q ? '?q=' + encodeURIComponent(q) : '')),
  get: (id) => call('/ideas/' + id),
  create: (data) => call('/ideas', 'POST', data),
  update: (id, data) => call('/ideas/' + id, 'PATCH', data),
  remove: (id) => call('/ideas/' + id, 'DELETE'),

  sources: (id) => call(`/ideas/${id}/sources`),
  addSource: (id, data) => call(`/ideas/${id}/sources`, 'POST', data),
  removeSource: (id, messageId) => call(`/ideas/${id}/sources/${messageId}`, 'DELETE'),

  relations: (id) => call(`/ideas/${id}/relations`),
  relate: (data) => call('/relations', 'POST', data),
  setRelation: (id, status) => call('/relations/' + id, 'PATCH', { status }),
}
