<template>
  <Toast />
  <router-view />
</template>

<script setup>
import Toast from 'primevue/toast'
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; font-family: 'Inter', system-ui, sans-serif; }
body { background: #0f1117; color: #e2e8f0; }
</style>
