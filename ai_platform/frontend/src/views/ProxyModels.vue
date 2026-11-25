<!-- 代理模型管理：表格 + 过滤 + 分页 + 新建/编辑 Dialog + 删除确认 -->
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { crud } from '../api'
import { usePagedList } from '../composables/usePagedList'
import { PROXY_MODEL_STATUS, PROXY_MODEL_TYPES, PROXY_STATUS_LABEL, PROXY_STATUS_TAG, PROXY_TYPE_LABEL } from '../constants'
import { fmtTime, pretty, toJsonOrNull, toJsonText } from '../utils/format'

const api = crud('proxy-models')

const { loading, items, total, query, filters, currentPage, load, search, resetFilters, onPageChange, onSizeChange, removeItem } =
  usePagedList(api, { model_type: '', status: '' }, { deleteLabel: (row) => row.model_name })

// ---------- 新建 / 编辑 ----------
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref()
const form = reactive({
  model_name: '',
  model_version: 'v1',
  model_type: 'kriging',
  input_dim: 1,
  output_dim: 1,
  status: 'draft',
  metric_text: '',
  weight_key: '',
  train_dataset_key: '',
  description: '',
})
const rules = {
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  model_version: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {
    model_name: '',
    model_version: 'v1',
    model_type: 'kriging',
    input_dim: 1,
    output_dim: 1,
    status: 'draft',
    metric_text: '',
    weight_key: '',
    train_dataset_key: '',
    description: '',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    model_name: row.model_name,
    model_version: row.model_version,
    model_type: row.model_type,
    input_dim: row.input_dim,
    output_dim: row.output_dim,
    status: row.status,
    metric_text: toJsonText(row.metric),
    weight_key: row.weight_key ?? '',
    train_dataset_key: row.train_dataset_key ?? '',
    description: row.description ?? '',
  })
  dialogVisible.value = true
}

async function save() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  let metric
  try {
    metric = toJsonOrNull(form.metric_text)
  } catch {
    ElMessage.warning('评估指标不是合法的 JSON')
    return
  }
  const payload = {
    model_name: form.model_name,
    model_version: form.model_version,
    model_type: form.model_type,
    input_dim: form.input_dim,
    output_dim: form.output_dim,
    status: form.status,
    metric,
    weight_key: form.weight_key || null,
    train_dataset_key: form.train_dataset_key || null,
    description: form.description || null,
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await api.update(editingId.value, payload)
    } else {
      await api.create(payload)
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="filters.model_type" placeholder="模型类型" clearable style="width: 170px">
        <el-option v-for="t in PROXY_MODEL_TYPES" :key="t" :label="PROXY_TYPE_LABEL[t]" :value="t" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px">
        <el-option v-for="s in PROXY_MODEL_STATUS" :key="s" :label="PROXY_STATUS_LABEL[s]" :value="s" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
      <div class="spacer" />
      <el-button type="primary" @click="openCreate">新建模型</el-button>
    </div>

    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="model_name" label="模型名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="model_version" label="版本" width="70" />
      <el-table-column label="类型" width="140">
        <template #default="{ row }">{{ PROXY_TYPE_LABEL[row.model_type] || row.model_type }}</template>
      </el-table-column>
      <el-table-column prop="input_dim" label="输入维度" width="90" align="center" />
      <el-table-column prop="output_dim" label="输出维度" width="90" align="center" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="PROXY_STATUS_TAG[row.status]">{{ PROXY_STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="评估指标" width="100" align="center">
        <template #default="{ row }">
          <el-popover v-if="row.metric" placement="left" :width="440" trigger="click">
            <template #reference>
              <el-link type="primary">查看</el-link>
            </template>
            <pre class="json-pre">{{ pretty(row.metric) }}</pre>
          </el-popover>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="weight_key" label="权重文件 Key" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.weight_key || '-' }}</template>
      </el-table-column>
      <el-table-column prop="train_dataset_key" label="训练集 Key" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.train_dataset_key || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
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

  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑模型' : '新建模型'" width="640px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="模型名称" prop="model_name">
        <el-input v-model="form.model_name" maxlength="200" />
      </el-form-item>
      <el-form-item label="版本" prop="model_version">
        <el-input v-model="form.model_version" maxlength="50" style="width: 200px" />
      </el-form-item>
      <el-form-item label="模型类型" prop="model_type">
        <el-select v-model="form.model_type" style="width: 220px">
          <el-option v-for="t in PROXY_MODEL_TYPES" :key="t" :label="PROXY_TYPE_LABEL[t]" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="输入维度" prop="input_dim">
        <el-input-number v-model="form.input_dim" :min="1" />
      </el-form-item>
      <el-form-item label="输出维度" prop="output_dim">
        <el-input-number v-model="form.output_dim" :min="1" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="form.status" style="width: 200px">
          <el-option v-for="s in PROXY_MODEL_STATUS" :key="s" :label="PROXY_STATUS_LABEL[s]" :value="s" />
        </el-select>
      </el-form-item>
      <el-form-item label="评估指标">
        <el-input v-model="form.metric_text" type="textarea" :rows="5" placeholder='JSON 格式，如 {"r2": 0.95, "rmse": 0.02}' />
      </el-form-item>
      <el-form-item label="权重文件 Key">
        <el-input v-model="form.weight_key" maxlength="500" placeholder="MinIO 对象 key" />
      </el-form-item>
      <el-form-item label="训练集 Key">
        <el-input v-model="form.train_dataset_key" maxlength="500" placeholder="MinIO 对象 key" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
