// 状态/类型枚举与展示映射（与后端 app/schemas.py 的 Literal 定义保持一致）

// 设计算例状态
export const DESIGN_CASE_STATUS = ['draft', 'running', 'finished', 'archived']
export const CASE_STATUS_LABEL = { draft: '草稿', running: '运行中', finished: '已完成', archived: '已归档' }
export const CASE_STATUS_TAG = { draft: 'info', running: 'warning', finished: 'success', archived: 'info' }

// CFD 任务状态
export const CFD_TASK_STATUS = ['pending', 'running', 'success', 'failed', 'stop']
export const CFD_STATUS_LABEL = { pending: '待运行', running: '运行中', success: '成功', failed: '失败', stop: '已停止' }
export const CFD_STATUS_TAG = { pending: 'info', running: 'warning', success: 'success', failed: 'danger', stop: 'info' }

// 代理模型类型与状态
export const PROXY_MODEL_TYPES = ['kriging', 'gp', 'mlp', 'mf_adaptive']
export const PROXY_TYPE_LABEL = { kriging: '克里金', gp: '高斯过程', mlp: 'MLP', mf_adaptive: '多保真自适应采样' }
export const PROXY_MODEL_STATUS = ['draft', 'training', 'ready', 'failed']
export const PROXY_STATUS_LABEL = { draft: '草稿', training: '训练中', ready: '可用', failed: '失败' }
export const PROXY_STATUS_TAG = { draft: 'info', training: 'warning', ready: 'success', failed: 'danger' }

// 智能体运行状态
export const AGENT_RUN_STATUS = ['pending', 'running', 'success', 'failed']
export const AGENT_STATUS_LABEL = { pending: '待运行', running: '运行中', success: '成功', failed: '失败' }
export const AGENT_STATUS_TAG = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }

// 用户角色
export const USER_ROLES = ['admin', 'engineer', 'viewer']
export const ROLE_LABEL = { admin: '管理员', engineer: '工程师', viewer: '观察者' }
