// 后端访问封装。默认走同源 /api（开发时由 Vite 代理到 127.0.0.1:8001）。
// 需要指向其他地址时（例如联调时指向别的机器），用环境变量 VITE_API_BASE 覆盖：
//   VITE_API_BASE=http://192.168.x.x:8001 npm run dev
const BASE = import.meta.env.VITE_API_BASE || ''

export function apiBaseLabel() {
  return BASE || '同源 /api（Vite 代理 → 127.0.0.1:8001）'
}

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(BASE + path, options)
  } catch {
    const error = new Error(
      '无法连接后端服务。请先在 sessionhub/backend 目录运行：uvicorn app.main:app --port 8001'
    )
    error.kind = 'network'
    throw error
  }
  const text = await res.text()
  let payload = null
  try {
    payload = text ? JSON.parse(text) : null
  } catch {
    payload = null
  }
  if (!res.ok) {
    const error = new Error('请求失败（HTTP ' + res.status + '）')
    error.status = res.status
    error.payload = payload
    throw error
  }
  return payload
}

export function listProjects() {
  return request('/api/projects')
}

export function createProject(name) {
  return request('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function importConversation(projectId, payload, overwrite = false) {
  const query = overwrite ? '?overwrite=true' : ''
  return request(
    '/api/projects/' + encodeURIComponent(projectId) + '/conversations/import' + query,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
}

export function getConversation(conversationId) {
  return request('/api/conversations/' + encodeURIComponent(conversationId))
}
