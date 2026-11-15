<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const stages = ['现在做', '以后再说', '已放弃']
const types = ['重复', '互补', '冲突']

const idea = ref(null)
const sources = ref([])
const relations = ref([])
const others = ref([])
const error = ref('')
const editing = ref(false)
const form = reactive({ title: '', summary: '', tags: '', premise: '' })
const target = ref('')
const type = ref('冲突')

async function load() {
  try {
    idea.value = await api.get(route.params.id)
    sources.value = await api.sources(route.params.id)
    relations.value = await api.relations(route.params.id)
  } catch (e) {
    error.value = e.message
  }
}

function startEdit() {
  Object.assign(form, {
    title: idea.value.title,
    summary: idea.value.summary || '',
    tags: (idea.value.tags || []).join(','),
    premise: idea.value.premise || '',
  })
  editing.value = true
}

async function save() {
  try {
    idea.value = await api.update(idea.value.idea_id, {
      ...form,
      tags: form.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean),
    })
    editing.value = false
  } catch (e) {
    error.value = e.message
  }
}

async function patch(changes) {
  try {
    idea.value = await api.update(idea.value.idea_id, changes)
  } catch (e) {
    error.value = e.message
  }
}

async function removeIdea() {
  if (!confirm(`删除「${idea.value.title}」？它的出处和关系也会一起删掉`)) return
  try {
    await api.remove(idea.value.idea_id)
    router.push('/ideas')
  } catch (e) {
    error.value = e.message
  }
}

async function removeSource(source) {
  try {
    await api.removeSource(idea.value.idea_id, source.message_id)
    sources.value = await api.sources(idea.value.idea_id)
  } catch (e) {
    error.value = e.message
  }
}

async function addRelation() {
  if (!target.value) {
    error.value = '先选一张卡片'
    return
  }
  try {
    await api.relate({ from_idea_id: idea.value.idea_id, to_idea_id: target.value, relation_type: type.value })
    target.value = ''
    relations.value = await api.relations(idea.value.idea_id)
  } catch (e) {
    error.value = e.message
  }
}

async function setRelation(rel, status) {
  try {
    await api.setRelation(rel.relation_id, status)
    relations.value = await api.relations(idea.value.idea_id)
  } catch (e) {
    error.value = e.message
  }
}

// 模块 1 的会话页还没接上，先把原文显示出来
function backToQuote(source) {
  alert(`模块 1 的会话页还没接上，先看原文：\n\n${source.quote || '（这条出处没存原文）'}`)
}

onMounted(async () => {
  await load()
  try {
    const all = await api.list('')
    others.value = all.filter((item) => item.idea_id !== route.params.id)
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <main class="page">
    <RouterLink to="/ideas">← 返回列表</RouterLink>
    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="idea">
      <div class="head">
        <h1>{{ idea.title }}</h1>
        <button type="button" class="star" :class="{ on: idea.favorite }"
                @click="patch({ favorite: !idea.favorite })">
          {{ idea.favorite ? '★' : '☆' }}
        </button>
      </div>

      <template v-if="!editing">
        <p>{{ idea.summary || '（还没有说明）' }}</p>
        <p class="premise">前提：{{ idea.premise || '未填' }}</p>
        <p v-if="idea.tags.length" class="tags">
          <span v-for="tag in idea.tags" :key="tag">{{ tag }}</span>
        </p>
        <div class="bar">
          <select :value="idea.stage" @change="patch({ stage: $event.target.value })">
            <option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option>
          </select>
          <button type="button" class="plain" @click="startEdit">编辑</button>
          <button type="button" class="danger" @click="removeIdea">删除</button>
        </div>
      </template>

      <form v-else class="card edit" @submit.prevent="save">
        <input v-model="form.title" placeholder="标题" maxlength="200" />
        <input v-model="form.summary" placeholder="一句话说明" />
        <input v-model="form.tags" placeholder="标签，逗号分隔" />
        <input v-model="form.premise" placeholder="适用条件" />
        <div class="bar">
          <button type="submit">保存更改</button>
          <button type="button" class="plain" @click="editing = false">取消</button>
        </div>
      </form>

      <h2>出处</h2>
      <p v-if="!sources.length" class="hint">暂无出处。</p>
      <ul class="list">
        <li v-for="source in sources" :key="source.message_id" class="card">
          <div class="row">
            <strong>{{ source.message_id }}</strong>
            <span v-if="source.source_ref" class="hint">{{ source.source_ref }}</span>
          </div>
          <p v-if="source.quote" class="quote">“{{ source.quote }}”</p>
          <div class="bar">
            <button type="button" class="plain" @click="backToQuote(source)">回到原话</button>
            <button type="button" class="danger" @click="removeSource(source)">移除出处</button>
          </div>
        </li>
      </ul>

      <h2>关联卡片</h2>
      <p v-if="!relations.length" class="hint">还没有关联。</p>
      <ul class="list">
        <li v-for="rel in relations" :key="rel.relation_id" class="card"
            :class="{ warn: rel.status === '待确认' }">
          <div class="row">
            <RouterLink :to="'/ideas/' + (rel.from_idea_id === idea.idea_id ? rel.to_idea_id : rel.from_idea_id)">
              {{ rel.from_idea_id === idea.idea_id ? rel.to_title : rel.from_title }}
            </RouterLink>
            <span>{{ rel.relation_type }} · {{ rel.status }}</span>
          </div>
          <div v-if="rel.status === '待确认'" class="bar">
            <button type="button" @click="setRelation(rel, '已确认')">确认</button>
            <button type="button" class="plain" @click="setRelation(rel, '已拒绝')">撤销</button>
          </div>
        </li>
      </ul>

      <div class="bar">
        <select v-model="target">
          <option value="">选另一张卡片</option>
          <option v-for="other in others" :key="other.idea_id" :value="other.idea_id">{{ other.title }}</option>
        </select>
        <select v-model="type">
          <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
        </select>
        <button type="button" class="plain" @click="addRelation">标记关系</button>
      </div>
    </template>
  </main>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.head h1 { margin: 12px 0; font-size: 22px; }

.premise { color: #92400e; }
.bar { display: flex; gap: 8px; align-items: center; margin: 12px 0; flex-wrap: wrap; }
.row { display: flex; gap: 10px; align-items: center; justify-content: space-between; }

h2 { font-size: 16px; margin: 24px 0 8px; }
.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.quote { margin: 8px 0 0; color: #374151; background: #f9fafb; padding: 8px 10px; border-radius: 8px; }

.warn { border-color: #fcd34d; background: #fffbeb; }
.edit { display: grid; gap: 10px; }
</style>
