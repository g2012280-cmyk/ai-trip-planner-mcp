<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { generateTripPlan } from '@/services/api'
import type { TripPlanRequest } from '@/types'

const router = useRouter()
const loading = ref(false)
const progress = ref(0)
const progressStatus = ref('')

const form = ref<TripPlanRequest>({
  city: '',
  start_date: '',
  end_date: '',
  days: 3,
  preferences: 'History & Culture',
  budget: 'Mid-range',
  transportation: 'Public transit',
  accommodation: 'Budget hotel',
})

const recalcDays = () => {
  if (form.value.start_date && form.value.end_date) {
    const diff = dayjs(form.value.end_date).diff(dayjs(form.value.start_date), 'day')
    if (diff > 0) form.value.days = diff
  }
}

const disabledEnd = computed(() => (d: dayjs.Dayjs) =>
  form.value.start_date ? d.isBefore(dayjs(form.value.start_date), 'day') : false
)

const steps = [
  { at: 20, label: 'Searching attractions...' },
  { at: 45, label: 'Fetching weather forecast...' },
  { at: 65, label: 'Finding hotels...' },
  { at: 85, label: 'Building your itinerary...' },
]

const submit = async () => {
  if (!form.value.city.trim()) { message.warning('Please enter a destination'); return }
  if (!form.value.start_date || !form.value.end_date) { message.warning('Please select travel dates'); return }

  loading.value = true
  progress.value = 0

  let idx = 0
  const timer = setInterval(() => {
    if (idx < steps.length) {
      progress.value = steps[idx].at
      progressStatus.value = steps[idx].label
      idx++
    }
  }, 4000)

  try {
    const plan = await generateTripPlan(form.value)
    clearInterval(timer)
    progress.value = 100
    progressStatus.value = 'Done!'
    router.push({ name: 'result', state: { plan: JSON.stringify(plan) } })
  } catch (err: any) {
    clearInterval(timer)
    message.error(err.response?.data?.detail || 'Something went wrong, please try again')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <header class="hero">
      <h1>Trip Planner</h1>
      <p>AI-powered itinerary generation for cities across China</p>
    </header>

    <a-card class="card">
      <a-form :model="form" layout="vertical" @finish="submit">

        <a-form-item label="Destination" name="city" :rules="[{ required: true, message: 'Required' }]">
          <a-input v-model:value="form.city" placeholder="e.g. Beijing, Shanghai, Chengdu" size="large" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Start date" name="start_date" :rules="[{ required: true, message: 'Required' }]">
              <a-date-picker v-model:value="form.start_date" value-format="YYYY-MM-DD" style="width:100%" size="large" @change="recalcDays" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="End date" name="end_date" :rules="[{ required: true, message: 'Required' }]">
              <a-date-picker v-model:value="form.end_date" value-format="YYYY-MM-DD" style="width:100%" size="large" :disabled-date="disabledEnd" @change="recalcDays" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Interests" name="preferences">
              <a-select v-model:value="form.preferences" size="large">
                <a-select-option value="History & Culture">History & Culture</a-select-option>
                <a-select-option value="Nature & Scenery">Nature & Scenery</a-select-option>
                <a-select-option value="Food & Shopping">Food & Shopping</a-select-option>
                <a-select-option value="Family & Kids">Family & Kids</a-select-option>
                <a-select-option value="Outdoor Adventure">Outdoor Adventure</a-select-option>
                <a-select-option value="Relaxation">Relaxation</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Budget" name="budget">
              <a-select v-model:value="form.budget" size="large">
                <a-select-option value="Budget">Budget</a-select-option>
                <a-select-option value="Mid-range">Mid-range</a-select-option>
                <a-select-option value="Premium">Premium</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Getting around" name="transportation">
              <a-select v-model:value="form.transportation" size="large">
                <a-select-option value="Public transit">Public transit</a-select-option>
                <a-select-option value="Self-drive">Self-drive</a-select-option>
                <a-select-option value="Walking">Walking</a-select-option>
                <a-select-option value="Taxi / Rideshare">Taxi / Rideshare</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Accommodation" name="accommodation">
              <a-select v-model:value="form.accommodation" size="large">
                <a-select-option value="Budget hotel">Budget hotel</a-select-option>
                <a-select-option value="Mid-range hotel">Mid-range hotel</a-select-option>
                <a-select-option value="Luxury hotel">Luxury hotel</a-select-option>
                <a-select-option value="Guesthouse / B&B">Guesthouse / B&B</a-select-option>
                <a-select-option value="Hostel">Hostel</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" :loading="loading" block style="height:48px;font-size:16px">
            {{ loading ? 'Generating...' : 'Plan my trip' }}
          </a-button>
        </a-form-item>

        <div v-if="loading">
          <a-progress :percent="progress" status="active" />
          <p class="progress-label">{{ progressStatus }}</p>
        </div>

      </a-form>
    </a-card>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 20px;
}
.hero {
  text-align: center;
  margin-bottom: 32px;
}
.hero h1 {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
}
.hero p {
  color: #888;
  font-size: 15px;
}
.card {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.07);
}
.progress-label {
  text-align: center;
  color: #888;
  margin-top: 8px;
  font-size: 13px;
}
</style>
