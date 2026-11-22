// 纯逻辑单测（node --test）。对齐第四模块前端的做法：只测纯 JS 模块，
// 不挂载组件。覆盖：错误归一化、错误表格排序、received 截断、请求体组装。
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildImportPayload,
  countMessages,
  fieldsFromBody,
  formatReceived,
  issueRows,
  normalizeError,
} from '../src/lib/errors.js'

test('normalizeError：422 数组 → issues，无 existing_conversation_id', () => {
  const n = normalizeError(422, {
    detail: [{ message_index: 3, field: 'role', issue: 'role 取值无效', received: 'tool' }],
  })
  assert.equal(n.kind, 'issues')
  assert.equal(n.status, 422)
  assert.equal(n.issues.length, 1)
  assert.equal(n.existingConversationId, null)
})

test('normalizeError：409 字符串 → message，并取出已有会话编号', () => {
  const n = normalizeError(409, {
    detail: '同来源会话已存在（source_conversation_id=demo-conv-001）',
    existing_conversation_id: 'abc-123',
  })
  assert.equal(n.kind, 'message')
  assert.equal(n.existingConversationId, 'abc-123')
  assert.match(n.message, /同来源会话已存在/)
})

test('normalizeError：404 字符串 → message；payload 缺失 → unknown', () => {
  const n404 = normalizeError(404, { detail: '项目不存在：x' })
  assert.equal(n404.kind, 'message')
  assert.equal(n404.message, '项目不存在：x')

  const nUnknown = normalizeError(500, null)
  assert.equal(nUnknown.kind, 'unknown')
})

test('issueRows：整体问题排前、消息级按序号升序、where 文案正确', () => {
  const rows = issueRows([
    { message_index: 3, field: 'role', issue: 'r3', received: 'tool' },
    { field: 'title', issue: 't-empty' },
    { message_index: 1, field: 'content', issue: 'c1', received: '' },
    { field: 'body', issue: 'not-json' },
    { message_index: 1, field: 'role', issue: 'r1', received: 'x' },
  ])
  assert.deepEqual(
    rows.map((r) => [r.where, r.field]),
    [
      ['请求体', 'body'],
      ['请求字段', 'title'],
      ['第 1 条消息', 'content'],
      ['第 1 条消息', 'role'],
      ['第 3 条消息', 'role'],
    ]
  )
})

test('formatReceived：字符串原样、缺失为空、对象转 JSON 且超长截断', () => {
  assert.equal(formatReceived('tool'), 'tool')
  assert.equal(formatReceived(undefined), '')
  assert.equal(formatReceived(null), '')
  assert.equal(formatReceived({ a: 1 }), '{"a":1}')
  const long = 'x'.repeat(130)
  const out = formatReceived(long)
  assert.equal(out.length, 121) // 120 + 省略号
  assert.ok(out.endsWith('…'))
})

test('buildImportPayload：正常组装；来源编号留空则不带该字段', () => {
  const built = buildImportPayload({
    title: 't',
    source: 'synthetic',
    sourceConversationId: '  ',
    messagesText: '[{"role":"user","content":"hi","created_at":null}]',
  })
  assert.equal(built.ok, true)
  assert.deepEqual(built.payload, {
    title: 't',
    source: 'synthetic',
    messages: [{ role: 'user', content: 'hi', created_at: null }],
  })

  const withSource = buildImportPayload({
    title: 't',
    source: 'synthetic',
    sourceConversationId: ' demo-conv-001 ',
    messagesText: '[]',
  })
  assert.equal(withSource.ok, true)
  assert.equal(withSource.payload.source_conversation_id, 'demo-conv-001')
})

test('buildImportPayload：messages 不是 JSON / 不是数组时报错且不发请求', () => {
  const badJson = buildImportPayload({ title: 't', source: 's', sourceConversationId: '', messagesText: '[{' })
  assert.equal(badJson.ok, false)
  assert.match(badJson.error, /不是合法 JSON/)

  const notArray = buildImportPayload({ title: 't', source: 's', sourceConversationId: '', messagesText: '{"a":1}' })
  assert.equal(notArray.ok, false)
  assert.match(notArray.error, /JSON 数组/)
})

test('countMessages：数组给条数，完整请求体取 messages 长度，其余给 null', () => {
  assert.equal(countMessages('[1,2,3]'), 3)
  assert.equal(countMessages('[]'), 0)
  assert.equal(
    countMessages('{"title":"t","source":"s","source_conversation_id":null,"messages":[{},{},{}]}'),
    3
  )
  assert.equal(countMessages('{"a":1}'), null)
  assert.equal(countMessages('broken'), null)
})

test('buildImportPayload：完整请求体对象 → 以对象字段为准，null 来源编号不参与查重', () => {
  const body = {
    title: '样例标题',
    source: 'synthetic',
    source_conversation_id: null,
    messages: [{ role: 'user', content: 'hi', created_at: null }],
  }
  const built = buildImportPayload({
    title: '表单标题',
    source: 'manual',
    sourceConversationId: 'form-id',
    messagesText: JSON.stringify(body),
  })
  assert.equal(built.ok, true)
  assert.deepEqual(built.payload, {
    title: '样例标题',
    source: 'synthetic',
    messages: body.messages,
  })
  assert.equal('source_conversation_id' in built.payload, false)

  const body2 = { ...body, source_conversation_id: 'demo-conv-001' }
  const built2 = buildImportPayload({
    title: '表单标题',
    source: 'manual',
    sourceConversationId: '',
    messagesText: JSON.stringify(body2),
  })
  assert.equal(built2.ok, true)
  assert.equal(built2.payload.source_conversation_id, 'demo-conv-001')
})

test('fieldsFromBody：完整请求体反填字段，null 清空来源编号；纯数组返回 null', () => {
  const f1 = fieldsFromBody('{"title":"t","source":"s","source_conversation_id":null,"messages":[]}')
  assert.deepEqual(f1, { title: 't', source: 's', sourceConversationId: '' })

  const f2 = fieldsFromBody('{"title":"t","source":"s","source_conversation_id":"c-1","messages":[]}')
  assert.equal(f2.sourceConversationId, 'c-1')

  assert.equal(fieldsFromBody('[{"role":"user"}]'), null)
  assert.equal(fieldsFromBody('broken'), null)
})
