<template>
  <div class="layout">
    <ContainerSidebar
      :selected="selectedId"
      @select="onSelect"
      @home="onHome"
      @select-group="onSelectGroup"
    />
    <DashboardView v-if="!selectedContainer && !selectedGroup" @select="onSelect" />
    <GroupedLogPane v-else-if="selectedGroup" :group="selectedGroup" />
    <LogPane v-else :container="selectedContainer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ContainerSidebar from './ContainerSidebar.vue'
import LogPane from './LogPane.vue'
import GroupedLogPane from './GroupedLogPane.vue'
import DashboardView from './DashboardView.vue'

const selectedId = ref(null)
const selectedContainer = ref(null)
const selectedGroup = ref(null)

function onSelect(container) {
  selectedId.value = container?.container_id ?? null
  selectedContainer.value = container ?? null
  selectedGroup.value = null
}

function onSelectGroup(group) {
  selectedGroup.value = group
  selectedContainer.value = null
  selectedId.value = null
}

function onHome() {
  selectedId.value = null
  selectedContainer.value = null
  selectedGroup.value = null
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
</style>
