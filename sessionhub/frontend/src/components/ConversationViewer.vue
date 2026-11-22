<script setup>
import { ref, watch } from 'vue'
import { getConversation } from '../api.js'
import { normalizeError } from '../lib/errors.js'
import { copyText } from '../lib/clipboard.js'

const props = defineProps({
  conversationId: { type: String, default: '' },
})

const manualId = ref('')
const loading = ref(false)
const conversation = ref(null)
const errorText = ref('')
const copiedKey = ref('')

async function load(id) {
  const target = (id || '').trim()
  if (!target || loading.value) return
  loading.value = true
  errorText.value = ''
  conversation.value = null
  try {
    conversation.value = await getConversation(target)
  } catch (err) {
    if (err.kind === 'network') {
      errorText.value = err.message
    } else {
      const n = normalizeError(err.status, err.payload)
      errorText.value = n.kind === 'message' ? n.message : '读取失败（HTTP ' + err.status + '）'
    }
  } finally {
    loading.value = false
  }
}

// 导入结果点「查看会话」时自动带过来
watch(
  () => props.conversationId,
  (v) => {
    if (v) {
      manualId.value = v
      load(v)
    }
  }
)

function formatTime(value) {
  return value === null || value === '' ? '（原始记录没有时间）' : value
}

async function copy(key, text) {
  if (await copyText(text)) {
    copiedKey.value = key
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = ''
    }, 1200)
  }
}
</script>

<template>
  <section class="panel viewer-panel">
    <div class="panel-heading">
      <div>
        <h2>会话查看</h2>
        <p>对应 GET /api/conversations/{id}：消息按导入顺序排列，seq 从 1 起始，供第二模块溯源对齐。</p>
      </div>
      <span v-if="conversation" class="count-pill">{{ conversation.messages.length }}</span>
    </div>

    <div class="viewer-controls">
      <input
        v-model="manualId"
        class="mono"
        placeholder="粘贴 conversation_id，或从上方导入结果点「查看会话」"
        @keyup.enter="load(manualId)"
      />
      <button class="primary-button" :disabled="loading || !manualId.trim()" @click="load(manualId)">
        {{ loading ? '读取中…' : '加载会话' }}
      </button>
    </div>

    <div v-if="errorText" class="alert error" style="margin-top: 13px">
      {{ errorText }}
    </div>

    <div v-else-if="!conversation && !loading" class="empty-box" style="padding: 34px 12px">
      <strong>还没有加载会话</strong>
      <p>导入成功后点「查看会话」，或直接粘贴 conversation_id。也可以粘贴一个不存在的编号试试 404 的返回。</p>
    </div>

    <template v-if="conversation">
      <div class="viewer-meta">
        <div class="meta-row meta-title">
          <span>标题</span>{{ conversation.title }}
        </div>
        <div class="meta-row">
          <span>来源 source</span>{{ conversation.source }}
        </div>
        <div class="meta-row">
          <span>来源编号</span>
          <code class="mono">{{ conversation.source_conversation_id === null ? 'null（不参与查重）' : conversation.source_conversation_id }}</code>
        </div>
        <div class="meta-row">
          <span>project_id</span>
          <code class="mono">{{ conversation.project_id }}</code>
          <button class="copy-btn" :class="{ copied: copiedKey === 'v-project' }" @click="copy('v-project', conversation.project_id)">
            {{ copiedKey === 'v-project' ? '已复制' : '复制' }}
          </button>
        </div>
        <div class="meta-row">
          <span>conversation_id</span>
          <code class="mono">{{ conversation.conversation_id }}</code>
          <button class="copy-btn" :class="{ copied: copiedKey === 'v-conv' }" @click="copy('v-conv', conversation.conversation_id)">
            {{ copiedKey === 'v-conv' ? '已复制' : '复制' }}
          </button>
        </div>
      </div>

      <div class="msg-list">
        <div v-for="m in conversation.messages" :key="m.message_id" class="msg-item">
          <div class="msg-head">
            <span class="seq-pill">#{{ m.seq }}</span>
            <span class="role-badge" :class="m.role">{{ m.role }}</span>
            <span class="msg-time">{{ formatTime(m.created_at) }}</span>
          </div>
          <div class="msg-content">{{ m.content }}</div>
          <div class="msg-foot">
            <span>message_id</span>
            <code class="mono">{{ m.message_id }}</code>
            <button class="copy-btn" :class="{ copied: copiedKey === 'v-' + m.message_id }" @click="copy('v-' + m.message_id, m.message_id)">
              {{ copiedKey === 'v-' + m.message_id ? '已复制' : '复制' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
