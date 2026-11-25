import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 通用「列表 + 过滤 + 分页 + 删除确认」逻辑。
// 后端 list 接口返回数组不带 total，因此用 limit+1 探测是否有下一页来近似分页。
export function usePagedList(api, defaultFilters = {}, options = {}) {
  const { deleteLabel = (row) => `ID ${row.id}` } = options

  const loading = ref(false)
  const items = ref([])
  const total = ref(0)
  const query = reactive({ offset: 0, limit: 10 })
  const filters = reactive({ ...defaultFilters })

  const currentPage = computed(() => Math.floor(query.offset / query.limit) + 1)

  // 过滤参数去掉空值（空串/undefined/null 不下发给后端）
  function clean(obj) {
    return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== ''))
  }

  async function load() {
    loading.value = true
    try {
      const { data } = await api.list({ offset: query.offset, limit: query.limit + 1, ...clean(filters) })
      const hasMore = data.length > query.limit
      if (hasMore) data.length = query.limit
      items.value = data
      total.value = query.offset + data.length + (hasMore ? 1 : 0)
    } finally {
      loading.value = false
    }
  }

  // 条件查询：回到第一页
  function search() {
    query.offset = 0
    return load()
  }

  function resetFilters() {
    Object.assign(filters, defaultFilters)
    return search()
  }

  function onPageChange(page) {
    query.offset = (page - 1) * query.limit
    return load()
  }

  function onSizeChange(size) {
    query.limit = size
    query.offset = 0
    return load()
  }

  // 删除确认 + 删除后刷新；若删掉的是本页最后一条则回退一页
  async function removeItem(row) {
    await ElMessageBox.confirm(`确认删除「${deleteLabel(row)}」吗？关联数据将级联删除。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await api.remove(row.id)
    ElMessage.success('删除成功')
    if (items.value.length === 1 && query.offset > 0) {
      query.offset = Math.max(0, query.offset - query.limit)
    }
    await load()
  }

  return { loading, items, total, query, filters, currentPage, load, search, resetFilters, onPageChange, onSizeChange, removeItem }
}
