<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const idea = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    idea.value = await api.get(route.params.id)
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <div class="page">
    <RouterLink to="/ideas">返回列表</RouterLink>
    <p v-if="error">{{ error }}</p>
    <template v-if="idea">
      <h1>{{ idea.title }}</h1>
      <p>{{ idea.summary }}</p>
      <p>前提：{{ idea.premise || '未填' }}</p>
      <p>标签：{{ idea.tags || '无' }}</p>
      <p>阶段：{{ idea.stage }}</p>
      <p>更新：{{ idea.updated_at }}</p>
      <!-- 出处和关联卡片：接口做好后在这里加 -->
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 720px; margin: 30px auto; }
</style>
