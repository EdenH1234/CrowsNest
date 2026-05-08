<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <CrowsNestLogo :size="24" />
      <span>CrowsNest</span>
      <Button
        icon="pi pi-sign-out"
        text
        rounded
        size="small"
        class="logout-btn"
        @click="logout"
        v-tooltip.right="'Sign out'"
      />
    </div>

    <div class="search-box">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="filter" placeholder="Filter..." size="small" fluid />
      </IconField>
    </div>

    <div v-if="grouped.length === 0" class="empty-state">
      <i class="pi pi-spin pi-spinner" />
      <span>No containers found</span>
    </div>

    <div v-for="group in grouped" :key="group.project" class="group">
      <div class="group-label">
        <i class="pi pi-folder" />
        {{ group.project || 'standalone' }}
      </div>
      <div
        v-for="c in group.containers"
        :key="c.container_id"
        class="container-item"
        :class="{ active: selected === c.container_id }"
        @click="$emit('select', c)"
      >
        <span class="status-dot" :class="c.status" />
        <span class="name" :title="c.container_name">{{ c.container_name }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import CrowsNestLogo from './CrowsNestLogo.vue'
import api from '../api.js'

const props = defineProps({ selected: String })
defineEmits(['select'])

const router = useRouter()
const containers = ref([])
const filter = ref('')
let pollTimer = null

const grouped = computed(() => {
  const q = filter.value.toLowerCase()
  const filtered = containers.value.filter((c) =>
    c.container_name.toLowerCase().includes(q)
  )
  const map = new Map()
  for (const c of filtered) {
    const key = c.compose_project || ''
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(c)
  }
  return [...map.entries()].map(([project, cs]) => ({ project, containers: cs }))
})

async function fetchContainers() {
  try {
    const { data } = await api.get('/containers')
    containers.value = data
  } catch {}
}

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}

onMounted(() => {
  fetchContainers()
  pollTimer = setInterval(fetchContainers, 5000)
})

onUnmounted(() => clearInterval(pollTimer))
</script>

<style scoped>
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #13151f;
  border-right: 1px solid #1e2235;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  font-weight: 600;
  font-size: 0.9rem;
  color: #94a3b8;
  border-bottom: 1px solid #1e2235;
}
.logout-btn {
  margin-left: auto;
}
.search-box {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #1e2235;
}
.group {
  margin-top: 0.25rem;
}
.group-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #4a5568;
}
.container-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.75rem 0.45rem 1rem;
  cursor: pointer;
  border-radius: 4px;
  margin: 0 0.3rem;
  transition: background 0.1s;
}
.container-item:hover {
  background: #1e2235;
}
.container-item.active {
  background: #252a40;
  color: #7c9ef8;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.running { background: #22c55e; }
.status-dot.stopped { background: #4a5568; }
.name {
  font-size: 0.82rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: #4a5568;
  font-size: 0.85rem;
}
</style>
