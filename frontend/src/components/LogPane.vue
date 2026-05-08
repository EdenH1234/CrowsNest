<template>
  <div class="log-pane">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="container-title">
          <span class="status-dot" :class="container?.status" />
          {{ container?.container_name ?? 'Select a container' }}
        </span>
        <Tag v-if="container?.compose_service" :value="container.compose_service" severity="secondary" />
      </div>
      <div class="toolbar-right">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Search logs..."
            size="small"
            @keyup.enter="runSearch"
            @keyup.escape="clearSearch"
          />
        </IconField>
        <Select
          v-model="timeRange"
          :options="TIME_RANGES"
          option-label="label"
          size="small"
          @change="loadHistory"
          style="width: 130px"
        />
        <Button
          :icon="autoScroll ? 'pi pi-arrow-down' : 'pi pi-lock'"
          :severity="autoScroll ? 'primary' : 'secondary'"
          text
          rounded
          size="small"
          v-tooltip.bottom="'Auto-scroll'"
          @click="autoScroll = !autoScroll"
        />
        <Button
          icon="pi pi-trash"
          text
          rounded
          size="small"
          severity="danger"
          v-tooltip.bottom="'Clear view'"
          @click="clearLogs"
        />
      </div>
    </div>

    <!-- Log output -->
    <div ref="logEl" class="log-output" @scroll="onScroll">
      <div v-if="!container" class="placeholder">
        <i class="pi pi-arrow-left" />
        Select a container to view logs
      </div>

      <div v-else-if="lines.length === 0 && !loading" class="placeholder">
        No logs found
      </div>

      <template v-for="line in lines" :key="line.id ?? line._key">
        <div v-if="line.stream === 'system'" class="log-divider">
          <span class="divider-line" />
          <span class="divider-label">{{ line.message }}</span>
          <span class="divider-line" />
        </div>
        <div v-else class="log-line" :class="line.stream">
          <span class="ts">{{ formatTs(line.timestamp) }}</span>
          <span class="msg">{{ line.message }}</span>
        </div>
      </template>

      <div v-if="loading" class="placeholder">
        <i class="pi pi-spin pi-spinner" /> Loading...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import api from '../api.js'

const props = defineProps({ container: Object })

const TIME_RANGES = [
  { label: 'Last 30 min', seconds: 1800 },
  { label: 'Last 1 hour', seconds: 3600 },
  { label: 'Last 6 hours', seconds: 21600 },
  { label: 'Last 24 hours', seconds: 86400 },
  { label: 'Last 7 days', seconds: 604800 },
  { label: 'All time', seconds: null },
]

const lines = ref([])
const loading = ref(false)
const autoScroll = ref(true)
const searchQuery = ref('')
const timeRange = ref(TIME_RANGES[1])
const logEl = ref(null)
let ws = null
let keyCounter = 0

function formatTs(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('en-GB', { hour12: false }) +
    '.' + String(d.getMilliseconds()).padStart(3, '0')
}

function scrollToBottom() {
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  })
}

function onScroll() {
  const el = logEl.value
  if (!el) return
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  autoScroll.value = atBottom
}

async function loadHistory() {
  if (!props.container) return
  loading.value = true
  try {
    const since = timeRange.value.seconds
      ? Date.now() / 1000 - timeRange.value.seconds
      : undefined
    const { data } = await api.get('/logs', {
      params: {
        container_name: props.container.container_name,
        since,
        q: searchQuery.value || undefined,
        limit: 1000,
      },
    })
    lines.value = data
    if (autoScroll.value) scrollToBottom()
  } finally {
    loading.value = false
  }
}

async function runSearch() {
  await loadHistory()
}

function clearSearch() {
  searchQuery.value = ''
  loadHistory()
}

function clearLogs() {
  lines.value = []
}

function connectWs() {
  if (ws) ws.close()
  if (!props.container) return
  const token = localStorage.getItem('token')
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(
    `${proto}://${location.host}/ws/logs/${encodeURIComponent(props.container.container_name)}?token=${token}`
  )
  ws.onmessage = (e) => {
    const entry = JSON.parse(e.data)
    if (entry.type === 'ping') return
    entry._key = ++keyCounter
    lines.value.push(entry)
    // cap in-memory lines at 5000
    if (lines.value.length > 5000) lines.value.splice(0, lines.value.length - 5000)
    if (autoScroll.value) scrollToBottom()
  }
  ws.onclose = () => {}
}

watch(
  () => props.container,
  async (c) => {
    lines.value = []
    searchQuery.value = ''
    if (ws) { ws.close(); ws = null }
    if (!c) return
    await loadHistory()
    connectWs()
  }
)

onUnmounted(() => { if (ws) ws.close() })
</script>

<style scoped>
.log-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0f1117;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #1e2235;
  background: #13151f;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.container-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  font-size: 0.9rem;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-dot.running { background: #22c55e; }
.status-dot.stopped { background: #4a5568; }

.log-output {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.78rem;
  line-height: 1.6;
}
.log-line {
  display: flex;
  gap: 0.75rem;
  padding: 0 1rem;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-line:hover {
  background: rgba(255,255,255,0.03);
}
.log-line.stderr .msg {
  color: #f87171;
}
.ts {
  flex-shrink: 0;
  color: #4a5568;
  user-select: none;
  font-size: 0.72rem;
  padding-top: 1px;
}
.msg {
  color: #cbd5e1;
}
.log-divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 1rem;
  color: #f59e0b;
  font-size: 0.72rem;
  font-family: system-ui, sans-serif;
  letter-spacing: 0.05em;
}
.divider-line {
  flex: 1;
  height: 1px;
  background: #f59e0b44;
}
.divider-label {
  white-space: nowrap;
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: 100%;
  color: #4a5568;
  font-size: 0.9rem;
}
</style>
