<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const stages = ['现在做', '以后再说', '已放弃']

const source = ref(null)
const error = ref('')
const saving = ref(false)
const form = reactive({ project_id: '', title: '', summary: '', tags: '', premise: '', stage: '现在做' })

const where = computed(() => {
  if (!source.value) return ''
  const start = source.value.charStart
  const end = source.value.charEnd
  const span = start != null && end != null ? ` 第 ${start}–${end} 字` : ''
  return `会话 ${source.value.sessionId}${span}`
})

// 坐标由搜索页通过 query 传入，这里读取并预填
onMounted(() => {
  const q = route.query
  if (!q.messageId) {
    error.value = '这个地址没带出处坐标，请从搜索结果页点「存为想法」进入'
    return
  }
  const num = (v) => (v == null || v === '' ? null : Number(v))
  source.value = {
    projectId: q.projectId || '',
    sessionId: q.sessionId || '',
    messageId: q.messageId,
    charStart: num(q.charStart),
    charEnd: num(q.charEnd),
    snippet: q.snippet || '',
  }
  form.project_id = source.value.projectId
  form.summary = source.value.snippet
  form.title = source.value.snippet.slice(0, 40)
})

async function save() {
  if (!form.title.trim()) {
    error.value = '标题不能为空'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const idea = await api.fromSource({
      ref: source.value,
      quote: source.value.snippet || form.summary,
      project_id: form.project_id,
      title: form.title,
      summary: form.summary,
      tags: form.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean),
      premise: form.premise,
      stage: form.stage,
    })
    router.push('/ideas/' + idea.idea_id)
  } catch (e) {
    // 409：该原文已存过，跳转到已有卡片
    if (e.status === 409 && e.data && e.data.existing_idea_id) {
      router.push('/ideas/' + e.data.existing_idea_id)
      return
    }
    error.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="page">
    <RouterLink to="/ideas">← 返回列表</RouterLink>
    <h1>存为想法</h1>
    <p class="hint">原文会作为出处一起存下来，保存后能从卡片跳回原话。</p>

    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="source">
      <section class="card quote">
        <p class="hint">来自 {{ where }}</p>
        <p v-if="source.snippet" class="text">{{ source.snippet }}</p>
        <p v-else class="hint">这次没带原文，请在下面的说明里补一句。</p>
      </section>

      <form class="card form" @submit.prevent="save">
        <input v-model="form.title" placeholder="想法标题（必填）" maxlength="200" />
        <textarea v-model="form.summary" rows="3" placeholder="一句话说明这个想法是什么"></textarea>
        <div class="row">
          <input v-model="form.tags" placeholder="标签，逗号分隔" />
          <input v-model="form.premise" placeholder="适用条件：什么前提下才成立" />
        </div>
        <div class="row two">
          <input v-model="form.project_id" placeholder="项目编号，不填＝不绑定项目" />
          <select v-model="form.stage">
            <option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option>
          </select>
        </div>
        <div class="bar">
          <button type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
          <button type="button" class="plain" @click="router.push('/ideas')">取消</button>
        </div>
      </form>
    </template>

    <p v-else class="hint">从第二部分的搜索结果里点「存为想法」再进来。</p>
  </main>
</template>

<style scoped>
h1 { font-size: 22px; margin: 12px 0 4px; }
.quote { margin: 16px 0; background: #f9fafb; }
.quote .text { margin: 8px 0 0; white-space: pre-wrap; }

.form { display: grid; gap: 10px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.row.two { grid-template-columns: 1fr 120px; }
.bar { display: flex; gap: 8px; margin-top: 4px; }
</style>
