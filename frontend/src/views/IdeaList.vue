<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const ideas = ref([])
const keyword = ref('')
const error = ref('')

async function load() {
  try {
    ideas.value = await api.list(keyword.value)
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>想法卡片</h1>
    <!-- 新建表单放这里 -->
    <input v-model="keyword" @input="load" placeholder="搜标题、说明、标签、前提" />
    <p v-if="error">{{ error }}</p>
    <ul>
      <li v-for="idea in ideas" :key="idea.idea_id">
        <RouterLink :to="'/ideas/' + idea.idea_id">{{ idea.title }}</RouterLink>
        <span>{{ idea.stage }}</span>
        <!-- 星标、改阶段、删除 -->
      </li>
    </ul>
    <p v-if="!ideas.length">还没有卡片</p>
  </div>
</template>

<style scoped>
.page { max-width: 720px; margin: 30px auto; }
li { padding: 10px 0; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
</style>
