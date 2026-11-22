<script setup>
import { onMounted, ref } from 'vue'
import { importConversation, listProjects } from './api.js'
import ProjectBar from './components/ProjectBar.vue'
import ImportForm from './components/ImportForm.vue'
import ResultPanel from './components/ResultPanel.vue'
import ConversationViewer from './components/ConversationViewer.vue'

const projects = ref([])
const activeProjectId = ref(localStorage.getItem('sessionhub.activeProject') || '')
const conn = ref({ ok: false, checked: false })
const importState = ref({ phase: 'idle' })
const viewerConversationId = ref('')

// 覆盖导入需要原样重发上一次的请求体
let lastPayload = null
let lastProjectId = ''

function rememberProject(id) {
  activeProjectId.value = id
  localStorage.setItem('sessionhub.activeProject', id)
}

async function refreshProjects() {
  try {
    projects.value = await listProjects()
    conn.value = { ok: true, checked: true }
    if (!projects.value.some((p) => p.project_id === activeProjectId.value)) {
      rememberProject(projects.value.length ? projects.value[0].project_id : '')
    }
  } catch {
    conn.value = { ok: false, checked: true }
  }
}

function handleCreated(created) {
  rememberProject(created.project_id)
  refreshProjects()
}

async function runImport(payload, overwrite) {
  lastPayload = payload
  lastProjectId = activeProjectId.value
  importState.value = { phase: 'loading' }
  try {
    const result = await importConversation(lastProjectId, payload, overwrite)
    importState.value = { phase: 'success', result }
  } catch (err) {
    importState.value = {
      phase: 'error',
      error: {
        kind: err.kind,
        status: err.status,
        payload: err.payload,
        message: err.kind === 'network' ? err.message : '',
      },
    }
  }
}

function handleSubmit(payload) {
  runImport(payload, false)
}

function handleOverwrite() {
  if (lastPayload && lastProjectId) runImport(lastPayload, true)
}

function handleView(conversationId) {
  viewerConversationId.value = ''
  // 触发 ConversationViewer 的 watch（同值重复点击也要重新加载）
  requestAnimationFrame(() => {
    viewerConversationId.value = conversationId
  })
}

onMounted(refreshProjects)
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <div class="brand-mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3v10" />
          <path d="m8 9 4 4 4-4" />
          <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
      </div>
      <div>
        <strong>会话导入与管理</strong>
        <small>IDEAFLOW · 第一模块 · SESSIONHUB</small>
      </div>
    </div>
    <div class="conn-pill" :class="{ ok: conn.ok }">
      <span class="conn-dot"></span>
      <template v-if="conn.ok">后端已连接（8001）</template>
      <template v-else-if="conn.checked">后端不可达</template>
      <template v-else>正在检查后端…</template>
    </div>
  </header>

  <main class="content">
    <div class="page-heading">
      <div class="eyebrow">第一模块 <span></span> 导入全流程</div>
      <h1>导入会话，拿到全链路编号</h1>
      <p>
        创建或选择项目 → 粘贴约定格式的 JSON → 导入 → 复制 conversation_id / message_ids 给检索与溯源模块 → 查看原文。
        错误按"第几条消息、哪个字段、什么原因"一次报全；同来源重复给出 409 提示并支持覆盖导入。
      </p>
    </div>

    <ProjectBar
      :projects="projects"
      v-model="activeProjectId"
      @created="handleCreated"
    />

    <div class="workspace-grid" style="margin-top: 16px">
      <ImportForm
        :project-id="activeProjectId"
        :importing="importState.phase === 'loading'"
        @submit="handleSubmit"
      />
      <ResultPanel
        :state="importState"
        @overwrite="handleOverwrite"
        @view="handleView"
      />
    </div>

    <ConversationViewer :conversation-id="viewerConversationId" />
  </main>
</template>
