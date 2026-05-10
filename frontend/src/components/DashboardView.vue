<template>
  <div class="dashboard">
    <div class="dash-header">
      <div class="dash-title">
        <CrowsNestLogo :size="20" />
        <span>Overview</span>
      </div>
      <span class="dash-summary">{{ runningCount }} running · {{ stoppedCount }} stopped</span>
    </div>

    <div class="dash-body">
      <div v-if="groups.length === 0" class="empty-state">
        <i class="pi pi-spin pi-spinner" />
        <span>No containers found</span>
      </div>

      <div v-for="group in groups" :key="group.project ?? '__standalone__'" class="group-section">
        <div class="group-title">
          <i :class="group.project ? 'pi pi-folder' : 'pi pi-box'" />
          <span>{{ group.project || 'standalone' }}</span>
          <span class="group-count">{{ group.containers.length }}</span>
        </div>

        <div class="container-grid">
          <div
            v-for="c in group.containers"
            :key="c.container_id"
            class="container-card"
            :class="c.status"
            @click="$emit('select', c)"
          >
            <div class="card-top">
              <span class="status-dot" :class="c.status" />
              <span class="card-name" :title="c.container_name">{{ c.container_name }}</span>
            </div>

            <div v-if="c.compose_service && c.compose_service !== c.container_name" class="card-service">
              {{ c.compose_service }}
            </div>

            <div class="card-image" :title="c.image_tag">{{ c.image_tag || '—' }}</div>

            <template v-if="c.status === 'running'">
              <div class="card-uptime">
                <i class="pi pi-clock" />
                {{ formatUptime(stats[c.container_name]?.started_at) }}
              </div>

              <div v-if="stats[c.container_name]" class="card-stats">
                <div class="stat-row">
                  <span class="stat-label">CPU</span>
                  <div class="stat-bar">
                    <div
                      class="stat-fill cpu"
                      :style="{ width: clamp(stats[c.container_name].cpu_pct) + '%' }"
                      :class="cpuClass(stats[c.container_name].cpu_pct)"
                    />
                  </div>
                  <span class="stat-val">{{ stats[c.container_name].cpu_pct }}%</span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">MEM</span>
                  <div class="stat-bar">
                    <div
                      class="stat-fill mem"
                      :style="{ width: clamp(stats[c.container_name].mem_pct) + '%' }"
                      :class="memClass(stats[c.container_name].mem_pct)"
                    />
                  </div>
                  <span class="stat-val">{{ formatMem(stats[c.container_name].mem_mb) }}</span>
                </div>
              </div>
              <div v-else class="card-stats-loading">
                <i class="pi pi-spin pi-spinner" />
              </div>
            </template>

            <div v-else class="card-stopped-label">stopped</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import CrowsNestLogo from './CrowsNestLogo.vue'
import api from '../api.js'

defineEmits(['select'])

const containers = ref([])
const stats = ref({})
let containerTimer = null
let statsTimer = null

const groups = computed(() => {
  const map = new Map()
  for (const c of containers.value) {
    const key = c.compose_project ?? '__standalone__'
    if (!map.has(key)) map.set(key, { project: c.compose_project ?? null, containers: [] })
    map.get(key).containers.push(c)
  }
  return [...map.values()]
})

const runningCount = computed(() => containers.value.filter(c => c.status === 'running').length)
const stoppedCount = computed(() => containers.value.filter(c => c.status === 'stopped').length)

function clamp(v) { return Math.min(Math.max(v, 0), 100) }

function cpuClass(pct) {
  if (pct >= 80) return 'danger'
  if (pct >= 50) return 'warn'
  return ''
}

function memClass(pct) {
  if (pct >= 90) return 'danger'
  if (pct >= 70) return 'warn'
  return ''
}

function formatUptime(startedAt) {
  if (!startedAt) return '—'
  const secs = Math.floor((Date.now() - new Date(startedAt)) / 1000)
  if (secs < 60) return 'Just started'
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
  return `${Math.floor(secs / 86400)}d ${Math.floor((secs % 86400) / 3600)}h`
}

function formatMem(mb) {
  if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB'
  return mb.toFixed(0) + ' MB'
}

async function fetchContainers() {
  try {
    const { data } = await api.get('/containers')
    containers.value = data
  } catch {}
}

async function fetchStats() {
  try {
    const { data } = await api.get('/containers/stats')
    const map = {}
    for (const s of data) map[s.container_name] = s
    stats.value = map
  } catch {}
}

onMounted(() => {
  fetchContainers()
  fetchStats()
  containerTimer = setInterval(fetchContainers, 5000)
  statsTimer = setInterval(fetchStats, 5000)
})

onUnmounted(() => {
  clearInterval(containerTimer)
  clearInterval(statsTimer)
})
</script>

<style scoped>
.dashboard {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-page);
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.dash-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.dash-summary {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.dash-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.empty-state {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  padding: 4rem;
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Group */
.group-section {}

.group-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 0.6rem;
  font-weight: 600;
}

.group-count {
  background: var(--bg-hover);
  border-radius: 10px;
  padding: 0 0.4rem;
  font-size: 0.65rem;
  color: var(--text-muted);
}

/* Grid */
.container-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 0.75rem;
}

/* Card */
.container-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.9rem 1rem;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.container-card:hover {
  border-color: var(--border-2);
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.container-card.stopped {
  opacity: 0.55;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.1rem;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.running { background: #22c55e; }
.status-dot.stopped { background: #94a3b8; }

.card-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-service {
  font-size: 0.7rem;
  color: var(--text-muted);
  padding-left: 1rem;
}

.card-image {
  font-size: 0.68rem;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 0.1rem;
}

.card-uptime {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.card-uptime .pi-clock {
  font-size: 0.65rem;
}

/* Stats */
.card-stats {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-top: 0.35rem;
}

.card-stats-loading {
  margin-top: 0.5rem;
  color: var(--text-muted);
  font-size: 0.7rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.card-stopped-label {
  font-size: 0.68rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.stat-label {
  font-size: 0.62rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  width: 2rem;
  flex-shrink: 0;
}

.stat-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-hover);
  border-radius: 2px;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s ease;
}

.stat-fill.cpu       { background: #3b82f6; }
.stat-fill.cpu.warn  { background: #f59e0b; }
.stat-fill.cpu.danger{ background: #ef4444; }
.stat-fill.mem       { background: #8b5cf6; }
.stat-fill.mem.warn  { background: #f59e0b; }
.stat-fill.mem.danger{ background: #ef4444; }

.stat-val {
  font-size: 0.68rem;
  color: var(--text-secondary);
  width: 3.5rem;
  text-align: right;
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}
</style>
