<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <div class="logo-title">重型燃气轮机</div>
        <div class="logo-sub">集成设计平台</div>
      </div>
      <el-menu
        :default-active="route.path"
        router
        background-color="#001529"
        text-color="#b7c0cd"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/cases">设计算例管理</el-menu-item>
        <el-menu-item index="/cfd">CFD 任务监控</el-menu-item>
        <el-menu-item index="/models">代理模型管理</el-menu-item>
        <el-menu-item index="/agents">智能体运行记录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ route.meta.title }}</span>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  display: flex;
  flex-direction: column;
  background: #001529;
}

.logo {
  padding: 20px 16px;
  color: #fff;
}

.logo-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.logo-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #b7c0cd;
}

.aside :deep(.el-menu) {
  flex: 1;
  overflow-y: auto;
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.main {
  background: #f5f7fa;
}
</style>
