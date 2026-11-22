// 纯函数模块：把后端错误响应与表单状态转换成页面可直接渲染的数据。
// 不依赖 Vue，便于 node --test 直接单测（对齐第四模块 task-list.js 的做法）。
//
// 对应后端约定（sessionhub/README「错误返回格式」）：
//   404/409  {"detail": "字符串"}，409 另带 existing_conversation_id
//   422      {"detail": [{message_index?, field, issue, received?}, ...]} 一次报全部问题
//   message_index 为 1 起始的消息序号；非消息级问题（title 为空、body 不是 JSON）不带该字段。

const RECEIVED_LIMIT = 120

export function normalizeError(status, payload) {
  if (payload && Array.isArray(payload.detail)) {
    return {
      status,
      kind: 'issues',
      issues: payload.detail,
      existingConversationId: payload.existing_conversation_id ?? null,
    }
  }
  if (payload && typeof payload.detail === 'string') {
    return {
      status,
      kind: 'message',
      message: payload.detail,
      existingConversationId: payload.existing_conversation_id ?? null,
    }
  }
  return { status, kind: 'unknown', message: '', existingConversationId: null }
}

// received 后端已截断到 120 字符；这里兜底处理缺失/非字符串的情况。
export function formatReceived(received) {
  if (received === undefined || received === null) return ''
  const text = typeof received === 'string' ? received : JSON.stringify(received)
  if (text.length > RECEIVED_LIMIT) return text.slice(0, RECEIVED_LIMIT) + '…'
  return text
}

// 生成错误表格行。排序：请求体/请求字段等整体问题在前，消息级按序号升序、同序号按字段名。
export function issueRows(issues) {
  const rows = (issues || []).map((issue) => ({
    where: typeof issue.message_index === 'number'
      ? '第 ' + issue.message_index + ' 条消息'
      : issue.field === 'body' ? '请求体' : '请求字段',
    field: issue.field ?? '',
    issue: issue.issue ?? '',
    received: formatReceived(issue.received),
    message_index: typeof issue.message_index === 'number' ? issue.message_index : null,
  }))
  rows.sort((a, b) => {
    if (a.message_index === null && b.message_index !== null) return -1
    if (b.message_index === null && a.message_index !== null) return 1
    if (a.message_index !== b.message_index) return (a.message_index ?? 0) - (b.message_index ?? 0)
    return a.field.localeCompare(b.field)
  })
  return rows
}

// 组装导入请求体。messages 输入框支持两种粘贴方式：
//   1. 仅 messages 数组：[ {...}, ... ]  —— 字段取表单输入框的值
//   2. 完整请求体对象：{ title, source, source_conversation_id, messages }
//      —— 以对象里的字段为准（source_conversation_id 为 null 表示不查重，清空来源编号）
export function buildImportPayload({ title, source, sourceConversationId, messagesText }) {
  let parsed
  try {
    parsed = JSON.parse(messagesText)
  } catch (err) {
    return { ok: false, error: 'messages 不是合法 JSON：' + err.message }
  }
  let messages
  let bodyTitle = title
  let bodySource = source
  let bodySourceId = (sourceConversationId || '').trim()
  if (Array.isArray(parsed)) {
    messages = parsed
  } else if (parsed && typeof parsed === 'object' && Array.isArray(parsed.messages)) {
    messages = parsed.messages
    if (typeof parsed.title === 'string' && parsed.title !== '') bodyTitle = parsed.title
    if (typeof parsed.source === 'string' && parsed.source !== '') bodySource = parsed.source
    if (parsed.source_conversation_id === null) {
      bodySourceId = '' // 样例显式给 null：不参与查重，等价于留空
    } else if (
      parsed.source_conversation_id !== undefined &&
      String(parsed.source_conversation_id).trim() !== ''
    ) {
      bodySourceId = String(parsed.source_conversation_id).trim()
    }
  } else {
    return {
      ok: false,
      error: 'messages 必须是 JSON 数组，或包含 messages 数组的完整请求体对象',
    }
  }
  const payload = { title: bodyTitle, source: bodySource, messages }
  if (bodySourceId !== '') payload.source_conversation_id = bodySourceId
  return { ok: true, payload }
}

// 解析消息条数用于提示：兼容数组与完整请求体两种输入，其余返回 null。
export function countMessages(messagesText) {
  try {
    const parsed = JSON.parse(messagesText)
    if (Array.isArray(parsed)) return parsed.length
    if (parsed && typeof parsed === 'object' && Array.isArray(parsed.messages)) {
      return parsed.messages.length
    }
    return null
  } catch {
    return null
  }
}

// 从 textarea 内容反填表单字段：完整请求体时以其字段为准（null 清空），纯数组时不动表单。
// 返回 { title, source, sourceConversationId } 或 null（解析失败/纯数组）。
export function fieldsFromBody(messagesText) {
  let parsed
  try {
    parsed = JSON.parse(messagesText)
  } catch {
    return null
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
  return {
    title: typeof parsed.title === 'string' ? parsed.title : '',
    source: typeof parsed.source === 'string' ? parsed.source : '',
    sourceConversationId:
      parsed.source_conversation_id === null || parsed.source_conversation_id === undefined
        ? ''
        : String(parsed.source_conversation_id),
  }
}
