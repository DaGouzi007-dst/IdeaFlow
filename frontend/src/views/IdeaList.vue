<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const stages = ['现在做', '以后再说', '已放弃']
const ideas = ref([])
const keyword = ref('')
const loading = ref(false)
const error = ref('')
const form = reactive({ project_id: 'demo-project', title: '', summary: '', tags: '', premise: '', stage: '现在做' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    ideas.value = await api.list(keyword.value.trim())
  } catch (e) {
    error.value = '连不上后端：' + e.message
  } finally {
    loading.value = false
  }
}

// 输入停下来再查，不要每敲一个字就发一次请求
let timer = null
function search() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}

async function create() {
  if (!form.title.trim()) {
    error.value = '标题不能为空'
    return
  }
  if (!form.project_id.trim()) {
    error.value = '项目编号不能为空'
    return
  }
  try {
    await api.create({ ...form, tags: form.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean) })
    Object.assign(form, { title: '', summary: '', tags: '', premise: '', stage: '现在做' })
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function patch(idea, changes) {
  try {
    Object.assign(idea, await api.update(idea.idea_id, changes))
  } catch (e) {
    error.value = e.message
    await load()
  }
}

async function remove(idea) {
  if (!confirm(`删除「${idea.title}」？它的出处和关系也会一起删掉`)) return
  try {
    await api.remove(idea.idea_id)
    await load()
  } catch (e) {
    error.value = e.message
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

    <form class="card create" @submit.prevent="create">
      <div class="row two">
        <input v-model="form.project_id" placeholder="项目编号" />
        <select v-model="form.stage">
          <option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option>
        </select>
      </div>
      <input v-model="form.title" placeholder="想法标题（必填）" maxlength="200" />
      <input v-model="form.summary" placeholder="一句话说明" />
      <div class="row">
        <input v-model="form.tags" placeholder="标签，逗号分隔" />
        <input v-model="form.premise" placeholder="适用条件：什么前提下才成立" />
      </div>
      <button type="submit">记下来</button>
    </form>

    <div class="search">
      <input v-model="keyword" placeholder="搜索标题、说明、标签、适用条件" @input="search" />
      <button type="button" class="plain" @click="load">刷新</button>
    </div>

    <p v-if="loading" class="hint">加载中…</p>
    <p v-else-if="!ideas.length" class="hint">还没有想法，在上面记一条试试。</p>

    <ul class="list">
      <li v-for="idea in ideas" :key="idea.idea_id" class="card idea">
        <div class="idea-head">
          <RouterLink :to="'/ideas/' + idea.idea_id" class="title">{{ idea.title }}</RouterLink>
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

        <p v-if="idea.sources.length" class="sources">来源：{{ idea.sources.join('、') }}</p>

        <div class="idea-foot">
          <select :value="idea.stage" @change="patch(idea, { stage: $event.target.value })">
            <option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option>
          </select>
          <button type="button" class="danger" @click="remove(idea)">删除</button>
        </div>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.head h1 { margin: 0 0 4px; font-size: 24px; }
.head p { margin: 0 0 20px; color: #6b7280; }

.create { display: grid; gap: 10px; margin-bottom: 16px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.row.two { grid-template-columns: 1fr 120px; }

.search { display: flex; gap: 8px; margin: 20px 0 12px; }
.search input { flex: 1; }

.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.idea-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.title { font-size: 17px; font-weight: 600; color: #1f2328; text-decoration: none; }
.title:hover { color: #1f6feb; }

.summary { margin: 6px 0 0; }
.premise { margin: 6px 0 0; color: #92400e; }
.sources { margin: 6px 0 0; color: #6b7280; font-size: 13px; }

.idea-foot { margin-top: 12px; display: flex; gap: 8px; align-items: center; }
</style>
