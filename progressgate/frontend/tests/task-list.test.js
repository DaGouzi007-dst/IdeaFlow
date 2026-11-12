import assert from 'node:assert/strict'
import test from 'node:test'
import { deadlineState, localDateKey, selectTasks } from '../src/task-list.js'

const today = '2026-11-12'
const task = (id, status, due_date, assignee = '') => ({
  task_id: id, title: `任务 ${id}`, status, due_date, assignee, created_at: '2026-11-10T10:00:00Z',
})
const tasks = [
  task('1', 'todo', '2026-11-11', '唐逸飞'),
  task('2', 'in_progress', today, '唐逸飞'),
  task('3', 'blocked', '2026-11-13'),
  task('4', 'done', '2026-11-01'),
  task('5', 'todo', null),
  task('6', 'done', today),
]

test('截止日当天不算逾期，已完成和无截止日期的任务不报逾期', () => {
  assert.equal(deadlineState(tasks[0], today), 'overdue')
  assert.equal(deadlineState(tasks[1], today), 'today')
  assert.equal(deadlineState(tasks[2], today), 'upcoming')
  assert.equal(deadlineState(tasks[3], today), 'done')
  assert.equal(deadlineState(tasks[4], today), 'undated')
  assert.deepEqual(selectTasks(tasks, { deadline: 'overdue', today }).map(t => t.task_id), ['1'])
  assert.deepEqual(selectTasks(tasks, { deadline: 'today', today }).map(t => t.task_id), ['2'])
  assert.equal(deadlineState(tasks[1], '2026-11-13'), 'overdue')
})

test('状态、截止日期和标题或负责人检索可以组合使用', () => {
  assert.deepEqual(selectTasks(tasks, { status: 'todo', deadline: 'overdue', search: ' 唐逸飞 ', today }).map(t => t.task_id), ['1'])
  assert.deepEqual(selectTasks(tasks, { status: 'todo', deadline: 'undated', today }).map(t => t.task_id), ['5'])
  assert.deepEqual(selectTasks(tasks, { search: '任务 3', today }).map(t => t.task_id), ['3'])
  assert.deepEqual(selectTasks(tasks, { status: 'blocked', deadline: 'today', today }), [])
})

test('按截止日期升序排列，无日期的放最后且不改写原始列表', () => {
  const original = tasks.map(t => t.task_id)
  assert.deepEqual(selectTasks(tasks, { sort: 'due_date', today }).map(t => t.task_id), ['4', '1', '2', '6', '3', '5'])
  assert.deepEqual(tasks.map(t => t.task_id), original)
  const newer = { ...tasks[4], task_id: '7', created_at: '2026-11-12T10:00:00Z' }
  assert.deepEqual(selectTasks([...tasks, newer], { today }).map(t => t.task_id), ['7', ...original])
  const sameDeadline = { ...newer, due_date: today }
  assert.deepEqual(selectTasks([...tasks, sameDeadline], { sort: 'due_date', today }).map(t => t.task_id), ['4', '1', '7', '2', '6', '3', '5'])
})

test('本地日期使用本地日历，跨 UTC 日界线不会提前或推迟一天', () => {
  const previous = process.env.TZ
  try {
    process.env.TZ = 'Asia/Shanghai'
    assert.equal(localDateKey(new Date('2026-11-11T16:30:00Z')), today)
    process.env.TZ = 'America/Los_Angeles'
    assert.equal(localDateKey(new Date('2026-11-12T01:30:00Z')), '2026-11-11')
  } finally {
    if (previous === undefined) delete process.env.TZ
    else process.env.TZ = previous
  }
})
