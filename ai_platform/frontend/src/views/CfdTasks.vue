<!-- CFD 任务监控：表格（迭代进度/状态）+ 过滤 + 分页 + 新建/编辑 Dialog + 删除确认 -->
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { crud } from '../api'
import { usePagedList } from '../composables/usePagedList'
import { CFD_STATUS_LABEL, CFD_STATUS_TAG, CFD_TASK_STATUS } from '../constants'
import { fmtTime, toJsonOrNull, toJsonText } from '../utils/format'

const api = crud('cfd-tasks')
const casesApi = crud('design-cases')
const proxyApi = crud('proxy-models')

const { loading, items, total, query, filters, currentPage, load, search, resetFilters, onPageChange, onSizeChange, removeItem } =
  usePagedList(api, { case_id: '', status: '' }, { deleteLabel: (row) => row.task_name })

// 算例 / 代理模型下拉
const cases = ref([])
const proxies = ref([])
const caseMap = computed(() => Object.fromEntries(cases.value.map((c) => [c.id, c.case_name])))
const proxyMap = computed(() => Object.fromEntries(proxies.value.map((p) => [p.id, `${p.model_name}(${p.model_version})`])))

// 迭代进度
function iterPct(row) {
  if (!row.max_iter) return 0
  return Math.min(100, Math.round((row.current_iter / row.max_iter) * 100))
}
function iterStatus(row) {
  if (row.status === 'failed') return 'exception'
  if (row.status === 'success') return 'success'
  return undefined
}

// ---------- 新建 / 编辑 ----------
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref()
const form = reactive({
  case_id: '',
  task_name: '',
  task_type: 'flow',
  max_iter: 100,
  input_params_text: '',
  converge_criteria_text: '',
  proxy_model_id: '',
  mesh_file_key: '',
  celery_task_id: '',
  // 编辑独有字段
  status: 'pending',
  current_iter: 0,
  output_result_text: '',
  result_file_key: '',
  error_msg: '',
})
const rules = {
  case_id: [{ required: true, message: '请选择所属算例', trigger: 'change' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请输入任务类型', trigger: 'blur' }],
  max_iter: [{ required: true, message: '请输入最大迭代数', trigger: 'blur' }],
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {
    case_id: '',
    task_name: '',
    task_type: 'flow',
    max_iter: 100,
    input_params_text: '',
    converge_criteria_text: '',
    proxy_model_id: '',
    mesh_file_key: '',
    celery_task_id: '',
    status: 'pending',
    current_iter: 0,
    output_result_text: '',
    result_file_key: '',
    error_msg: '',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    case_id: row.case_id,
    task_name: row.task_name,
    task_type: row.task_type,
    max_iter: row.max_iter,
    input_params_text: toJsonText(row.input_params),
    converge_criteria_text: toJsonText(row.converge_criteria),
    proxy_model_id: row.proxy_model_id ?? '',
    mesh_file_key: row.mesh_file_key ?? '',
    celery_task_id: row.celery_task_id ?? '',
    status: row.status,
    current_iter: row.current_iter,
    output_result_text: toJsonText(row.output_result),
    result_file_key: row.result_file_key ?? '',
    error_msg: row.error_msg ?? '',
  })
  dialogVisible.value = true
}

async function save() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  let inputParams
  let convergeCriteria
  let outputResult
  try {
    inputParams = toJsonOrNull(form.input_params_text)
  } catch {
    ElMessage.warning('输入参数不是合法的 JSON')
    return
  }
  try {
    convergeCriteria = toJsonOrNull(form.converge_criteria_text)
  } catch {
    ElMessage.warning('收敛准则不是合法的 JSON')
    return
  }
  if (isEdit.value) {
    try {
      outputResult = toJsonOrNull(form.output_result_text)
    } catch {
      ElMessage.warning('输出结果不是合法的 JSON')
      return
    }
  }

  const base = {
    case_id: form.case_id,
    task_name: form.task_name,
    task_type: form.task_type,
    max_iter: form.max_iter,
    input_params: inputParams,
    converge_criteria: convergeCriteria,
    proxy_model_id: form.proxy_model_id || null,
    mesh_file_key: form.mesh_file_key || null,
    celery_task_id: form.celery_task_id || null,
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await api.update(editingId.value, {
        ...base,
        status: form.status,
        current_iter: form.current_iter,
        output_result: outputResult,
        result_file_key: form.result_file_key || null,
        error_msg: form.error_msg || null,
      })
    } else {
      await api.create(base)
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
  const [casesResp, proxyResp] = await Promise.all([casesApi.list({ limit: 500 }), proxyApi.list({ limit: 500 })])
  cases.value = casesResp.data
  proxies.value = proxyResp.data
})
</script>

<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="filters.case_id" placeholder="所属算例" clearable filterable style="width: 200px">
        <el-option v-for="c in cases" :key="c.id" :label="c.case_name" :value="c.id" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px">
        <el-option v-for="s in CFD_TASK_STATUS" :key="s" :label="CFD_STATUS_LABEL[s]" :value="s" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
      <div class="spacer" />
      <el-button type="primary" @click="openCreate">新建任务</el-button>
    </div>

    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="task_name" label="任务名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="task_type" label="类型" width="90" />
      <el-table-column label="所属算例" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ caseMap[row.case_id] || row.case_id }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="CFD_STATUS_TAG[row.status]">{{ CFD_STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="迭代进度" width="160">
        <template #default="{ row }">
          <el-progress
            :percentage="iterPct(row)"
            :status="iterStatus(row)"
            :stroke-width="10"
            :format="() => `${row.current_iter}/${row.max_iter}`"
          />
        </template>
      </el-table-column>
      <el-table-column label="代理模型" min-width="130" show-overflow-tooltip>
        <template #default="{ row }">{{ row.proxy_model_id ? proxyMap[row.proxy_model_id] || row.proxy_model_id : '-' }}</template>
      </el-table-column>
      <el-table-column prop="celery_task_id" label="Celery ID" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.celery_task_id || '-' }}</template>
      </el-table-column>
      <el-table-column label="开始时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.finished_at) }}</template>
      </el-table-column>
      <el-table-column prop="error_msg" label="错误信息" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.error_msg || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
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

  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新建任务'" width="680px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="所属算例" prop="case_id">
        <el-select v-model="form.case_id" filterable :disabled="isEdit" style="width: 320px" placeholder="选择算例">
          <el-option v-for="c in cases" :key="c.id" :label="c.case_name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="任务名称" prop="task_name">
        <el-input v-model="form.task_name" maxlength="200" />
      </el-form-item>
      <el-form-item label="任务类型" prop="task_type">
        <el-input v-model="form.task_type" maxlength="50" style="width: 220px" placeholder="flow / combustion / heat / cooling" />
      </el-form-item>
      <el-form-item label="最大迭代数" prop="max_iter">
        <el-input-number v-model="form.max_iter" :min="1" :step="50" />
      </el-form-item>
      <el-form-item label="输入参数">
        <el-input v-model="form.input_params_text" type="textarea" :rows="6" placeholder='JSON 格式，如 {"inlet_mach": 0.9}' />
      </el-form-item>
      <el-form-item label="收敛准则">
        <el-input v-model="form.converge_criteria_text" type="textarea" :rows="5" placeholder='JSON 格式，如 {"residual": 1e-6}' />
      </el-form-item>
      <el-form-item label="代理模型">
        <el-select v-model="form.proxy_model_id" filterable clearable style="width: 320px" placeholder="可选，关联代理模型">
          <el-option v-for="p in proxies" :key="p.id" :label="`${p.model_name}(${p.model_version})`" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="网格文件 Key">
        <el-input v-model="form.mesh_file_key" maxlength="500" placeholder="MinIO 对象 key" />
      </el-form-item>
      <el-form-item label="Celery ID">
        <el-input v-model="form.celery_task_id" maxlength="100" />
      </el-form-item>

      <template v-if="isEdit">
        <el-divider content-position="left">运行状态（编辑）</el-divider>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 200px">
            <el-option v-for="s in CFD_TASK_STATUS" :key="s" :label="CFD_STATUS_LABEL[s]" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="当前迭代">
          <el-input-number v-model="form.current_iter" :min="0" :step="10" />
        </el-form-item>
        <el-form-item label="输出结果">
          <el-input v-model="form.output_result_text" type="textarea" :rows="6" placeholder="JSON 格式" />
        </el-form-item>
        <el-form-item label="结果文件 Key">
          <el-input v-model="form.result_file_key" maxlength="500" placeholder="MinIO 对象 key" />
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
