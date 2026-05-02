<template>
  <div class="page-wrap">
    <TopBar />
    <div class="content-scroll">
      <div class="tile">
        <div class="tile-header">
          <span class="tile-title">{{ route.meta.label || 'Сторінка' }}</span>
        </div>
        <div class="placeholder-body">
          <span>{{ route.meta.label }} (в розробці)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import TopBar from '../components/TopBar.vue'

const route = useRoute()
</script>

<style scoped>
.page-wrap {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.tile-header {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border-light);
}

.tile-title {
  font-size: 15px;
  font-weight: 700;
}

.placeholder-body {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-light);
  font-size: 14px;
}
</style>
