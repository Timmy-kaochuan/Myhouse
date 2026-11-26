// 展示格式化与 JSON 文本转换工具

// UTC ISO 时间 -> 本地可读时间
export function fmtTime(v) {
  if (!v) return '-'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString('zh-CN', { hour12: false })
}

// 任意 JSON 值 -> 缩进文本（用于 pre 展示）
export function pretty(v) {
  return v == null ? '-' : JSON.stringify(v, null, 2)
}

// textarea 文本 -> JSON 值；空白返回 null；非法 JSON 抛出（调用方提示）
export function toJsonOrNull(text) {
  const t = (text ?? '').trim()
  if (!t) return null
  return JSON.parse(t)
}

// JSON 值 -> textarea 展示文本
export function toJsonText(v) {
  return v == null ? '' : JSON.stringify(v, null, 2)
}
