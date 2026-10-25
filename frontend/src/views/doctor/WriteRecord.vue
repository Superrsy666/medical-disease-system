<template>
  <div class="page">
    <h2>开具病历</h2>
    <el-card style="max-width:800px">
      <el-form :model="form" label-width="100px" ref="formRef">
        <el-form-item label="选择患者" prop="patientId" :rules="[{ required: true, message: '请选择患者' }]">
          <el-select v-model="form.patientId" filterable placeholder="搜索患者姓名/用户名" style="width:100%">
            <el-option v-for="p in patients" :key="p.id" :label="`${p.realName || p.username}`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="就诊日期" prop="visitDate" :rules="[{ required: true, message: '请选择日期' }]">
          <el-date-picker v-model="form.visitDate" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="主诉">
          <el-input v-model="form.chiefComplaint" type="textarea" :rows="2" placeholder="患者主诉" />
        </el-form-item>
        <el-form-item label="诊断疾病" prop="diagnosis" :rules="[{ required: true, message: '请填写诊断' }]">
          <el-autocomplete v-model="form.diagnosis" :fetch-suggestions="searchDisease"
            placeholder="输入疾病名称搜索" style="width:100%" />
        </el-form-item>
        <el-form-item label="诊断详情">
          <el-input v-model="form.diagnosisDetail" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="处方药品">
          <div v-for="(item, idx) in form.prescription" :key="idx" class="presc-row">
            <el-select v-model="item.drugId" filterable placeholder="选择药品" style="width:200px"
              @change="(val) => onDrugChange(val, idx)">
              <el-option v-for="d in drugs" :key="d.id" :label="d.drugName" :value="d.id" />
            </el-select>
            <el-input v-model="item.dosage" placeholder="用法用量，如：口服 每次1片 每日1次" style="flex:1;margin-left:8px" />
            <el-button type="danger" icon="Delete" circle style="margin-left:8px" @click="form.prescription.splice(idx,1)" />
          </div>
          <el-button type="primary" size="small" @click="addDrug" style="margin-top:8px">+ 添加药品</el-button>
        </el-form-item>
        <el-form-item label="就诊状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">初诊</el-radio>
            <el-radio :value="2">复诊</el-radio>
            <el-radio :value="3">痊愈</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">提交病历</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { getPatients } from '../../api/patient'
import { getDrugs } from '../../api/drug'
import { getDiseases } from '../../api/disease'
import { createRecord } from '../../api/record'

const formRef = ref()
const loading = ref(false)
const patients = ref([])
const drugs = ref([])

const form = reactive({
  patientId: null,
  visitDate: '',
  chiefComplaint: '',
  diagnosis: '',
  diagnosisDetail: '',
  prescription: [],
  status: 1
})

const addDrug = () => form.prescription.push({ drugId: null, dosage: '' })

const onDrugChange = (val, idx) => {
  const drug = drugs.value.find(d => d.id === val)
  if (drug && !form.prescription[idx].dosage) {
    form.prescription[idx].dosage = `口服 每次1片 每日1次`
  }
}

const searchDisease = async (query, cb) => {
  if (!query) { cb([]); return }
  const res = await getDiseases({ keyword: query, page: 1, size: 10 })
  cb((res.data.records || []).map(d => ({ value: d.diseaseName, id: d.id })))
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await createRecord(form)
    ElMessage.success('病历提交成功')
    Object.assign(form, { patientId: null, visitDate: '', chiefComplaint: '', diagnosis: '', diagnosisDetail: '', prescription: [], status: 1 })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const [pr, dr] = await Promise.all([
    getPatients({ page: 1, size: 100 }),
    getDrugs({ page: 1, size: 200 })
  ])
  patients.value = pr.data.records || []
  drugs.value = dr.data.records || []
})
</script>

<style scoped>
.page { padding: 20px; }
.presc-row { display: flex; align-items: center; margin-bottom: 8px; }
</style>
