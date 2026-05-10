<template>
  <div class="log-pane">
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="group-title">
          <i class="pi pi-folder" />
          {{ group.project }}
        </span>
        <div class="legend">
          <span
            v-for="(c, i) in group.containers"
            :key="c.container_id"
            class="legend-pill"
            :style="pillStyle(i)"
          >
            {{ c.compose_service || c.container_name }}
          </span>
        </div>
      </div>
      <div class="toolbar-right">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Search logs..."
            size="small"
            @keyup.enter="loadHistory"
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
          text rounded size="small"
          v-tooltip.bottom="'Auto-scroll'"
          @click="autoScroll = !autoScroll"
        />
        <Button
          icon="pi pi-trash"
          text rounded size="small" severity="danger"
          v-tooltip.bottom="'Clear view'"
          @click="lines = []"
        />
      </div>
    </div>

    <div ref="logEl" class="log-output" @scroll="onScroll">
      <div v-if="lines.length === 0 && !loading" class="placeholder">No logs found</div>

      <template v-for="line in lines" :key="line._key">
        <div v-if="line.stream === 'system'" class="log-divider">
          <span class="divider-line" />
          <span class="divider-label">{{ line.container_name }} — {{ line.message }}</span>
          <span class="divider-line" />
        </div>
        <div v-else class="log-line" :class="line.stream">
          <span class="svc-tag" :style="tagStyle(line._svc_idx)" :title="line.container_name">
            {{ line._svc_name }}
          </span>
          <span class="ts">{{ formatTs(line.timestamp) }}</span>
          <span v-if="getStatusDot(line)" class="log-dot" :class="getStatusDot(line)" />
          <span v-else class="log-dot-gap" />

          <span v-if="line._parsed" class="msg json-msg" @click="toggleExpand(line)">
            <template v-if="isCrowsNestLog(line._parsed)">
              <span class="log-level" :class="line._parsed.level?.toLowerCase()">{{ line._parsed.level }}</span>
              <span class="log-logger">{{ line._parsed.logger }}</span>
              <span class="log-text">{{ line._parsed.message }}</span>
            </template>
            <template v-else>
              <span class="log-text">{{ jsonPreview(line._parsed) }}</span>
            </template>
            <span class="expand-toggle">{{ line._expanded ? '▾' : '▸' }}</span>
            <pre v-if="line._expanded" class="json-raw">{{ JSON.stringify(line._parsed, null, 2) }}</pre>
          </span>
          <span v-else class="msg">{{ line.message }}</span>
        </div>
      </template>

      <div v-if="loading" class="placeholder">
        <i class="pi pi-spin pi-spinner" /> Loading...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick, onUnmounted } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Select from 'primevue/select'
import api from '../api.js'

const props = defineProps({ group: Object })

const PALETTE = ['#3b82f6', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#ef4444', '#a78bfa']

const TIME_RANGES = [
  { label: 'Last 30 min',  seconds: 1800 },
  { label: 'Last 1 hour',  seconds: 3600 },
  { label: 'Last 6 hours', seconds: 21600 },
  { label: 'Last 24 hours',seconds: 86400 },
  { label: 'Last 7 days',  seconds: 604800 },
  { label: 'All time',     seconds: null },
]

const lines = ref([])
const loading = ref(false)
const autoScroll = ref(true)
const searchQuery = ref('')
const timeRange = ref(TIME_RANGES[1])
const logEl = ref(null)
let sockets = []
let keyCounter = 0

const svcMeta = computed(() => {
  const map = {}
  ;(props.group?.containers ?? []).forEach((c, i) => {
    map[c.container_name] = { idx: i, name: c.compose_service || c.container_name }
  })
  return map
})

function pillStyle(i) {
  const c = PALETTE[i % PALETTE.length]
  return { color: c, borderColor: c + '55', backgroundColor: c + '18' }
}

function tagStyle(idx) {
  if (idx < 0) return {}
  const c = PALETTE[idx % PALETTE.length]
  return { color: c, borderColor: c + '55', backgroundColor: c + '15' }
}

function formatTs(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('en-GB', { hour12: false }) +
    '.' + String(d.getMilliseconds()).padStart(3, '0')
}

function enrichLine(line) {
  try {
    const parsed = JSON.parse(line.message)
    line._parsed = (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : null
  } catch { line._parsed = null }
  line._expanded = false
  const meta = svcMeta.value[line.container_name] ?? {}
  line._svc_idx = meta.idx ?? -1
  line._svc_name = meta.name ?? line.container_name
  return line
}

function isCrowsNestLog(p) {
  return 'level' in p && 'logger' in p && 'message' in p
}

function jsonPreview(obj) {
  const parts = []
  for (const [k, v] of Object.entries(obj)) {
    if (parts.length >= 5) { parts.push('…'); break }
    if (v === null) parts.push(`${k}: null`)
    else if (typeof v === 'object') parts.push(`${k}: {…}`)
    else parts.push(`${k}: ${v}`)
  }
  return parts.join('   ')
}

function toggleExpand(line) {
  if (window.getSelection().toString()) return
  line._expanded = !line._expanded
}

function getStatusDot(line) {
  if (line.stream === 'stderr') return 'red'
  const p = line._parsed
  if (p) {
    if (p.level === 'ERROR') return 'red'
    if (p.level === 'WARNING') return 'amber'
    if (p.level === 'INFO' || p.level === 'DEBUG') return 'green'
    const code = p.status ?? p.status_code ?? p.statusCode
    if (typeof code === 'number') {
      if (code >= 200 && code < 300) return 'green'
      if (code >= 400) return 'red'
    }
    return null
  }
  const match = line.message.match(/\s([2-5]\d{2})(?:\s|$)/)
  if (match) {
    const code = parseInt(match[1])
    if (code >= 200 && code < 300) return 'green'
    if (code >= 400) return 'red'
  }
  return null
}

function scrollToBottom() {
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

function onScroll() {
  const el = logEl.value
  if (!el) return
  autoScroll.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40
}

async function loadHistory() {
  if (!props.group) return
  loading.value = true
  try {
    const since = timeRange.value.seconds ? Date.now() / 1000 - timeRange.value.seconds : undefined
    const results = await Promise.all(
      props.group.containers.map(c =>
        api.get('/logs', {
          params: { container_name: c.container_name, since, q: searchQuery.value || undefined, limit: 500 },
        }).then(r => r.data).catch(() => [])
      )
    )
    const merged = results.flat().sort((a, b) => a.timestamp - b.timestamp)
    lines.value = merged.map(l => enrichLine({ ...l, _key: ++keyCounter }))
    if (autoScroll.value) scrollToBottom()
  } finally {
    loading.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  loadHistory()
}

function closeAll() {
  sockets.forEach(ws => ws.close())
  sockets = []
}

function connectAll() {
  closeAll()
  if (!props.group) return
  const token = localStorage.getItem('token')
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  for (const c of props.group.containers) {
    const ws = new WebSocket(
      `${proto}://${location.host}/ws/logs/${encodeURIComponent(c.container_name)}?token=${token}`
    )
    ws.onmessage = (e) => {
      const entry = JSON.parse(e.data)
      if (entry.type === 'ping') return
      entry._key = ++keyCounter
      enrichLine(entry)
      lines.value.push(entry)
      if (lines.value.length > 10000) lines.value.splice(0, lines.value.length - 10000)
      if (autoScroll.value) scrollToBottom()
    }
    sockets.push(ws)
  }
}

watch(
  () => props.group,
  async (g) => {
    lines.value = []
    searchQuery.value = ''
    closeAll()
    if (!g) return
    await loadHistory()
    connectAll()
  },
  { immediate: true }
)

onUnmounted(closeAll)
</script>

<style scoped>
.log-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-page);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  gap: 0.75rem;
  flex-wrap: wrap;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.group-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
  white-space: nowrap;
}
.legend {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
}
.legend-pill {
  font-size: 0.62rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  border: 1px solid;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
}
.log-output {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.78rem;
  line-height: 1.6;
}
.log-line {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  padding: 0 1rem;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-line:hover { background: var(--log-hover); }
.log-line.stderr .msg { color: var(--log-stderr); }

.svc-tag {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 0 0.3rem;
  border-radius: 3px;
  border: 1px solid;
  flex-shrink: 0;
  width: 5rem;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: none;
  font-family: 'JetBrains Mono', monospace;
}
.ts {
  flex-shrink: 0;
  color: var(--log-ts);
  user-select: none;
  font-size: 0.72rem;
  padding-top: 1px;
}
.log-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5px;
}
.log-dot.green  { background: #22c55e; }
.log-dot.red    { background: #f87171; }
.log-dot.amber  { background: #f59e0b; }
.log-dot-gap { flex-shrink: 0; width: 6px; }

.json-msg {
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.4rem;
  flex: 1;
}
.json-msg:hover .expand-toggle { opacity: 1; }
.log-level {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0 0.3rem;
  border-radius: 3px;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}
.log-level.info    { background: var(--badge-info-bg);  color: var(--badge-info-text); }
.log-level.warning { background: var(--badge-warn-bg);  color: var(--badge-warn-text); }
.log-level.error   { background: var(--badge-error-bg); color: var(--badge-error-text); }
.log-level.debug   { background: var(--badge-debug-bg); color: var(--badge-debug-text); }
.log-logger {
  color: var(--text-muted);
  font-size: 0.72rem;
  flex-shrink: 0;
}
.log-logger::after { content: ' ›'; margin-left: 0.1rem; }
.log-text { color: var(--log-text); }
.expand-toggle {
  color: var(--text-muted);
  font-size: 0.7rem;
  opacity: 0;
  transition: opacity 0.1s;
  flex-shrink: 0;
}
.json-raw {
  width: 100%;
  margin: 0.25rem 0;
  padding: 0.5rem 0.75rem;
  background: var(--bg-sunken);
  border-left: 2px solid var(--border);
  color: var(--text-muted);
  font-size: 0.72rem;
  white-space: pre;
  overflow-x: auto;
  border-radius: 0 4px 4px 0;
}
.msg { color: var(--log-text); flex: 1; }
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
.divider-line { flex: 1; height: 1px; background: #f59e0b44; }
.divider-label { white-space: nowrap; }
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: 100%;
  color: var(--text-muted);
  font-size: 0.9rem;
}
</style>
