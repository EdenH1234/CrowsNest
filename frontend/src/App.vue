<template>
  <Toast />
  <router-view />
</template>

<script setup>
import Toast from 'primevue/toast'
import { useTheme } from './composables/useTheme.js'
useTheme()
</script>

<style>
:root {
  --bg-page:      #f1f5f9;
  --bg-surface:   #ffffff;
  --bg-surface-2: #f8fafc;
  --bg-hover:     #f1f5f9;
  --bg-active:    #e2e8f0;
  --bg-sunken:    #f8fafc;
  --border:       #e2e8f0;
  --border-2:     #cbd5e1;
  --text-primary:   #0f172a;
  --text-secondary: #475569;
  --text-muted:     #94a3b8;
  --text-active:    #3b5fc0;
  --log-text:   #334155;
  --log-ts:     #94a3b8;
  --log-stderr: #dc2626;
  --log-hover:  rgba(0, 0, 0, 0.04);
  --badge-info-bg:    #dbeafe; --badge-info-text:    #1d4ed8;
  --badge-warn-bg:    #fef3c7; --badge-warn-text:    #92400e;
  --badge-error-bg:   #fee2e2; --badge-error-text:   #b91c1c;
  --badge-debug-bg:   #f1f5f9; --badge-debug-text:   #475569;
}

:root.dark-mode {
  --bg-page:      #0f1117;
  --bg-surface:   #13151f;
  --bg-surface-2: #1a1d27;
  --bg-hover:     #1e2235;
  --bg-active:    #252a40;
  --bg-sunken:    #0a0d14;
  --border:       #1e2235;
  --border-2:     #2d3148;
  --text-primary:   #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted:     #4a5568;
  --text-active:    #7c9ef8;
  --log-text:   #cbd5e1;
  --log-ts:     #4a5568;
  --log-stderr: #f87171;
  --log-hover:  rgba(255, 255, 255, 0.03);
  --badge-info-bg:    #1e3a5f; --badge-info-text:    #60a5fa;
  --badge-warn-bg:    #3b2f00; --badge-warn-text:    #f59e0b;
  --badge-error-bg:   #3b0f0f; --badge-error-text:   #f87171;
  --badge-debug-bg:   #1e2235; --badge-debug-text:   #6b7280;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; font-family: 'Inter', system-ui, sans-serif; }
body { background: var(--bg-page); color: var(--text-primary); }
</style>
