<script setup>
import { computed, ref } from 'vue'
import { buildImportPayload, countMessages, fieldsFromBody } from '../lib/errors.js'
import { SAMPLE_409_TEXT, SAMPLE_BASIC_TEXT } from '../sample.js'

const props = defineProps({
  projectId: { type: String, default: '' },
  importing: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])

const title = ref('讨论会话导入格式的边界')
const source = ref('synthetic')
const sourceConversationId = ref('')
const messagesText = ref(SAMPLE_BASIC_TEXT)

const parseState = computed(() => {
  const n = countMessages(messagesText.value)
  return n === null
    ? { ok: false, text: 'messages 目前不是可用的 JSON（数组或完整请求体），无法发送' }
    : { ok: true, text: '已解析 ' + n + ' 条消息' }
})

const canSubmit = computed(() => !!props.projectId && parseState.value.ok && !props.importing)

// 载入样例：textarea 放仓库样例原文（完整请求体），同时把字段反填到表单输入框。
function loadSample(which) {
  messagesText.value = which === '409' ? SAMPLE_409_TEXT : SAMPLE_BASIC_TEXT
  const fields = fieldsFromBody(messagesText.value)
  if (fields) {
    title.value = fields.title || title.value
    source.value = fields.source || source.value
    sourceConversationId.value = fields.sourceConversationId
  }
}

function formatJson() {
  const n = countMessages(messagesText.value)
  if (n !== null) messagesText.value = JSON.stringify(JSON.parse(messagesText.value), null, 2)
}

function clearMessages() {
  messagesText.value = ''
}

function submit() {
  if (!canSubmit.value) return
  const built = buildImportPayload({
    title: title.value,
    source: source.value,
    sourceConversationId: sourceConversationId.value,
    messagesText: messagesText.value,
  })
  if (!built.ok) return // parseState 已拦截，这里只做保险
  emit('submit', built.payload)
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h2>导入表单</h2>
        <p>字段约定见《会话导入与管理-格式说明》v1.1：title / source 必填非空，messages 至少 1 条，role 三选一，created_at 可为 null。</p>
      </div>
    </div>

    <div class="form-grid">
      <label class="field full">
        <span>会话标题 title（必填）</span>
        <input v-model="title" placeholder="如：讨论会话导入格式的边界" />
      </label>
      <label class="field">
        <span>来源 source（必填，建议值）</span>
        <input v-model="source" list="source-options" placeholder="manual / paste / json_file / synthetic" />
        <datalist id="source-options">
          <option value="manual"></option>
          <option value="paste"></option>
          <option value="json_file"></option>
          <option value="synthetic"></option>
        </datalist>
      </label>
      <label class="field">
        <span>来源会话编号 source_conversation_id（可留空）</span>
        <input v-model="sourceConversationId" placeholder="留空等同 null，不参与查重" />
      </label>
      <label class="field full">
        <span>消息 messages（JSON，至少 1 条）</span>
        <textarea
          v-model="messagesText"
          rows="13"
          class="mono"
          spellcheck="false"
          placeholder='支持两种粘贴：完整请求体 { title, source, source_conversation_id, messages }（以其中字段为准），或仅 messages 数组 [ { "role": "user", ... }, ... ]'
        ></textarea>
      </label>
    </div>

    <div class="toolbar">
      <button class="small-button" @click="loadSample('basic')">载入仓库样例</button>
      <button class="small-button" @click="loadSample('409')">载入 409 演示样例</button>
      <button class="small-button" :disabled="!parseState.ok" @click="formatJson">格式化 JSON</button>
      <button class="small-button" @click="clearMessages">清空</button>
    </div>
    <div class="parse-hint" :class="{ bad: !parseState.ok }">{{ parseState.text }}</div>

    <div class="submit-row">
      <button class="primary-button" :disabled="!canSubmit" @click="submit">
        {{ importing ? '导入中…' : '导入会话' }}
      </button>
      <span v-if="!projectId" class="why-disabled">先在上方选择或创建项目（否则接口返回 404）</span>
      <span v-else-if="!parseState.ok" class="why-disabled">先修正 messages 的 JSON 语法</span>
    </div>
  </section>
</template>
