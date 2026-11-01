<script setup>
import { onMounted, reactive, ref } from 'vue'

const stages = ['现在做', '以后再说', '已放弃']
const ideas = ref([])
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')

const form = reactive({ title: '', summary: '', tags: '', premise: '', stage: '现在做' })

async function call(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    let detail = `请求失败（HTTP ${response.status}）`
    try {
      const body = await response.json()
      if (body && body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : '填的内容不合法'
      }
    } catch (ignored) {
      // 后端没返回 JSON，就用默认提示
    }
    throw new Error(detail)
  }
  return response.status === 204 ? null : response.json()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const q = keyword.value.trim()
    ideas.value = await call(`/api/ideas${q ? `?q=${encodeURIComponent(q)}` : ''}`)
  } catch (err) {
    error.value = `连不上后端：${err.message}`
  } finally {
    loading.value = false
  }
}

// 输入停下来再搜，不要每敲一个字就发一次请求
let timer = null
function search() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}

async function createIdea() {
  if (!form.title.trim()) {
    error.value = '标题不能为空'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await call('/api/ideas', {
      method: 'POST',
      body: JSON.stringify({
        ...form,
        tags: form.tags.split(/[,，]/).map((tag) => tag.trim()).filter(Boolean),
      }),
    })
    Object.assign(form, { title: '', summary: '', tags: '', premise: '', stage: '现在做' })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function patch(idea, changes) {
  error.value = ''
  try {
    Object.assign(idea, await call(`/api/ideas/${idea.idea_id}`, {
      method: 'PATCH',
      body: JSON.stringify(changes),
    }))
  } catch (err) {
    error.value = err.message
    await load()
  }
}

async function removeIdea(idea) {
  if (!confirm(`删除「${idea.title}」？`)) return
  try {
    await call(`/api/ideas/${idea.idea_id}`, { method: 'DELETE' })
    await load()
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
</script>

<template>
  <main class="page">
    <header class="head">
      <h1>想法卡片</h1>
      <p>把对话里值得留下的东西存成卡片，写清它在什么前提下成立。</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <form class="card create" @submit.prevent="createIdea">
      <input v-model="form.title" placeholder="想法标题（必填）" maxlength="200" />
      <input v-model="form.summary" placeholder="一句话说明" />
      <div class="row">
        <input v-model="form.tags" placeholder="标签，逗号分隔" />
        <input v-model="form.premise" placeholder="适用条件：什么前提下才成立" />
        <select v-model="form.stage">
          <option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option>
        </select>
      </div>
      <button type="submit" :disabled="saving">{{ saving ? '保存中…' : '记下来' }}</button>
    </form>

    <div class="search">
      <input v-model="keyword" placeholder="搜索标题、说明、标签、适用条件" @input="search" />
      <button type="button" @click="load">刷新</button>
    </div>

    <p v-if="loading" class="hint">加载中…</p>
    <p v-else-if="!ideas.length" class="hint">还没有想法，在上面记一条试试。</p>

    <ul class="list">
      <li v-for="idea in ideas" :key="idea.idea_id" class="card idea">
        <div class="idea-head">
          <h2>{{ idea.title }}</h2>
          <button type="button" class="star" :class="{ on: idea.favorite }"
                  :title="idea.favorite ? '取消收藏' : '收藏'"
                  @click="patch(idea, { favorite: !idea.favorite })">
            {{ idea.favorite ? '★' : '☆' }}
          </button>
        </div>

        <p v-if="idea.summary" class="summary">{{ idea.summary }}</p>
        <p v-if="idea.premise" class="premise">前提：{{ idea.premise }}</p>

        <p v-if="idea.tags.length" class="tags">
          <span v-for="tag in idea.tags" :key="tag">{{ tag }}</span>
        </p>

        <p v-if="idea.sources.length" class="sources">
          来源：{{ idea.sources.join('、') }}
        </p>

        <div class="idea-foot">
          <select :value="idea.stage" @change="patch(idea, { stage: $event.target.value })">
            <option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option>
          </select>
          <button type="button" class="danger" @click="removeIdea(idea)">删除</button>
        </div>
      </li>
    </ul>
  </main>
</template>

<style>
* { box-sizing: border-box; }

body {
  margin: 0;
  background: #f6f7f9;
  color: #1f2328;
  font: 15px/1.6 "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
}

.page {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 20px 64px;
}

.head h1 { margin: 0 0 4px; font-size: 24px; }
.head p { margin: 0 0 20px; color: #6b7280; }

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}

.create { display: grid; gap: 10px; margin-bottom: 16px; }
.row { display: grid; grid-template-columns: 1fr 1fr 120px; gap: 10px; }

input, select, button {
  font: inherit;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
}

button { cursor: pointer; background: #1f6feb; border-color: #1f6feb; color: #fff; }
button:disabled { opacity: 0.6; cursor: default; }

.search { display: flex; gap: 8px; margin: 20px 0 12px; }
.search input { flex: 1; }

.error { background: #fee2e2; color: #991b1b; padding: 10px 12px; border-radius: 8px; }
.hint { color: #6b7280; }

.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.idea-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.idea-head h2 { margin: 0; font-size: 17px; }

.star { background: none; border: none; color: #9ca3af; font-size: 20px; line-height: 1; padding: 0 4px; }
.star.on { color: #f59e0b; }

.summary { margin: 6px 0 0; }
.premise { margin: 6px 0 0; color: #92400e; }
.sources { margin: 6px 0 0; color: #6b7280; font-size: 13px; }

.tags { margin: 8px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
.tags span { background: #eef2ff; color: #3730a3; border-radius: 999px; padding: 1px 10px; font-size: 13px; }

.idea-foot { margin-top: 12px; display: flex; gap: 8px; align-items: center; }
.danger { background: #fff; color: #b91c1c; border-color: #fca5a5; }
</style>
