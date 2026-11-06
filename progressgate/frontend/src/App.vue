<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import BrandMark from './components/BrandMark.vue'

const route = useRoute()
const router = useRouter()
const project = ref(null)
const ideas = ref([])
const decisions = ref({})
const tasks = ref([])
const events = ref([])
const decisionEvents = ref([])
const selectedId = ref(null)
const activeFilter = ref('all')
const search = ref('')
const loading = ref(true)
const saving = ref(false)
const notice = ref('')
const error = ref('')
const dialog = ref(null)
const taskTitle = ref(null)
const selectedIdeaId = ref(null)
const sources = ref([])
const decisionForm = reactive({ status: 'pending', reason: '' })
const newTask = reactive({ title: '', description: '', assignee: '', due_date: '', completion_condition: '', idea_id: '' })
const edit = reactive({})

const statusLabels = { todo: '待开始', in_progress: '进行中', blocked: '受阻', done: '已完成' }
const decisionLabels = { pending: '待讨论', adopted: '已采纳', rejected: '暂不采纳' }
const fieldLabels = {
  title: '标题', description: '说明', assignee: '负责人', due_date: '截止日期', completion_condition: '完成条件',
  status: '状态', block_reason: '阻塞原因', error_excerpt: '错误信息', attempted_steps: '已尝试的方法',
  next_step: '下一步', resolution: '处理结果', result: '执行结果',
}
const selectedTask = computed(() => tasks.value.find(task => task.task_id === selectedId.value))
const selectedIdea = computed(() => ideas.value.find(idea => idea.idea_id === selectedIdeaId.value))
const linkedTasks = computed(() => tasks.value.filter(task => task.idea_id === selectedIdeaId.value))
const counts = computed(() => ({
  all: tasks.value.length,
  in_progress: tasks.value.filter(task => task.status === 'in_progress').length,
  blocked: tasks.value.filter(task => task.status === 'blocked').length,
  done: tasks.value.filter(task => task.status === 'done').length,
}))
const visibleTasks = computed(() => tasks.value.filter(task => {
  const matchesStatus = activeFilter.value === 'all' || task.status === activeFilter.value
  const term = search.value.trim().toLowerCase()
  return matchesStatus && (!term || `${task.title} ${task.assignee || ''}`.toLowerCase().includes(term))
}))
const cards = [
  { key: 'all', label: '全部任务', hint: '项目中的任务', icon: '▦' },
  { key: 'in_progress', label: '进行中', hint: '正在推进', icon: '↗' },
  { key: 'blocked', label: '受阻', hint: '需要跟进', icon: '!' },
  { key: 'done', label: '已完成', hint: '已记录结果', icon: '✓' },
]

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : '请检查填写内容后重试。'
    throw new Error(detail)
  }
  return body
}

async function refreshDecisions() {
  const entries = await Promise.all(ideas.value.map(async idea => [
    idea.idea_id, await api(`/api/ideas/${idea.idea_id}/decision`),
  ]))
  decisions.value = Object.fromEntries(entries)
  syncDecisionForm()
}

async function refreshTasks(selectId = selectedId.value) {
  tasks.value = await api(`/api/projects/${project.value.project_id}/tasks`)
  const visible = visibleTasks.value
  selectedId.value = visible.some(task => task.task_id === selectId) ? selectId : (visible[0]?.task_id || null)
  await syncTaskLocation()
  await loadTaskDetails()
}

async function syncTaskLocation() {
  if (route.name === 'tasks' && route.query.task && route.query.task !== selectedId.value) {
    await router.replace({ name: 'tasks', query: selectedId.value ? { task: selectedId.value } : {} })
  }
}

async function loadTaskDetails() {
  const task = selectedTask.value
  if (!task) { events.value = []; return }
  Object.assign(edit, {
    title: task.title, description: task.description || '', assignee: task.assignee || '', due_date: task.due_date || '',
    completion_condition: task.completion_condition || '', status: task.status,
    block_reason: task.block_reason || '', error_excerpt: task.error_excerpt || '', attempted_steps: task.attempted_steps || '',
    next_step: task.next_step || '', resolution: task.resolution || '', result: task.result || '',
  })
  events.value = await api(`/api/tasks/${task.task_id}/events`)
}

async function selectTask(task) {
  error.value = ''
  notice.value = ''
  selectedId.value = task.task_id
  try { await syncTaskLocation(); await loadTaskDetails() } catch (err) { error.value = err.message }
}

function syncDecisionForm() {
  const decision = decisions.value[selectedIdeaId.value]
  decisionForm.status = decision?.status || 'pending'
  decisionForm.reason = decision?.reason || ''
}

function selectIdea(idea) {
  error.value = ''
  notice.value = ''
  selectedIdeaId.value = idea.idea_id
  syncDecisionForm()
}

async function loadIdeaSources(ideaId) {
  sources.value = []
  if (!ideaId) return
  try {
    const result = await api(`/api/demo/ideas/${ideaId}/sources`)
    if (selectedIdeaId.value === ideaId) sources.value = result
  } catch (err) {
    if (selectedIdeaId.value === ideaId) error.value = err.message
  }
}

async function loadDecisionEvents(ideaId) {
  decisionEvents.value = []
  if (!ideaId) return
  try {
    const result = await api(`/api/ideas/${ideaId}/decision/events`)
    if (selectedIdeaId.value === ideaId) decisionEvents.value = result
  } catch (err) {
    if (selectedIdeaId.value === ideaId) error.value = err.message
  }
}

async function reconcileSelection() {
  if (visibleTasks.value.some(task => task.task_id === selectedId.value)) return
  selectedId.value = visibleTasks.value[0]?.task_id || null
  try { await syncTaskLocation(); await loadTaskDetails() } catch (err) { error.value = err.message }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const projects = await api('/api/projects')
    project.value = projects[0] || null
    if (!project.value) throw new Error('暂无项目数据。')
    ideas.value = await api(`/api/projects/${project.value.project_id}/ideas`)
    selectedIdeaId.value = ideas.value.some(idea => idea.idea_id === route.query.idea)
      ? route.query.idea : (ideas.value[0]?.idea_id || null)
    if (route.name === 'tasks' && typeof route.query.task === 'string') selectedId.value = route.query.task
    await Promise.all([refreshDecisions(), refreshTasks()])
  } catch (err) { error.value = `无法连接服务：${err.message}` }
  finally { loading.value = false }
}

async function openCreate() {
  error.value = ''
  notice.value = ''
  Object.assign(newTask, { title: '', description: '', assignee: '', due_date: '', completion_condition: '', idea_id: '' })
  dialog.value.showModal()
  await nextTick()
  taskTitle.value?.focus()
}

async function createTask() {
  saving.value = true
  error.value = ''
  try {
    const task = await api(`/api/projects/${project.value.project_id}/tasks`, {
      method: 'POST', body: JSON.stringify({ ...newTask, idea_id: newTask.idea_id || null, due_date: newTask.due_date || null }),
    })
    dialog.value.close()
    activeFilter.value = 'all'
    search.value = ''
    await refreshTasks(task.task_id)
    notice.value = '任务已创建。'
  } catch (err) { error.value = err.message }
  finally { saving.value = false }
}

async function saveTask() {
  if (!selectedTask.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await api(`/api/tasks/${selectedTask.value.task_id}`, { method: 'PATCH', body: JSON.stringify({ ...edit, due_date: edit.due_date || null }) })
    await refreshTasks(selectedTask.value.task_id)
    notice.value = '任务进展已保存。'
  } catch (err) { error.value = err.message }
  finally { saving.value = false }
}

async function saveDecision() {
  if (!selectedIdea.value) return
  const ideaId = selectedIdea.value.idea_id
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await api(`/api/ideas/${ideaId}/decision`, {
      method: 'PUT', body: JSON.stringify(decisionForm),
    })
    await refreshDecisions()
    if (selectedIdeaId.value === ideaId) await loadDecisionEvents(ideaId)
    notice.value = '方案决策已保存。'
  } catch (err) { error.value = err.message }
  finally { saving.value = false }
}

function ideaTitle(id) {
  return ideas.value.find(idea => idea.idea_id === id)?.title || '来源想法不可用'
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function eventText(event) {
  if (event.event_type === 'created') return '创建了任务'
  const status = event.changes.status?.to
  if (status) return `状态更新为「${statusLabels[status] || status}」`
  const names = Object.keys(event.changes).map(key => fieldLabels[key] || key)
  return `更新了${names.join('、')}`
}

function changeValue(field, value) {
  if (value === null || value === '') return '未填写'
  return field === 'status' ? (statusLabels[value] || value) : value
}

watch([activeFilter, search], reconcileSelection)
watch(selectedIdeaId, loadIdeaSources)
watch(selectedIdeaId, loadDecisionEvents)
watch(() => [route.name, route.query.idea, route.query.task], () => {
  error.value = ''
  notice.value = ''
  if (route.name === 'decisions' && ideas.value.some(idea => idea.idea_id === route.query.idea)) {
    selectedIdeaId.value = route.query.idea
    syncDecisionForm()
  }
  if (route.name === 'tasks' && typeof route.query.task === 'string') {
    const task = tasks.value.find(item => item.task_id === route.query.task)
    if (task && task.task_id !== selectedId.value) {
      activeFilter.value = 'all'
      search.value = ''
      selectTask(task)
    }
  }
})
onMounted(load)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark"><BrandMark /></span>
        <span><strong>IdeaFlow</strong><small>想法与进展</small></span>
      </div>

      <div class="sidebar-section-label">工作空间</div>
      <div class="project-chip">
        <span class="project-avatar"><BrandMark /></span>
        <span class="project-copy"><strong>{{ project?.name || '示例项目' }}</strong><small>本地项目</small></span>
        <span class="project-chevron" aria-hidden="true">⌄</span>
      </div>

      <div class="sidebar-section-label nav-label">项目管理</div>
      <nav class="navigation" aria-label="主导航">
        <RouterLink to="/tasks" :class="{ active: route.name === 'tasks' }">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><rect x="3" y="3" width="6" height="6" rx="1.3"/><rect x="11" y="3" width="6" height="6" rx="1.3"/><rect x="3" y="11" width="6" height="6" rx="1.3"/><rect x="11" y="11" width="6" height="6" rx="1.3"/></svg>
          进展跟踪
        </RouterLink>
        <RouterLink to="/decisions" :class="{ active: route.name === 'decisions' }">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M6 3.5h8a1 1 0 0 1 1 1v12l-5-2.7-5 2.7v-12a1 1 0 0 1 1-1Z"/><path d="m7.8 8.5 1.5 1.5 3-3"/></svg>
          方案决策
        </RouterLink>
      </nav>

      <div class="sidebar-bottom">
        <span class="sidebar-bottom-icon">✳</span>
        <div><strong>把想法落到行动</strong><p>记录每一步的进展与决定。</p></div>
      </div>
    </aside>

    <main class="main">
      <header class="topbar"><span>工作空间 <span class="crumb">/</span> <strong>{{ route.name === 'decisions' ? '方案决策' : '进展跟踪' }}</strong></span><span class="topbar-right"><span class="live-dot"></span> 本地工作区</span></header>
      <div class="content">
        <div class="demo-banner"><span class="demo-badge">演示数据</span><span>项目与想法使用模拟数据，决策和任务保存在本机。</span></div>
        <div v-if="error && !dialog?.open" class="alert error" role="alert">{{ error }} <button type="button" @click="error = ''" aria-label="关闭提示">×</button></div>
        <div v-if="notice" class="alert success" role="status">{{ notice }} <button type="button" @click="notice = ''" aria-label="关闭提示">×</button></div>
        <div v-if="loading" class="loading">正在加载工作区…</div>

        <template v-else-if="route.name === 'tasks'">
          <div class="page-heading">
            <div><div class="eyebrow">PROGRESSGATE <span></span> 任务与进展</div><h1>进展跟踪</h1><p>把计划转化为行动，记录每一次推进。</p></div>
            <button class="primary-button" type="button" :disabled="!project" @click="openCreate"><span aria-hidden="true">＋</span> 新建任务</button>
          </div>

          <div class="stats" aria-label="任务状态筛选">
            <button v-for="card in cards" :key="card.key" type="button" class="stat-card" :class="[{ chosen: activeFilter === card.key }, `stat-${card.key}`]" :aria-pressed="activeFilter === card.key" @click="activeFilter = card.key">
              <div class="stat-top"><span>{{ card.label }}</span><span class="stat-icon">{{ card.icon }}</span></div>
              <div class="stat-bottom"><strong>{{ counts[card.key] }}</strong><small>{{ card.hint }}</small></div>
            </button>
          </div>

          <div class="workspace-grid">
            <section class="panel task-list-panel" aria-labelledby="task-list-title">
              <div class="panel-heading"><div><h2 id="task-list-title">任务列表</h2><p>聚焦眼前，逐步完成</p></div><span class="count-pill">{{ visibleTasks.length }}</span></div>
              <label class="search-field"><span aria-hidden="true">⌕</span><input v-model="search" type="search" placeholder="搜索任务或负责人" aria-label="搜索任务或负责人" /></label>
              <div v-if="visibleTasks.length" class="task-list">
                <button v-for="task in visibleTasks" :key="task.task_id" type="button" class="task-item" :class="{ selected: task.task_id === selectedId }" @click="selectTask(task)">
                  <span class="task-item-top"><span class="status-dot" :class="task.status"></span><strong>{{ task.title }}</strong><span class="task-arrow">↗</span></span>
                  <span class="task-item-bottom"><span class="status-pill" :class="task.status">{{ statusLabels[task.status] }}</span><span>{{ task.assignee || '未指定负责人' }}</span></span>
                </button>
              </div>
              <div v-else class="empty-list"><div class="empty-icon">▤</div><strong>{{ tasks.length ? '没有匹配的任务' : '还没有任务' }}</strong><p>{{ tasks.length ? '试试其他筛选条件。' : '创建第一个任务，开始记录进展。' }}</p><button v-if="!tasks.length" type="button" class="text-button" @click="openCreate">＋ 新建任务</button></div>
            </section>

            <section class="panel detail-panel" aria-labelledby="detail-title">
              <template v-if="selectedTask">
                <div class="detail-head"><div><div class="eyebrow muted">TASK DETAILS</div><h2 id="detail-title">任务详情</h2><p>更新进展，保留处理过程。</p></div><span class="status-pill" :class="selectedTask.status">{{ statusLabels[selectedTask.status] }}</span></div>
                <form class="detail-form" @submit.prevent="saveTask">
                  <div class="form-grid"><label class="field full"><span>任务标题 <em>*</em></span><input v-model="edit.title" required maxlength="200" /></label>
                    <label class="field"><span>负责人</span><input v-model="edit.assignee" maxlength="100" placeholder="填写负责人" /></label>
                    <label class="field"><span>当前状态</span><select v-model="edit.status"><option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option></select></label>
                    <label class="field full"><span>截止日期</span><input v-model="edit.due_date" type="date" /></label>
                    <label class="field full"><span>任务说明</span><textarea v-model="edit.description" rows="2" maxlength="5000" placeholder="补充任务背景或内容"></textarea></label>
                    <label class="field full"><span>完成条件</span><textarea v-model="edit.completion_condition" rows="2" maxlength="5000" placeholder="什么情况下算完成？"></textarea></label>
                  </div>
                  <div class="source-line"><span>关联想法</span><RouterLink v-if="selectedTask.idea_id" class="source-link" :to="{ name: 'decisions', query: { idea: selectedTask.idea_id } }">{{ ideaTitle(selectedTask.idea_id) }} <span aria-hidden="true">↗</span></RouterLink><strong v-else>手动创建 · 暂无关联</strong></div>
                  <div class="divider"></div>
                  <div class="section-heading"><span class="section-icon">↳</span><div><h3>阻塞与处理</h3><p>记录遇到的问题，方便后续回顾。</p></div></div>
                  <div class="form-grid"><label class="field full"><span>阻塞原因 <em v-if="edit.status === 'blocked'">*</em></span><textarea v-model="edit.block_reason" rows="2" maxlength="5000" :required="edit.status === 'blocked'" placeholder="遇到了什么问题？"></textarea></label>
                    <label class="field full"><span>错误信息或片段</span><textarea v-model="edit.error_excerpt" rows="2" maxlength="5000" placeholder="粘贴有助于排查的错误信息"></textarea></label>
                    <label class="field"><span>已尝试的方法</span><textarea v-model="edit.attempted_steps" rows="2" maxlength="5000" placeholder="记录已经做过的尝试"></textarea></label>
                    <label class="field"><span>下一步</span><textarea v-model="edit.next_step" rows="2" maxlength="5000" placeholder="接下来准备怎么做？"></textarea></label>
                    <label class="field"><span>处理结果</span><textarea v-model="edit.resolution" rows="2" maxlength="5000" placeholder="问题是如何解决的？"></textarea></label>
                    <label class="field"><span>执行结果 <em v-if="edit.status === 'done'">*</em></span><textarea v-model="edit.result" rows="2" maxlength="5000" :required="edit.status === 'done'" placeholder="记录任务的最终结果"></textarea></label>
                  </div>
                  <div class="save-row"><span>修改后记得保存</span><button class="primary-button" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存进展' }}</button></div>
                </form>
                <div class="history"><div class="history-title"><h3>进展记录</h3><span>按时间记录</span></div><ol><li v-for="event in events" :key="event.event_id"><span class="history-dot"></span><div class="history-entry"><strong>{{ eventText(event) }}</strong><small>{{ formatDate(event.created_at) }}</small><details v-if="Object.keys(event.changes).length"><summary>查看变更</summary><dl><div v-for="(change, field) in event.changes" :key="field"><dt>{{ fieldLabels[field] || field }}</dt><dd><span>{{ changeValue(field, change.from) }}</span><span aria-hidden="true"> → </span><span>{{ changeValue(field, change.to) }}</span></dd></div></dl></details></div></li></ol></div>
              </template>
              <div v-else class="empty-detail"><div class="empty-illustration"><span>✓</span></div><h2 id="detail-title">{{ tasks.length ? '选择一项任务' : '从一个任务开始' }}</h2><p>{{ tasks.length ? '选择左侧任务，查看和更新它的进展。' : '创建任务后，可以在这里记录负责人、进度、遇到的问题和处理结果。' }}</p><button v-if="!tasks.length" class="secondary-button" type="button" :disabled="!project" @click="openCreate">新建任务 <span>↗</span></button></div>
            </section>
          </div>
        </template>

        <template v-else>
          <div class="page-heading decision-heading"><div><div class="eyebrow">PROGRESSGATE <span></span> 方案与选择</div><h1>方案决策</h1><p>记录采纳与否，以及做出选择的原因。</p></div></div>
          <div class="workspace-grid decisions-grid">
            <section class="panel idea-panel" aria-labelledby="ideas-title"><div class="panel-heading"><div><h2 id="ideas-title">项目想法</h2><p>选择一条想法，记录决策</p></div><span class="count-pill">{{ ideas.length }}</span></div>
              <div v-if="ideas.length" class="idea-list"><button v-for="idea in ideas" :key="idea.idea_id" type="button" class="idea-item" :class="{ selected: idea.idea_id === selectedIdeaId }" @click="selectIdea(idea)"><span class="idea-icon">✧</span><span class="idea-item-copy"><strong>{{ idea.title }}</strong><small>{{ idea.content }}</small><span class="idea-decision">{{ decisionLabels[decisions[idea.idea_id]?.status || 'pending'] }}</span></span><span class="task-arrow">↗</span></button></div>
              <div v-else class="empty-list"><strong>暂无想法</strong></div>
            </section>
            <section class="panel decision-panel" aria-labelledby="decision-title">
              <template v-if="selectedIdea"><div class="detail-head"><div><div class="eyebrow muted">DECISION DETAILS</div><h2 id="decision-title">记录方案选择</h2><p>让以后的每一次回顾都有据可依。</p></div></div>
                <div class="idea-summary"><span class="idea-summary-label">当前想法</span><strong>{{ selectedIdea.title }}</strong><p>{{ selectedIdea.content }}</p><small>{{ sources.length ? '已关联模拟来源消息' : '暂无来源消息' }}</small></div>
                <details v-if="sources.length" class="source-details"><summary>查看来源与上下文</summary><div v-for="source in sources" :key="source.message_id" class="source-context"><strong>{{ source.conversation_title }}</strong><div v-for="message in source.context" :key="message.message_id" class="source-message" :class="{ highlighted: message.message_id === source.message_id }"><small>{{ message.role === 'user' ? '用户' : message.role === 'assistant' ? 'AI' : '系统' }}{{ message.message_id === source.message_id ? ' · 来源消息' : '' }}</small><p>{{ message.content }}</p></div></div></details>
                <form @submit.prevent="saveDecision"><div class="decision-form"><label class="field"><span>决策状态</span><select v-model="decisionForm.status"><option v-for="(label, key) in decisionLabels" :key="key" :value="key">{{ label }}</option></select></label><label class="field"><span>选择理由</span><textarea v-model="decisionForm.reason" rows="5" maxlength="5000" placeholder="为什么采纳或暂不采纳？"></textarea></label></div><div class="decision-note"><span>✦</span> 采纳后的想法可以在创建任务时关联。</div><div class="save-row"><span>决策可随时修改</span><button class="primary-button" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存决策' }}</button></div></form>
                <div class="history"><div class="history-title"><h3>决策记录</h3><span>按时间记录</span></div><p v-if="!decisionEvents.length">暂无决策记录；升级前的修改无法追溯。</p><ol v-else><li v-for="event in decisionEvents" :key="event.event_id"><span class="history-dot"></span><div class="history-entry"><strong>{{ event.event_type === 'created' ? '记录了决策' : '修改了决策' }}</strong><small>{{ formatDate(event.created_at) }}</small><dl><div v-for="(change, field) in event.changes" :key="field"><dt>{{ field === 'status' ? '决策状态' : '选择理由' }}</dt><dd><span>{{ field === 'status' ? (decisionLabels[change.from] || '未记录') : (change.from || '未填写') }}</span><span aria-hidden="true"> → </span><span>{{ field === 'status' ? (decisionLabels[change.to] || '未记录') : (change.to || '未填写') }}</span></dd></div></dl></div></li></ol></div>
                <div class="linked-tasks"><div class="history-title"><h3>关联任务</h3><span>{{ linkedTasks.length }} 项</span></div><p v-if="!linkedTasks.length">暂无关联任务。</p><RouterLink v-for="task in linkedTasks" :key="task.task_id" :to="{ name: 'tasks', query: { task: task.task_id } }"><strong>{{ task.title }}</strong><span class="status-pill" :class="task.status">{{ statusLabels[task.status] }}</span></RouterLink></div>
              </template>
              <div v-else class="empty-detail"><h2 id="decision-title">选择一条想法</h2><p>在这里记录是否采纳及选择理由。</p></div>
            </section>
          </div>
        </template>
        <footer class="page-footer">IDEAFLOW <span>·</span> 将想法与行动连接起来</footer>
      </div>
    </main>

    <dialog ref="dialog" class="create-dialog" @close="error = ''">
      <div class="dialog-heading"><div><div class="eyebrow muted">NEW TASK</div><h2>新建任务</h2><p>先记录下来，再逐步完善。</p></div><button class="icon-button" type="button" aria-label="关闭" @click="dialog.close()">×</button></div>
      <div v-if="error" class="alert error dialog-alert" role="alert">{{ error }}</div>
      <form class="create-form" @submit.prevent="createTask"><label class="field"><span>任务标题 <em>*</em></span><input ref="taskTitle" v-model="newTask.title" required maxlength="200" placeholder="例如：整理任务状态页面" /></label><label class="field"><span>任务说明</span><textarea v-model="newTask.description" rows="2" maxlength="5000" placeholder="这项任务需要做什么？"></textarea></label><div class="form-grid"><label class="field"><span>负责人</span><input v-model="newTask.assignee" maxlength="100" placeholder="填写负责人" /></label><label class="field"><span>截止日期</span><input v-model="newTask.due_date" type="date" /></label></div><label class="field"><span>关联想法</span><select v-model="newTask.idea_id"><option value="">不关联，手动创建</option><option v-for="idea in ideas" :key="idea.idea_id" :value="idea.idea_id">{{ idea.title }}{{ decisions[idea.idea_id]?.status === 'adopted' ? '（已采纳）' : '（待采纳）' }}</option></select></label><label class="field"><span>完成条件</span><input v-model="newTask.completion_condition" maxlength="5000" placeholder="什么情况下算完成？" /></label><p class="form-help">关联想法前，请先在“方案决策”中将其设为已采纳。</p><div class="dialog-actions"><button class="secondary-button" type="button" @click="dialog.close()">取消</button><button class="primary-button" type="submit" :disabled="saving">{{ saving ? '创建中…' : '创建任务' }}</button></div></form>
    </dialog>
  </div>
</template>
