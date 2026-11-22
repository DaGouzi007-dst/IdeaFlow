<script setup>
import { computed, ref } from 'vue'
import { normalizeError, issueRows } from '../lib/errors.js'
import { copyText } from '../lib/clipboard.js'

const props = defineProps({
  state: { type: Object, default: () => ({ phase: 'idle' }) },
})
const emit = defineEmits(['overwrite', 'view'])

// state.phase: idle | loading | success | error
// state.error: { status?, payload?, kind?, message? }
const normalized = computed(() => {
  if (props.state.phase !== 'error' || !props.state.error) return null
  if (props.state.error.kind === 'network') {
    return { status: 0, kind: 'network', message: props.state.error.message, existingConversationId: null }
  }
  return normalizeError(props.state.error.status, props.state.error.payload)
})

const rows = computed(() =>
  normalized.value && normalized.value.kind === 'issues' ? issueRows(normalized.value.issues) : []
)

const rawText = computed(() => {
  if (props.state.phase !== 'error' || !props.state.error) return ''
  return JSON.stringify(props.state.error.payload ?? {}, null, 2)
})

const copiedKey = ref('')
async function copy(key, text) {
  if (await copyText(text)) {
    copiedKey.value = key
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = ''
    }, 1200)
  }
}

function copyAllMessageIds() {
  if (props.state.phase === 'success') copy('all-ids', JSON.stringify(props.state.result.message_ids))
}

function overwrite() {
  if (
    window.confirm(
      '覆盖导入会先删除旧会话及其全部消息，再写入本次内容（同一事务内完成）。确定覆盖？'
    )
  ) {
    emit('overwrite')
  }
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h2>导入结果</h2>
        <p>成功返回全链路编号；错误按"第几条消息、哪个字段、什么原因"定位。</p>
      </div>
      <span v-if="state.phase === 'success'" class="state-pill" :class="state.result.overwritten ? 'overwritten' : 'new'">
        {{ state.result.overwritten ? '已覆盖旧会话' : '新导入' }}
      </span>
    </div>

    <!-- 空闲 -->
    <div v-if="state.phase === 'idle'" class="empty-box">
      <div class="empty-icon">↓</div>
      <strong>还没有导入结果</strong>
      <p>填写左侧表单后点「导入会话」。可以用内置样例先跑一遍：仓库样例演示正常导入，409 演示样例演示重复提示与覆盖。</p>
    </div>

    <!-- 进行中 -->
    <div v-else-if="state.phase === 'loading'" class="empty-box">
      <strong>正在导入…</strong>
      <p>校验按规则 1-6 顺序执行，全部通过后一次性写入。</p>
    </div>

    <!-- 成功 -->
    <template v-else-if="state.phase === 'success'">
      <div class="alert success" style="margin-top: 2px">
        <span class="alert-title">导入成功（201）</span>
        共写入 {{ state.result.imported_count }} 条消息，编号已生成，可直接给检索与溯源模块使用。
      </div>
      <div class="id-line">
        <span>conversation_id</span>
        <code class="mono">{{ state.result.conversation_id }}</code>
        <button class="copy-btn" :class="{ copied: copiedKey === 'conv' }" @click="copy('conv', state.result.conversation_id)">
          {{ copiedKey === 'conv' ? '已复制' : '复制' }}
        </button>
      </div>
      <div class="mid-row">
        <span style="font-size: 11px; color: #7c9083">message_ids（seq 与查看接口一致，1 起始）</span>
        <div class="actions">
          <button class="small-button" @click="copyAllMessageIds">
            {{ copiedKey === 'all-ids' ? '已复制' : '复制全部（JSON 数组）' }}
          </button>
          <button class="primary-button" @click="emit('view', state.result.conversation_id)">查看会话</button>
        </div>
      </div>
      <div class="message-id-list">
        <div v-for="(id, i) in state.result.message_ids" :key="id" class="message-id-row">
          <span class="seq-pill">#{{ i + 1 }}</span>
          <code class="mono">{{ id }}</code>
          <button class="copy-btn" :class="{ copied: copiedKey === 'id-' + i }" @click="copy('id-' + i, id)">
            {{ copiedKey === 'id-' + i ? '已复制' : '复制' }}
          </button>
        </div>
      </div>
    </template>

    <!-- 失败 -->
    <template v-else-if="state.phase === 'error' && normalized">
      <!-- 网络 -->
      <div v-if="normalized.kind === 'network'" class="alert error">
        <span class="alert-title">无法连接后端</span>
        {{ normalized.message }}
      </div>

      <!-- 404 -->
      <template v-else-if="normalized.status === 404">
        <div class="alert error">
          <span class="alert-title">404：项目或会话不存在</span>
          {{ normalized.message }}
        </div>
        <div class="alert info" style="margin-bottom: 0">先在上方选择正确的项目；如果列表里没有，用「新建项目」创建后再导入。</div>
      </template>

      <!-- 409 -->
      <template v-else-if="normalized.status === 409">
        <div class="alert warn">
          <span class="alert-title">409：同来源会话已存在（校验规则第 6 条）</span>
          {{ normalized.message }}
        </div>
        <div v-if="normalized.existingConversationId" class="id-line">
          <span>existing_conversation_id</span>
          <code class="mono">{{ normalized.existingConversationId }}</code>
          <button
            class="copy-btn"
            :class="{ copied: copiedKey === 'existing' }"
            @click="copy('existing', normalized.existingConversationId)"
          >
            {{ copiedKey === 'existing' ? '已复制' : '复制' }}
          </button>
        </div>
        <div class="mid-row">
          <span style="font-size: 11px; color: #9b6d2a">确认要替换旧会话吗？替换是原子操作，不会留下半份残留。</span>
          <div class="actions">
            <button class="secondary-button" @click="overwrite">覆盖导入（?overwrite=true）</button>
          </div>
        </div>
      </template>

      <!-- 422 -->
      <template v-else-if="normalized.status === 422">
        <div class="alert error">
          <span class="alert-title">422：格式或取值错误，共 {{ rows.length }} 个问题（一次校验报出全部）</span>
          按"位置 / 字段 / 原因 / 收到值"逐项修复后重新提交即可，无需修一个报一个。
        </div>
        <table class="issue-table">
          <thead>
            <tr><th>位置</th><th>字段</th><th>问题</th><th>收到值</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in rows" :key="i">
              <td>{{ row.where }}</td>
              <td><code class="mono">{{ row.field }}</code></td>
              <td>{{ row.issue }}</td>
              <td class="received"><code v-if="row.received !== ''">{{ row.received }}</code></td>
            </tr>
          </tbody>
        </table>
        <details class="raw-details">
          <summary>查看原始 JSON 响应</summary>
          <pre>{{ rawText }}</pre>
        </details>
      </template>

      <!-- 其他 -->
      <div v-else class="alert error">
        <span class="alert-title">请求失败（HTTP {{ normalized.status }}）</span>
        响应不符合本模块错误约定，可展开下方原始内容排查。
        <details class="raw-details" style="margin-top: 8px">
          <summary>查看原始 JSON 响应</summary>
          <pre>{{ rawText }}</pre>
        </details>
      </div>
    </template>
  </section>
</template>
