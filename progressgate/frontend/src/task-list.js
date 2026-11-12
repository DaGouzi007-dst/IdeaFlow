// Date-only deadlines follow the user's local calendar, rather than UTC midnight.
export function localDateKey(value = new Date()) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

export function deadlineState(task, today) {
  if (!task.due_date) return 'undated'
  if (task.status === 'done') return 'done'
  if (task.due_date < today) return 'overdue'
  return task.due_date === today ? 'today' : 'upcoming'
}

function newestFirst(a, b) {
  return Date.parse(b.created_at) - Date.parse(a.created_at) || a.task_id.localeCompare(b.task_id)
}

export function selectTasks(tasks, { status = 'all', deadline = 'all', search = '', sort = 'newest', today = localDateKey() } = {}) {
  const term = search.trim().toLowerCase()
  return tasks.filter(task => (
    (status === 'all' || task.status === status)
    && (deadline === 'all' || deadlineState(task, today) === deadline)
    && (!term || `${task.title} ${task.assignee || ''}`.toLowerCase().includes(term))
  )).sort((a, b) => {
    if (sort === 'due_date') {
      if (a.due_date && !b.due_date) return -1
      if (!a.due_date && b.due_date) return 1
      if (a.due_date && b.due_date && a.due_date !== b.due_date) return a.due_date < b.due_date ? -1 : 1
    }
    return newestFirst(a, b)
  })
}
