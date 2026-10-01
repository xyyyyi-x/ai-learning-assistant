<script setup>
const props = defineProps({
  task: {
    type: Object,
    required: true
  },
  updating: {
    type: Boolean,
    default: false
  },
  deleting: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(["toggle-completed", "remove-task"])

function requestToggle() {
  emit("toggle-completed", props.task.id)
}

function requestRemove() {
  emit("remove-task", props.task.id)
}

function priorityText(priority) {
  if (priority === 1) {
    return "普通"
  } else if (priority === 2) {
    return "重要"
  } else if (priority === 3) {
    return "紧急"
  }
  return "未知"
}
</script>

<template>
  <li>
    <button
      type="button"
      @click="requestToggle"
      :disabled="updating || deleting"
    >
      {{ updating ? "更新中……" : (task.completed ? "取消完成" : "标记完成") }}
    </button>

    <span>{{ task.title }} · {{ priorityText(task.priority) }}</span>
    <span>{{ task.completed ? "已完成" : "未完成" }}</span>

    <button
      type="button"
      @click="requestRemove"
      :disabled="deleting || updating"
    >
      {{ deleting ? "删除中……" : "删除" }}
    </button>
  </li>
</template>
