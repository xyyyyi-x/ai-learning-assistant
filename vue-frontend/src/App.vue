<script setup>
import { computed, onMounted, ref } from "vue"
import TaskItem from "./components/TaskItem.vue"
import SuggestionItem from "./components/SuggestionItem.vue"

const taskTitle = ref("")
const newPriority = ref(1)
const statusFilter = ref("all")
const submitting = ref(false)
const formMessage = ref("")
const updatingTaskIds = ref([])
const deletingTaskIds = ref([])
const taskMessage = ref("")

const aiGoal = ref("")
const suggestions = ref([])
const generating = ref(false)
const aiMessage = ref("")
const savingSuggestionIds = ref([])

let nextSuggestionId = 1

const tasks = ref([])

const loading = ref(false)
const errorMessage = ref("")

const completedCount = computed(() => {
  return tasks.value.filter(task => task.completed).length
})

const visibleTasks = computed(() => {
  if (statusFilter.value === "active") {
    return tasks.value.filter(task => !task.completed)
  }
  if (statusFilter.value === "completed") {
    return tasks.value.filter(task => task.completed)
  }
  return tasks.value
})

async function loadTasks() {
  loading.value = true
  errorMessage.value = ""

  try {
    const response = await fetch("/tasks")

    if (!response.ok) {
      throw new Error(`读取任务失败：${response.status}`)
    }

    tasks.value = await response.json()
    return true
  } catch (error) {
    errorMessage.value = error.message
    return false
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)

async function addTask() {
  const title = taskTitle.value.trim()
  if (!title) {
    formMessage.value = "请输入任务标题"
    return
  }

  submitting.value = true
  formMessage.value = ""

  try {
    const response = await fetch("/tasks", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        title: title,
        priority: newPriority.value
      })
    })

    if (!response.ok) {
      throw new Error(`添加任务失败：${response.status}`)
    }

    const created = await response.json()
    tasks.value.push(created)

    taskTitle.value = ""
    newPriority.value = 1
  } catch (error) {
    formMessage.value = error.message
  } finally {
    submitting.value = false
  }
}

async function toggleCompleted(taskId) {
  if (updatingTaskIds.value.includes(taskId)) {
    return
  }

  const task = tasks.value.find(item => item.id === taskId)
  if (!task) {
    return
  }

  const newCompleted = !task.completed

  updatingTaskIds.value.push(taskId)
  taskMessage.value = ""

  try {
    const response = await fetch(`/tasks/${taskId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ completed: newCompleted })
    })

    if (!response.ok) {
      throw new Error(`更新任务失败：${response.status}`)
    }

    const updated = await response.json()
    const index = tasks.value.findIndex(item => item.id === taskId)

    if (index !== -1) {
      tasks.value[index] = updated
    }
  } catch (error) {
    taskMessage.value = error.message
  } finally {
    updatingTaskIds.value = updatingTaskIds.value.filter(id => id !== taskId)
  }
}

async function removeTask(taskId) {
  if (deletingTaskIds.value.includes(taskId)) {
    return
  }

  const task = tasks.value.find(item => item.id === taskId)
  if (!task) {
    return
  }

  if (!window.confirm(`确定删除任务"${task.title}"吗？`)) {
    return
  }

  deletingTaskIds.value.push(taskId)
  taskMessage.value = ""

  try {
    const response = await fetch(`/tasks/${taskId}`, {
      method: "DELETE"
    })

    if (!response.ok) {
      throw new Error(`删除任务失败：${response.status}`)
    }

    tasks.value = tasks.value.filter(item => item.id !== taskId)
  } catch (error) {
    taskMessage.value = error.message
  } finally {
    deletingTaskIds.value = deletingTaskIds.value.filter(id => id !== taskId)
  }
}

async function generateSuggestions() {
  if (generating.value || savingSuggestionIds.value.length > 0) {
    return
  }

  const goal = aiGoal.value.trim()
  if (!goal) {
    aiMessage.value = "请输入学习目标"
    return
  }

  generating.value = true
  aiMessage.value = ""
  suggestions.value = []

  try {
    const response = await fetch("/ai/suggestions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ goal: goal })
    })

    const data = await response.json()

    if (!response.ok) {
      const detail = typeof data.detail === "string"
        ? data.detail
        : `生成建议失败：HTTP ${response.status}`
      throw new Error(detail)
    }

    if (
      !Array.isArray(data.suggestions) ||
      data.suggestions.length === 0 ||
      !data.suggestions.every(
        item => typeof item === "string" && item.trim().length > 0
      )
    ) {
      throw new Error("服务器没有返回有效建议")
    }

    suggestions.value = data.suggestions.map(title => ({
      id: nextSuggestionId++,
      title: title,
      priority: 1
    }))

    aiMessage.value = "建议已生成"
  } catch (error) {
    aiMessage.value = error.message
  } finally {
    generating.value = false
  }
}

function updateSuggestionTitle(id, newTitle) {
  const suggestion = suggestions.value.find(item => item.id === id)

  if (suggestion) {
    suggestion.title = newTitle
  }
}

function updateSuggestionPriority(id, newPriority) {
  const suggestion = suggestions.value.find(item => item.id === id)

  if (suggestion) {
    suggestion.priority = newPriority
  }
}

function removeSuggestion(id) {
  suggestions.value = suggestions.value.filter(item => item.id !== id)

  if (suggestions.value.length === 0) {
    aiMessage.value = "候选任务已全部移除"
  }
}

async function saveSuggestion(id) {
  if (savingSuggestionIds.value.includes(id)) {
    return
  }

  const suggestion = suggestions.value.find(item => item.id === id)
  if (!suggestion) {
    return
  }

  const title = suggestion.title.trim()
  if (title.length < 1 || title.length > 50) {
    aiMessage.value = "任务标题必须为1到50个字符"
    return
  }

  savingSuggestionIds.value.push(id)
  aiMessage.value = ""

  try {
    const response = await fetch("/tasks", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        title: title,
        priority: suggestion.priority
      })
    })

    if (!response.ok) {
      throw new Error(`保存任务失败：HTTP ${response.status}`)
    }

    suggestions.value = suggestions.value.filter(item => item.id !== id)

    const refreshed = await loadTasks()

    if (refreshed) {
      aiMessage.value = "任务已保存"
    } else {
      aiMessage.value = "任务已保存，但列表刷新失败，请刷新页面查看"
    }
  } catch (error) {
    aiMessage.value = error.message
  } finally {
    savingSuggestionIds.value =
      savingSuggestionIds.value.filter(sid => sid !== id)
  }
}
</script>

<template>
  <main>
    <h1>Vue任务练习</h1>

    <form @submit.prevent="addTask">
      <label for="task-title">任务标题</label>
      <input id="task-title" v-model="taskTitle" maxlength="50">

      <label for="task-priority">优先级</label>
      <select id="task-priority" v-model.number="newPriority">
        <option :value="1">普通</option>
        <option :value="2">重要</option>
        <option :value="3">紧急</option>
      </select>

      <button type="submit" :disabled="submitting">
        {{ submitting ? "添加中……" : "添加任务" }}
      </button>
    </form>

    <p>{{ formMessage }}</p>

    <label for="status-filter">显示状态</label>
    <select id="status-filter" v-model="statusFilter">
      <option value="all">全部</option>
      <option value="active">未完成</option>
      <option value="completed">已完成</option>
    </select>

    <section>
      <h2>AI学习建议</h2>

      <label for="ai-goal">学习目标</label>
      <input id="ai-goal" v-model="aiGoal" maxlength="200">

      <button
        type="button"
        :disabled="generating || savingSuggestionIds.length > 0"
        @click="generateSuggestions"
      >
        {{ generating ? "生成中……" : "生成建议" }}
      </button>

      <p data-testid="ai-message" aria-live="polite">
        {{ aiMessage }}
      </p>

      <div>
        <SuggestionItem
          v-for="suggestion in suggestions"
          :key="suggestion.id"
          :suggestion="suggestion"
          :saving="savingSuggestionIds.includes(suggestion.id)"
          @update-title="updateSuggestionTitle"
          @update-priority="updateSuggestionPriority"
          @remove-suggestion="removeSuggestion"
          @save-suggestion="saveSuggestion"
        />
      </div>
    </section>

    <p>共{{ tasks.length }}条，已完成{{ completedCount }}条</p>

    <p v-if="loading">正在加载任务……</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>

    <p>{{ taskMessage }}</p>

    <ul data-testid="task-list">
      <TaskItem
        v-for="task in visibleTasks"
        :key="task.id"
        :task="task"
        :updating="updatingTaskIds.includes(task.id)"
        :deleting="deletingTaskIds.includes(task.id)"
        @toggle-completed="toggleCompleted"
        @remove-task="removeTask"
      />
    </ul>
  </main>
</template>
