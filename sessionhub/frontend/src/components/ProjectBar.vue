<script setup>
import { ref } from 'vue'
import { createProject } from '../api.js'
import { normalizeError } from '../lib/errors.js'
import { copyText } from '../lib/clipboard.js'

const props = defineProps({
  projects: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'created', 'refresh'])

const newName = ref('')
const creating = ref(false)
const createError = ref('')
const copied = ref(false)

function selectProject(event) {
  emit('update:modelValue', event.target.value)
}

async function submitCreate() {
  const name = newName.value.trim()
  if (!name || creating.value) return
  creating.value = true
  createError.value = ''
  try {
    const created = await createProject(name)
    newName.value = ''
    emit('created', created)
  } catch (err) {
    if (err.kind === 'network') {
      createError.value = err.message
    } else {
      const n = normalizeError(err.status, err.payload)
      createError.value =
        n.kind === 'message'
          ? n.message
          : '创建失败（HTTP ' + err.status + '）'
    }
  } finally {
    creating.value = false
  }
}

async function copyProjectId() {
  if (await copyText(props.modelValue)) {
    copied.value = true
    setTimeout(() => (copied.value = false), 1200)
  }
}
</script>

<template>
  <section class="panel project-panel">
    <div class="panel-heading">
      <div>
        <h2>项目</h2>
        <p>导入前必须先有项目（校验规则第 1 条：项目不存在返回 404）。</p>
      </div>
      <span class="count-pill">{{ projects.length }}</span>
    </div>

    <div class="form-grid">
      <label class="field">
        <span>当前项目</span>
        <select :value="modelValue" :disabled="!projects.length" @change="selectProject">
          <option v-if="!projects.length" value="">（还没有项目，先在右侧创建）</option>
          <option v-for="p in projects" :key="p.project_id" :value="p.project_id">
            {{ p.name }}
          </option>
        </select>
      </label>
      <label class="field">
        <span>新建项目</span>
        <div class="viewer-controls" style="margin-top: 0">
          <input
            v-model="newName"
            placeholder="项目名称，如：IdeaFlow 联调演示"
            @keyup.enter="submitCreate"
          />
          <button class="primary-button" :disabled="creating || !newName.trim()" @click="submitCreate">
            {{ creating ? '创建中…' : '创建' }}
          </button>
        </div>
      </label>
    </div>

    <div v-if="modelValue" class="id-line">
      <span>project_id</span>
      <code class="mono">{{ modelValue }}</code>
      <button class="copy-btn" :class="{ copied }" @click="copyProjectId">
        {{ copied ? '已复制' : '复制' }}
      </button>
    </div>

    <div v-if="createError" class="alert error" style="margin-top: 12px; margin-bottom: 0">
      {{ createError }}
    </div>
  </section>
</template>
