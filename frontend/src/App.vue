<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <a-config-provider :theme="{ token: { colorPrimary: '#1677ff' } }">
    <RouterView />
  </a-config-provider>
</template>

<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
}
</style>
