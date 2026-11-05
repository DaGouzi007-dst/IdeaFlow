const call = async (path, method = 'GET', body) => {
  const res = await fetch('/api' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error((await res.json()).detail || '出错了')
  return res.status === 204 ? null : res.json()
}

export const api = {
  list: (q) => call('/ideas' + (q ? '?q=' + encodeURIComponent(q) : '')),
  get: (id) => call('/ideas/' + id),
  create: (data) => call('/ideas', 'POST', data),
  update: (id, data) => call('/ideas/' + id, 'PATCH', data),
  remove: (id) => call('/ideas/' + id, 'DELETE'),
}
