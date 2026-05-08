<template>
  <div class="layout">
    <ContainerSidebar
      :selected="selectedId"
      @select="onSelect"
    />
    <LogPane :container="selectedContainer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ContainerSidebar from './ContainerSidebar.vue'
import LogPane from './LogPane.vue'

const selectedId = ref(null)
const selectedContainer = ref(null)

function onSelect(container) {
  selectedId.value = container.container_id
  selectedContainer.value = container
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
</style>
