<!-- 算例管理（主档）：表格 + 过滤 + 分页 + 新建/编辑 Dialog + 版本抽屉（版本 CRUD + 产物增删查） -->
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { crud } from '../api'
import { usePagedList } from '../composables/usePagedList'
import { ARTIFACT_TYPES, ARTIFACT_TYPE_LABEL, CASE_VERSION_STATUS, VERSION_STATUS_LABEL, VERSION_STATUS_TAG } from '../constants'
import { fmtTime, pretty, toJsonOrNull, toJsonText } from '../utils/format'

const api = crud('design-cases')
const versionsApi = crud('case-versions')
const artifactsApi = crud('case-artifacts')
const usersApi = crud('users')

const { loading, items, total, query, filters, currentPage, load, search, resetFilters, onPageChange, onSizeChange, removeItem } =
  usePagedList(api, { creator_id: '' }, { deleteLabel: (row) => row.case_name })

// 用户下拉（创建人/父算例）
const users = ref([])
const userMap = computed(() => Object.fromEntries(users.value.map((u) => [u.id, u.display_name || u.email])))

// ---------- 版本数据（用于版本数列与抽屉） ----------
const versions = ref([])
const versionCount = computed(() => {
  const m = {}
  for (const v of versions.value) m[v.case_id] = (m[v.case_id] || 0) + 1
  return m
})
async function reloadVersions() {
  const { data } = await versionsApi.list({ limit: 500 })
  versions.value = data
}

// ---------- 新建 / 编辑主档 ----------
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref()
const form = reactive({
  case_name: '',
  creator_id: '',
  parent_case_id: '',
  description: '',
  design_parameters_text: '',
})
const rules = {
  case_name: [{ required: true, message: '请输入算例名称', trigger: 'blur' }],
  creator_id: [{ required: true, message: '请选择创建人', trigger: 'change' }],
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, { case_name: '', creator_id: '', parent_case_id: '', description: '', design_parameters_text: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    case_name: row.case_name,
    creator_id: row.creator_id,
    parent_case_id: row.parent_case_id ?? '',
    description: row.description ?? '',
    design_parameters_text: '',
  })
  dialogVisible.value = true
}

async function save() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  saving.value = true
  try {
    if (isEdit.value) {
      await api.update(editingId.value, {
        case_name: form.case_name,
        description: form.description || null,
        parent_case_id: form.parent_case_id || null,
      })
    } else {
      let designParameters
      try {
        designParameters = toJsonOrNull(form.design_parameters_text)
      } catch {
        ElMessage.warning('初始设计参数不是合法的 JSON')
        return
      }
      await api.create({
        case_name: form.case_name,
        creator_id: form.creator_id,
        parent_case_id: form.parent_case_id || null,
        description: form.description || null,
        design_parameters: designParameters,
      })
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功（已生成 v1 版本）')
    dialogVisible.value = false
    await Promise.all([load(), reloadVersions()])
  } finally {
    saving.value = false
  }
}

// ---------- 版本抽屉 ----------
const drawerVisible = ref(false)
const currentCase = ref(null)
const versionsLoading = ref(false)

function openVersions(row) {
  currentCase.value = row
  drawerVisible.value = true
}

// 版本新建/编辑 Dialog
const versionDialogVisible = ref(false)
const versionSaving = ref(false)
const versionIsEdit = ref(false)
const versionFormRef = ref()
const versionForm = reactive({ id: null, version_no: '', status: 'draft', description: '', design_parameters_text: '' })
const versionRules = {
  version_no: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

function openVersionCreate() {
  versionIsEdit.value = false
  Object.assign(versionForm, { id: null, version_no: '', status: 'draft', description: '', design_parameters_text: '' })
  versionDialogVisible.value = true
}

function openVersionEdit(row) {
  versionIsEdit.value = true
  Object.assign(versionForm, {
    id: row.id,
    version_no: row.version_no,
    status: row.status,
    description: row.description ?? '',
    design_parameters_text: toJsonText(row.design_parameters),
  })
  versionDialogVisible.value = true
}

async function saveVersion() {
  const ok = await versionFormRef.value.validate().catch(() => false)
  if (!ok) return
  let designParameters
  try {
    designParameters = toJsonOrNull(versionForm.design_parameters_text)
  } catch {
    ElMessage.warning('设计参数不是合法的 JSON')
    return
  }
  versionSaving.value = true
  try {
    if (versionIsEdit.value) {
      await versionsApi.update(versionForm.id, {
        version_no: versionForm.version_no,
        status: versionForm.status,
        description: versionForm.description || null,
        design_parameters: designParameters,
      })
    } else {
      await versionsApi.create({
        case_id: currentCase.value.id,
        version_no: versionForm.version_no,
        status: versionForm.status,
        description: versionForm.description || null,
        design_parameters: designParameters,
      })
    }
    ElMessage.success(versionIsEdit.value ? '版本已更新' : '版本已创建')
    versionDialogVisible.value = false
    await reloadVersions()
  } finally {
    versionSaving.value = false
  }
}

async function removeVersion(row) {
  await ElMessageBox.confirm(`确认删除版本「${row.version_no}」吗？其产物与 CFD 任务将级联删除。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await versionsApi.remove(row.id)
  ElMessage.success('版本已删除')
  await reloadVersions()
}

// ---------- 产物管理 Dialog ----------
const artifactDialogVisible = ref(false)
const currentVersion = ref(null)
const artifacts = ref([])
const artifactsLoading = ref(false)

async function openArtifacts(row) {
  currentVersion.value = row
  artifactDialogVisible.value = true
  artifactsLoading.value = true
  try {
    const { data } = await artifactsApi.list({ case_version_id: row.id, limit: 500 })
    artifacts.value = data
  } finally {
    artifactsLoading.value = false
  }
}

const artifactSaving = ref(false)
const artifactFormRef = ref()
const artifactForm = reactive({ artifact_type: 'mesh', file_key: '', description: '' })
const artifactRules = {
  artifact_type: [{ required: true, message: '请选择产物类型', trigger: 'change' }],
  file_key: [{ required: true, message: '请输入 MinIO 对象 key', trigger: 'blur' }],
}

async function saveArtifact() {
  const ok = await artifactFormRef.value.validate().catch(() => false)
  if (!ok) return
  artifactSaving.value = true
  try {
    await artifactsApi.create({
      case_version_id: currentVersion.value.id,
      artifact_type: artifactForm.artifact_type,
      file_key: artifactForm.file_key,
      description: artifactForm.description || null,
    })
    ElMessage.success('产物已登记')
    Object.assign(artifactForm, { artifact_type: 'mesh', file_key: '', description: '' })
    const { data } = await artifactsApi.list({ case_version_id: currentVersion.value.id, limit: 500 })
    artifacts.value = data
  } finally {
    artifactSaving.value = false
  }
}

async function removeArtifact(row) {
  await ElMessageBox.confirm(`确认删除产物「${row.file_key}」吗？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await artifactsApi.remove(row.id)
  ElMessage.success('产物已删除')
  const { data } = await artifactsApi.list({ case_version_id: currentVersion.value.id, limit: 500 })
  artifacts.value = data
}

onMounted(async () => {
  await load()
  await reloadVersions()
  const { data } = await usersApi.list({ limit: 500 })
  users.value = data
})
</script>

<template>
  <el-card shadow="never">
    <div class="toolbar">
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
      <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
      <el-table-column label="版本数" width="90" align="center">
        <template #default="{ row }">{{ versionCount[row.id] || 0 }}</template>
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
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openVersions(row)">版本</el-button>
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

  <!-- 新建/编辑主档 -->
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑算例' : '新建算例'" width="640px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="算例名称" prop="case_name">
        <el-input v-model="form.case_name" maxlength="200" placeholder="如：某型燃机一级透平叶片优化" />
      </el-form-item>
      <el-form-item label="创建人" prop="creator_id">
        <el-select v-model="form.creator_id" filterable :disabled="isEdit" style="width: 260px" placeholder="选择用户">
          <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.email" :value="u.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="父算例">
        <el-select v-model="form.parent_case_id" filterable clearable style="width: 260px" placeholder="可选，衍生/复制来源">
          <el-option v-for="c in items.filter((x) => x.id !== editingId)" :key="c.id" :label="c.case_name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000" />
      </el-form-item>
      <el-form-item v-if="!isEdit" label="初始设计参数">
        <el-input
          v-model="form.design_parameters_text"
          type="textarea"
          :rows="8"
          placeholder='JSON 格式，写入 v1 版本，如 {"blade_count": 36, "chord_mm": 62.5}'
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>

  <!-- 版本抽屉 -->
  <el-drawer v-model="drawerVisible" :title="`算例版本 - ${currentCase?.case_name || ''}`" size="72%">
    <div class="drawer-toolbar">
      <el-button type="primary" @click="openVersionCreate">新建版本</el-button>
    </div>
    <el-table :data="versions.filter((v) => v.case_id === currentCase?.id)" border stripe v-loading="versionsLoading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="version_no" label="版本号" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="VERSION_STATUS_TAG[row.status]">{{ VERSION_STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
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
      <el-table-column prop="description" label="版本说明" min-width="150" show-overflow-tooltip />
      <el-table-column label="产物" width="80" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openArtifacts(row)">产物</el-button>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="165">
        <template #default="{ row }">{{ fmtTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openVersionEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="removeVersion(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 版本新建/编辑 -->
    <el-dialog v-model="versionDialogVisible" :title="versionIsEdit ? '编辑版本' : '新建版本'" width="640px" append-to-body destroy-on-close>
      <el-form ref="versionFormRef" :model="versionForm" :rules="versionRules" label-width="110px">
        <el-form-item label="版本号" prop="version_no">
          <el-input v-model="versionForm.version_no" maxlength="50" style="width: 200px" placeholder="如 v2 / v3（同算例内唯一）" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="versionForm.status" style="width: 200px">
            <el-option v-for="s in CASE_VERSION_STATUS" :key="s" :label="VERSION_STATUS_LABEL[s]" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本说明">
          <el-input v-model="versionForm.description" type="textarea" :rows="2" maxlength="2000" />
        </el-form-item>
        <el-form-item label="设计参数">
          <el-input v-model="versionForm.design_parameters_text" type="textarea" :rows="8" placeholder='JSON 格式，如 {"blade_count": 36}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="versionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="versionSaving" @click="saveVersion">保存</el-button>
      </template>
    </el-dialog>

    <!-- 产物管理 -->
    <el-dialog v-model="artifactDialogVisible" :title="`产物管理 - ${currentVersion?.version_no || ''}`" width="760px" append-to-body destroy-on-close>
      <el-table :data="artifacts" border stripe v-loading="artifactsLoading" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ ARTIFACT_TYPE_LABEL[row.artifact_type] || row.artifact_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_key" label="MinIO 对象 key" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="登记时间" width="165">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeArtifact(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-divider content-position="left">登记新产物</el-divider>
      <el-form ref="artifactFormRef" :model="artifactForm" :rules="artifactRules" label-width="110px">
        <el-form-item label="产物类型" prop="artifact_type">
          <el-select v-model="artifactForm.artifact_type" style="width: 200px">
            <el-option v-for="t in ARTIFACT_TYPES" :key="t" :label="ARTIFACT_TYPE_LABEL[t]" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="对象 key" prop="file_key">
          <el-input v-model="artifactForm.file_key" maxlength="500" placeholder="MinIO 对象 key，如 cases/1/v2/outputs/result.csv" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="artifactForm.description" maxlength="2000" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="artifactSaving" @click="saveArtifact">登记产物</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </el-drawer>
</template>

<style scoped>
.drawer-toolbar {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
