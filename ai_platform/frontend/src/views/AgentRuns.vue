<!-- 智能体运行记录：表格 + 过滤 + 分页 + 详情抽屉（state_snapshot/trace_log）+ 新建/编辑 + 删除 -->
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { crud } from '../api'
import { usePagedList } from '../composables/usePagedList'
import { AGENT_RUN_STATUS, AGENT_STATUS_LABEL, AGENT_STATUS_TAG } from '../constants'
import { fmtTime, pretty, toJsonOrNull, toJsonText } from '../utils/format'

const api = crud('agent-runs')
const casesApi = crud('design-cases')

const { loading, items, total, query, filters, currentPage, load, search, resetFilters, onPageChange, onSizeChange, removeItem } =
  usePagedList(api, { case_id: '', status: '' }, { deleteLabel: (row) => `#${row.id} ${row.agent_name}` })

const cases = ref([])
const caseMap = computed(() => Object.fromEntries(cases.value.map((c) => [c.id, c.case_name])))

// ---------- 详情抽屉 ----------
const drawerVisible = ref(false)
const detail = ref(null)

function openDetail(row) {
  detail.value = row
  drawerVisible.value = true
}

// ---------- 新建 / 编辑 ----------
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref()
const form = reactive({
  case_id: '',
  agent_name: '',
  thread_id: '',
  input_query: '',
  status: 'pending',
  state_snapshot_text: '',
  trace_log_text: '',
  error_msg: '',
})
const rules = {
  case_id: [{ required: true, message: '请选择所属算例', trigger: 'change' }],
  agent_name: [{ required: true, message: '请输入智能体名称', trigger: 'blur' }],
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {
    case_id: '',
    agent_name: '',
    thread_id: '',
    input_query: '',
    status: 'pending',
    state_snapshot_text: '',
    trace_log_text: '',
    error_msg: '',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    case_id: row.case_id,
    agent_name: row.agent_name,
    thread_id: row.thread_id ?? '',
    input_query: row.input_query ?? '',
    status: row.status,
    state_snapshot_text: toJsonText(row.state_snapshot),
    trace_log_text: toJsonText(row.trace_log),
    error_msg: row.error_msg ?? '',
  })
  dialogVisible.value = true
}

async function save() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  let stateSnapshot
  let traceLog
  if (isEdit.value) {
    try {
      stateSnapshot = toJsonOrNull(form.state_snapshot_text)
    } catch {
      ElMessage.warning('state_snapshot 不是合法的 JSON')
      return
    }
    try {
      traceLog = toJsonOrNull(form.trace_log_text)
    } catch {
      ElMessage.warning('trace_log 不是合法的 JSON')
      return
    }
  }
  const base = {
    agent_name: form.agent_name,
    thread_id: form.thread_id || null,
    input_query: form.input_query || null,
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await api.update(editingId.value, {
        ...base,
        status: form.status,
        state_snapshot: stateSnapshot,
        trace_log: traceLog,
        error_msg: form.error_msg || null,
      })
    } else {
      await api.create({ ...base, case_id: form.case_id, status: form.status })
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await load()
  const { data } = await casesApi.list({ limit: 500 })
  cases.value = data
})
</script>

<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="filters.case_id" placeholder="所属算例" clearable filterable style="width: 200px">
        <el-option v-for="c in cases" :key="c.id" :label="c.case_name" :value="c.id" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px">
        <el-option v-for="s in AGENT_RUN_STATUS" :key="s" :label="AGENT_STATUS_LABEL[s]" :value="s" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
      <div class="spacer" />
      <el-button type="primary" @click="openCreate">新建记录</el-button>
    </div>

    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="agent_name" label="智能体" min-width="130" show-overflow-tooltip />
      <el-table-column label="所属算例" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ caseMap[row.case_id] || row.case_id }}</template>
      </el-table-column>
      <el-table-column prop="thread_id" label="Thread ID" min-width="130" show-overflow-tooltip>
        <template #default="{ row }">{{ row.thread_id || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="AGENT_STATUS_TAG[row.status]">{{ AGENT_STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="input_query" label="输入 Query" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.input_query || '-' }}</template>
      </el-table-column>
      <el-table-column label="开始时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.finished_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="removeItem(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      class="pager"
      background
      layout="total, prev, pager, next, sizes"
      :total="total"
      :page-size="query.limit"
      :page-sizes="[10, 20, 50]"
      @current-change="onPageChange"
      @size-change="onSizeChange"
    />
  </el-card>

  <!-- 详情抽屉：查看 state_snapshot / trace_log -->
  <el-drawer v-model="drawerVisible" title="运行详情" size="600px">
    <template v-if="detail">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="智能体">{{ detail.agent_name }}</el-descriptions-item>
        <el-descriptions-item label="所属算例">{{ caseMap[detail.case_id] || detail.case_id }}</el-descriptions-item>
        <el-descriptions-item label="Thread ID">{{ detail.thread_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="AGENT_STATUS_TAG[detail.status]">{{ AGENT_STATUS_LABEL[detail.status] || detail.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ fmtTime(detail.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ fmtTime(detail.finished_at) }}</el-descriptions-item>
        <el-descriptions-item label="输入 Query">{{ detail.input_query || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.error_msg" label="错误信息">{{ detail.error_msg }}</el-descriptions-item>
      </el-descriptions>
      <div class="drawer-section-title">state_snapshot</div>
      <pre class="json-pre">{{ pretty(detail.state_snapshot) }}</pre>
      <div class="drawer-section-title">trace_log</div>
      <pre class="json-pre">{{ pretty(detail.trace_log) }}</pre>
    </template>
  </el-drawer>

  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑记录' : '新建记录'" width="640px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="所属算例" prop="case_id">
        <el-select v-model="form.case_id" filterable :disabled="isEdit" style="width: 320px" placeholder="选择算例">
          <el-option v-for="c in cases" :key="c.id" :label="c.case_name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="智能体名称" prop="agent_name">
        <el-input v-model="form.agent_name" maxlength="100" placeholder="如：geometry-agent" />
      </el-form-item>
      <el-form-item label="Thread ID">
        <el-input v-model="form.thread_id" maxlength="100" placeholder="LangGraph thread_id" />
      </el-form-item>
      <el-form-item label="输入 Query">
        <el-input v-model="form.input_query" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="form.status" style="width: 200px">
          <el-option v-for="s in AGENT_RUN_STATUS" :key="s" :label="AGENT_STATUS_LABEL[s]" :value="s" />
        </el-select>
      </el-form-item>
      <template v-if="isEdit">
        <el-divider content-position="left">运行产物（编辑）</el-divider>
        <el-form-item label="state_snapshot">
          <el-input v-model="form.state_snapshot_text" type="textarea" :rows="6" placeholder="JSON 格式" />
        </el-form-item>
        <el-form-item label="trace_log">
          <el-input v-model="form.trace_log_text" type="textarea" :rows="6" placeholder="JSON 格式" />
        </el-form-item>
        <el-form-item label="错误信息">
          <el-input v-model="form.error_msg" type="textarea" :rows="3" />
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
