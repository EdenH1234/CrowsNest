<template>
  <div class="layout">
    <ContainerSidebar
      :selected="selectedId"
      @select="onSelect"
      @home="onHome"
    />
    <DashboardView v-if="!selectedContainer" @select="onSelect" />
    <LogPane v-else :container="selectedContainer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ContainerSidebar from './ContainerSidebar.vue'
import LogPane from './LogPane.vue'
import DashboardView from './DashboardView.vue'

const selectedId = ref(null)
const selectedContainer = ref(null)

function onSelect(container) {
  selectedId.value = container?.container_id ?? null
  selectedContainer.value = container ?? null
}

function onHome() {
  selectedId.value = null
  selectedContainer.value = null
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
</style>
