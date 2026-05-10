<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <CrowsNestLogo :size="24" />
      <span>CrowsNest</span>
      <Button
        :icon="isDark ? 'pi pi-sun' : 'pi pi-moon'"
        text
        rounded
        size="small"
        class="header-btn"
        @click="toggle"
        v-tooltip.right="isDark ? 'Light mode' : 'Dark mode'"
      />
      <Button
        icon="pi pi-sign-out"
        text
        rounded
        size="small"
        class="header-btn"
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

    <div class="container-list">
      <div v-if="grouped.length === 0" class="empty-state">
        <i class="pi pi-spin pi-spinner" />
        <span>No containers found</span>
      </div>

      <div v-for="group in grouped" :key="group.project ?? '__standalone__'" class="group">
        <div class="group-label">
          <i :class="group.project ? 'pi pi-folder' : 'pi pi-box'" />
          <span class="group-name">{{ group.project || 'standalone' }}</span>
          <button
            class="delete-group-btn"
            v-tooltip.right="'Delete group'"
            @click.stop="promptDelete(group)"
          >
            <i class="pi pi-trash" />
          </button>
        </div>
        <div
          v-for="c in group.containers"
          :key="c.container_id"
          class="container-item"
          :class="{ active: selected === c.container_id }"
          @click="$emit('select', c)"
        >
          <span class="status-dot" :class="c.status" />
          <span class="container-info">
            <span class="name" :title="c.container_name">{{ c.container_name }}</span>
            <span v-if="c.image_tag" class="image-tag" :title="c.image_tag">{{ c.image_tag }}</span>
          </span>
        </div>
      </div>

      <!-- Recently deleted -->
      <div v-if="deletedGroups.length > 0" class="deleted-section">
        <div class="deleted-header" @click="showDeleted = !showDeleted">
          <i class="pi pi-trash" />
          <span>Recently deleted</span>
          <i :class="showDeleted ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="chevron" />
        </div>
        <div v-if="showDeleted">
          <div
            v-for="dg in deletedGroups"
            :key="dg.project ?? '__standalone__'"
            class="deleted-item"
          >
            <div class="deleted-item-info">
              <span class="deleted-name">{{ dg.project || 'standalone' }}</span>
              <span class="deleted-days">{{ dg.daysLeft }}d left</span>
            </div>
            <button class="recover-btn" @click="recoverGroup(dg.project)">Restore</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete confirmation dialog -->
    <Dialog
      v-model:visible="deleteDialog.visible"
      modal
      :header="`Delete '${deleteDialog.groupName}'`"
      :style="{ width: '360px' }"
      @hide="resetDeleteDialog"
    >
      <div class="dialog-body">
        <p class="dialog-msg">
          This will hide all logs for <strong>{{ deleteDialog.groupName }}</strong>.
          You have 7 days to restore before they are permanently deleted.
        </p>
        <label class="dialog-label">Type <strong>delete</strong> to confirm</label>
        <InputText
          v-model="deleteDialog.input"
          placeholder="delete"
          fluid
          autofocus
          @keyup.enter="confirmDelete"
        />
      </div>
      <template #footer>
        <Button label="Cancel" text @click="resetDeleteDialog" />
        <Button
          label="Delete"
          severity="danger"
          :disabled="deleteDialog.input !== 'delete'"
          @click="confirmDelete"
        />
      </template>
    </Dialog>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import CrowsNestLogo from './CrowsNestLogo.vue'
import { useTheme } from '../composables/useTheme.js'
import api from '../api.js'

const props = defineProps({ selected: String })
const emit = defineEmits(['select'])

const router = useRouter()
const { isDark, toggle } = useTheme()
const containers = ref([])
const deletedContainers = ref([])
const filter = ref('')
const showDeleted = ref(false)
let pollTimer = null

const deleteDialog = ref({ visible: false, groupName: '', project: null, input: '' })

const grouped = computed(() => {
  const q = filter.value.toLowerCase()
  const filtered = containers.value.filter((c) =>
    c.container_name.toLowerCase().includes(q)
  )
  const map = new Map()
  for (const c of filtered) {
    const key = c.compose_project ?? '__standalone__'
    if (!map.has(key)) map.set(key, { project: c.compose_project ?? null, containers: [] })
    map.get(key).containers.push(c)
  }
  return [...map.values()]
})

const deletedGroups = computed(() => {
  const map = new Map()
  const now = Date.now() / 1000
  for (const c of deletedContainers.value) {
    const key = c.compose_project ?? '__standalone__'
    if (!map.has(key)) {
      const daysLeft = Math.max(0, Math.ceil((c.deleted_at + 7 * 86400 - now) / 86400))
      map.set(key, { project: c.compose_project ?? null, daysLeft })
    }
  }
  return [...map.values()]
})

async function fetchContainers() {
  try {
    const [{ data: active }, { data: deleted }] = await Promise.all([
      api.get('/containers'),
      api.get('/containers/deleted'),
    ])
    containers.value = active
    deletedContainers.value = deleted
  } catch {}
}

function promptDelete(group) {
  deleteDialog.value = {
    visible: true,
    groupName: group.project || 'standalone',
    project: group.project,
    input: '',
  }
}

function resetDeleteDialog() {
  deleteDialog.value = { visible: false, groupName: '', project: null, input: '' }
}

async function confirmDelete() {
  if (deleteDialog.value.input !== 'delete') return
  try {
    await api.post('/groups/delete', { compose_project: deleteDialog.value.project })
    emit('select', null)
    await fetchContainers()
    showDeleted.value = true
  } catch {}
  resetDeleteDialog()
}

async function recoverGroup(project) {
  try {
    await api.post('/groups/recover', { compose_project: project })
    await fetchContainers()
  } catch {}
}

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}

onMounted(() => {
  fetchContainers()
  pollTimer = setInterval(fetchContainers, 2000)
})

onUnmounted(() => clearInterval(pollTimer))
</script>

<style scoped>
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
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
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}
.header-btn {
  margin-left: auto;
}
.header-btn + .header-btn {
  margin-left: 0;
}
.search-box {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border);
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
  color: var(--text-muted);
}
.group-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.delete-group-btn {
  all: unset;
  cursor: pointer;
  opacity: 0;
  display: flex;
  align-items: center;
  padding: 2px 4px;
  border-radius: 3px;
  color: var(--text-muted);
  transition: opacity 0.1s, color 0.1s;
}
.group-label:hover .delete-group-btn {
  opacity: 1;
}
.delete-group-btn:hover {
  color: #f87171;
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
  background: var(--bg-hover);
}
.container-item.active {
  background: var(--bg-active);
  color: var(--text-active);
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.running { background: #22c55e; }
.status-dot.stopped { background: #94a3b8; }
.container-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 0.05rem;
}
.name {
  font-size: 0.82rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.image-tag {
  font-size: 0.68rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.container-list {
  flex: 1;
  overflow-y: auto;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: var(--text-muted);
  font-size: 0.85rem;
}

/* Recently deleted */
.deleted-section {
  border-top: 1px solid var(--border);
  margin-top: 0.5rem;
}
.deleted-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}
.deleted-header:hover {
  color: var(--text-secondary);
}
.chevron {
  margin-left: auto;
  font-size: 0.6rem;
}
.deleted-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.35rem 0.75rem 0.35rem 1rem;
  gap: 0.5rem;
}
.deleted-item-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.deleted-name {
  font-size: 0.8rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.deleted-days {
  font-size: 0.65rem;
  color: var(--text-muted);
  opacity: 0.7;
}
.recover-btn {
  all: unset;
  cursor: pointer;
  font-size: 0.7rem;
  color: #60a5fa;
  white-space: nowrap;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #60a5fa44;
  transition: background 0.1s;
}
.recover-btn:hover {
  background: #60a5fa22;
}

/* Dialog */
.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.dialog-msg {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}
.dialog-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}
</style>
