<!-- 算例管理：表格 + 过滤 + 分页 + 新建/编辑 Dialog + 删除确认 -->
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { crud } from '../api'
import { usePagedList } from '../composables/usePagedList'
import { CASE_STATUS_LABEL, CASE_STATUS_TAG, DESIGN_CASE_STATUS } from '../constants'
import { fmtTime, pretty, toJsonOrNull, toJsonText } from '../utils/format'

const api = crud('design-cases')
const usersApi = crud('users')

const { loading, items, total, query, filters, currentPage, load, search, resetFilters, onPageChange, onSizeChange, removeItem } =
  usePagedList(api, { status: '', creator_id: '' }, { deleteLabel: (row) => row.case_name })

// 用户下拉（创建人）
const users = ref([])
const userMap = computed(() => Object.fromEntries(users.value.map((u) => [u.id, u.display_name || u.email])))

// ---------- 新建 / 编辑 ----------
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref()
const form = reactive({
  case_name: '',
  case_version: 'v1',
  status: 'draft',
  creator_id: '',
  description: '',
  design_parameters_text: '',
})
const rules = {
  case_name: [{ required: true, message: '请输入算例名称', trigger: 'blur' }],
  case_version: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  creator_id: [{ required: true, message: '请选择创建人', trigger: 'change' }],
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {
    case_name: '',
    case_version: 'v1',
    status: 'draft',
    creator_id: '',
    description: '',
    design_parameters_text: '',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    case_name: row.case_name,
    case_version: row.case_version,
    status: row.status,
    creator_id: row.creator_id,
    description: row.description ?? '',
    design_parameters_text: toJsonText(row.design_parameters),
  })
  dialogVisible.value = true
}

async function save() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  let designParameters
  try {
    designParameters = toJsonOrNull(form.design_parameters_text)
  } catch {
    ElMessage.warning('设计参数不是合法的 JSON')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await api.update(editingId.value, {
        case_name: form.case_name,
        case_version: form.case_version,
        status: form.status,
        description: form.description || null,
        design_parameters: designParameters,
      })
    } else {
      await api.create({
        case_name: form.case_name,
        case_version: form.case_version,
        status: form.status,
        creator_id: form.creator_id,
        description: form.description || null,
        design_parameters: designParameters,
      })
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
  const { data } = await usersApi.list({ limit: 500 })
  users.value = data
})
</script>

<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px">
        <el-option v-for="s in DESIGN_CASE_STATUS" :key="s" :label="CASE_STATUS_LABEL[s]" :value="s" />
      </el-select>
      <el-select v-model="filters.creator_id" placeholder="创建人" clearable filterable style="width: 180px">
        <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.email" :value="u.id" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
      <div class="spacer" />
      <el-button type="primary" @click="openCreate">新建算例</el-button>
    </div>

    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="case_name" label="算例名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="case_version" label="版本" width="80" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="CASE_STATUS_TAG[row.status]">{{ CASE_STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
      <el-table-column label="设计参数" width="100" align="center">
        <template #default="{ row }">
          <el-popover v-if="row.design_parameters" placement="left" :width="440" trigger="click">
            <template #reference>
              <el-link type="primary">查看</el-link>
            </template>
            <pre class="json-pre">{{ pretty(row.design_parameters) }}</pre>
          </el-popover>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="创建人" width="130">
        <template #default="{ row }">{{ userMap[row.creator_id] || row.creator_id }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.updated_at) }}</template>
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

  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑算例' : '新建算例'" width="640px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="算例名称" prop="case_name">
        <el-input v-model="form.case_name" maxlength="200" placeholder="如：某型燃机一级透平叶片优化" />
      </el-form-item>
      <el-form-item label="版本" prop="case_version">
        <el-input v-model="form.case_version" maxlength="50" style="width: 200px" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="form.status" style="width: 200px">
          <el-option v-for="s in DESIGN_CASE_STATUS" :key="s" :label="CASE_STATUS_LABEL[s]" :value="s" />
        </el-select>
      </el-form-item>
      <el-form-item label="创建人" prop="creator_id">
        <el-select v-model="form.creator_id" filterable :disabled="isEdit" style="width: 260px" placeholder="选择用户">
          <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.email" :value="u.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000" />
      </el-form-item>
      <el-form-item label="设计参数">
        <el-input
          v-model="form.design_parameters_text"
          type="textarea"
          :rows="8"
          placeholder='JSON 格式，如 {"blade_count": 36, "chord_mm": 62.5}'
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
