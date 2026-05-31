<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { generateTripPlan } from '@/services/api'
import type { TripPlanRequest } from '@/types'

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const formData = ref<TripPlanRequest>({
  city: '',
  start_date: '',
  end_date: '',
  days: 3,
  preferences: '历史文化',
  budget: '中等',
  transportation: '公共交通',
  accommodation: '经济型酒店'
})

// 日期选择后自动计算天数
const handleDateChange = () => {
  if (formData.value.start_date && formData.value.end_date) {
    const start = dayjs(formData.value.start_date)
    const end = dayjs(formData.value.end_date)
    const diff = end.diff(start, 'day')
    if (diff > 0) formData.value.days = diff
  }
}

const disabledEndDate = computed(() => (current: dayjs.Dayjs) => {
  if (!formData.value.start_date) return false
  return current.isBefore(dayjs(formData.value.start_date), 'day')
})

const handleSubmit = async () => {
  if (!formData.value.city.trim()) {
    message.warning('请输入目的地城市')
    return
  }
  if (!formData.value.start_date || !formData.value.end_date) {
    message.warning('请选择出行日期')
    return
  }

  loading.value = true
  loadingProgress.value = 0

  const steps = [
    { progress: 25, status: '🔍 正在搜索景点...' },
    { progress: 50, status: '🌤️ 正在查询天气...' },
    { progress: 75, status: '🏨 正在推荐酒店...' },
    { progress: 90, status: '📋 正在生成行程计划...' }
  ]
  let stepIdx = 0
  const progressTimer = setInterval(() => {
    if (stepIdx < steps.length) {
      loadingProgress.value = steps[stepIdx].progress
      loadingStatus.value = steps[stepIdx].status
      stepIdx++
    }
  }, 4000)

  try {
    const tripPlan = await generateTripPlan(formData.value)
    clearInterval(progressTimer)
    loadingProgress.value = 100
    loadingStatus.value = '✅ 行程生成完毕！'

    // 通过 router state 传递数据
    router.push({ name: 'result', state: { tripPlan: JSON.stringify(tripPlan) } })
  } catch (err: any) {
    clearInterval(progressTimer)
    message.error(`生成失败：${err.response?.data?.detail || '请稍后重试'}`)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="home-container">
    <div class="page-header">
      <h1 class="page-title">✈️ 智能旅行助手</h1>
      <p class="page-subtitle">基于多 Agent 的 AI 个性化旅行规划</p>
    </div>

    <a-card class="form-card">
      <a-form :model="formData" layout="vertical" @finish="handleSubmit">

        <a-row :gutter="16">
          <a-col :span="24">
            <a-form-item label="目的地城市" name="city" :rules="[{ required: true, message: '请输入目的地' }]">
              <a-input v-model:value="formData.city" placeholder="例：北京、上海、成都" size="large" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="出发日期" name="start_date" :rules="[{ required: true, message: '请选择出发日期' }]">
              <a-date-picker
                v-model:value="formData.start_date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
                size="large"
                @change="handleDateChange"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="返回日期" name="end_date" :rules="[{ required: true, message: '请选择返回日期' }]">
              <a-date-picker
                v-model:value="formData.end_date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
                size="large"
                :disabled-date="disabledEndDate"
                @change="handleDateChange"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="偏好类型" name="preferences">
              <a-select v-model:value="formData.preferences" size="large">
                <a-select-option value="历史文化">历史文化</a-select-option>
                <a-select-option value="自然风光">自然风光</a-select-option>
                <a-select-option value="美食购物">美食购物</a-select-option>
                <a-select-option value="亲子家庭">亲子家庭</a-select-option>
                <a-select-option value="户外探险">户外探险</a-select-option>
                <a-select-option value="休闲度假">休闲度假</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="预算范围" name="budget">
              <a-select v-model:value="formData.budget" size="large">
                <a-select-option value="低（经济型）">低（经济型）</a-select-option>
                <a-select-option value="中等">中等</a-select-option>
                <a-select-option value="高（品质型）">高（品质型）</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="交通方式" name="transportation">
              <a-select v-model:value="formData.transportation" size="large">
                <a-select-option value="公共交通">公共交通</a-select-option>
                <a-select-option value="自驾">自驾</a-select-option>
                <a-select-option value="步行为主">步行为主</a-select-option>
                <a-select-option value="打车为主">打车为主</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="住宿类型" name="accommodation">
              <a-select v-model:value="formData.accommodation" size="large">
                <a-select-option value="经济型酒店">经济型酒店</a-select-option>
                <a-select-option value="中档酒店">中档酒店</a-select-option>
                <a-select-option value="豪华酒店">豪华酒店</a-select-option>
                <a-select-option value="民宿">民宿</a-select-option>
                <a-select-option value="青旅">青旅</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            :loading="loading"
            block
            style="height: 48px; font-size: 16px"
          >
            {{ loading ? '生成中...' : '开始智能规划 ✨' }}
          </a-button>
        </a-form-item>

        <div v-if="loading" style="margin-top: 16px">
          <a-progress :percent="loadingProgress" status="active" />
          <p style="text-align: center; margin-top: 8px; color: #666">{{ loadingStatus }}</p>
        </div>

      </a-form>
    </a-card>
  </div>
</template>

<style scoped>
.home-container {
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 20px;
}
.page-header {
  text-align: center;
  margin-bottom: 32px;
}
.page-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #1677ff, #36cfc9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.page-subtitle {
  font-size: 16px;
  color: #888;
}
.form-card {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
</style>
