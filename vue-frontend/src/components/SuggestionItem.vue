<script setup>
const props = defineProps({
  suggestion: {
    type: Object,
    required: true
  },
  saving: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  "update-title",
  "update-priority",
  "remove-suggestion",
  "save-suggestion"
])

function onInput(event) {
  emit("update-title", props.suggestion.id, event.target.value)
}

function onPriorityChange(event) {
  emit("update-priority", props.suggestion.id, Number(event.target.value))
}

function requestRemove() {
  emit("remove-suggestion", props.suggestion.id)
}

function requestSave() {
  emit("save-suggestion", props.suggestion.id)
}
</script>

<template>
  <div class="suggestion-item">
    <input
      type="text"
      class="suggestion-title"
      maxlength="50"
      :value="suggestion.title"
      :disabled="saving"
      @input="onInput"
    >
    <select
      class="suggestion-priority"
      :value="suggestion.priority"
      :disabled="saving"
      @change="onPriorityChange"
    >
      <option :value="1">普通</option>
      <option :value="2">重要</option>
      <option :value="3">紧急</option>
    </select>
    <button type="button" :disabled="saving" @click="requestSave">
      {{ saving ? "保存中……" : "保存为任务" }}
    </button>
    <button type="button" :disabled="saving" @click="requestRemove">移除</button>
  </div>
</template>
