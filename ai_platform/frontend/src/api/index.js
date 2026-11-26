import axios from 'axios'
import { ElMessage } from 'element-plus'

// axios 实例：vite dev 代理把 /api 转发到 FastAPI 后端（导出供自定义动作调用，如 /predict）
export const http = axios.create({ baseURL: '/api', timeout: 20000 })

// 统一错误提示：FastAPI 的 detail 是字符串，其余按 HTTP 状态码提示
http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const detail = error.response?.data?.detail
    const msg =
      typeof detail === 'string'
        ? detail
        : error.response?.status
          ? `请求失败（HTTP ${error.response.status}）`
          : error.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

// 六类资源通用 CRUD（对应后端 REST 路由：users / design-cases / cfd-tasks / proxy-models / agent-runs / experiment-records）
export function crud(resource) {
  return {
    list: (params) => http.get(`/${resource}`, { params }),
    get: (id) => http.get(`/${resource}/${id}`),
    create: (data) => http.post(`/${resource}`, data),
    update: (id, data) => http.patch(`/${resource}/${id}`, data),
    remove: (id) => http.delete(`/${resource}/${id}`),
  }
}
