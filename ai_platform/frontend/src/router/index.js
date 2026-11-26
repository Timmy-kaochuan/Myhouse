import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'

// MVP 四个页面：算例管理 / CFD 任务监控 / 代理模型管理 / 智能体运行记录
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/cases',
      children: [
        { path: 'cases', component: () => import('../views/DesignCases.vue'), meta: { title: '设计算例管理' } },
        { path: 'cfd', component: () => import('../views/CfdTasks.vue'), meta: { title: 'CFD 任务监控' } },
        { path: 'models', component: () => import('../views/ProxyModels.vue'), meta: { title: '代理模型管理' } },
        { path: 'agents', component: () => import('../views/AgentRuns.vue'), meta: { title: '智能体运行记录' } },
      ],
    },
  ],
})

export default router
