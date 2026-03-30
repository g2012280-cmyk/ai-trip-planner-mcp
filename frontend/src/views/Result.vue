<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { TripPlan, Attraction } from '@/types'

const router = useRouter()
const raw = history.state?.plan
const trip = reactive<TripPlan>(raw ? JSON.parse(raw) : ({} as TripPlan))

if (!raw) router.replace({ name: 'home' })

const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || '60ff8c58b093ad440e3de9d0a234a400'
const editMode = ref(false)
const activeKey = ref('overview')
let map: any = null
let backup = ''

const mealLabel = (type: string) => ({ breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner', snack: 'Snack' }[type] ?? type)
const mealColor = (type: string) => ({ breakfast: 'orange', lunch: 'green', dinner: 'purple', snack: 'cyan' }[type] ?? 'default')

const initMap = async () => {
  try {
    const AMap = await AMapLoader.load({ key: AMAP_KEY, version: '2.0' })
    if (map) map.destroy()

    const first = trip.days?.[0]?.attractions?.[0]
    map = new AMap.Map('map', {
      zoom: 13,
      center: first ? [first.location.longitude, first.location.latitude] : [116.397, 39.916],
    })

    trip.days?.forEach((day, di) => {
      day.attractions?.forEach((a: Attraction, ai: number) => {
        new AMap.Marker({
          map,
          position: [a.location.longitude, a.location.latitude],
          title: a.name,
          label: {
            content: `<span style="background:#1677ff;color:#fff;padding:2px 7px;border-radius:4px;font-size:12px">D${di+1}-${ai+1} ${a.name}</span>`,
            direction: 'top',
          },
        })
      })
    })

    if (trip.days?.length) map.setFitView()
  } catch (e) {
    console.warn('Map failed to load:', e)
  }
}

const startEdit = () => { backup = JSON.stringify(trip); editMode.value = true }
const saveEdit = () => { editMode.value = false; message.success('Changes saved'); initMap() }
const cancelEdit = () => { Object.assign(trip, JSON.parse(backup)); editMode.value = false }

const move = (di: number, ai: number, dir: 'up' | 'down') => {
  const arr = trip.days[di].attractions
  const to = dir === 'up' ? ai - 1 : ai + 1
  if (to >= 0 && to < arr.length) [arr[ai], arr[to]] = [arr[to], arr[ai]]
}
const remove = (di: number, ai: number) => trip.days[di].attractions.splice(ai, 1)

const exportImage = async () => {
  const el = document.getElementById('content')
  if (!el) return
  try {
    const c = await html2canvas(el, { backgroundColor: '#fff', scale: 2, useCORS: true })
    const a = document.createElement('a')
    a.download = `${trip.city}-trip.png`
    a.href = c.toDataURL('image/png')
    a.click()
    message.success('Image exported')
  } catch { message.error('Export failed — try a screenshot instead') }
}

const exportPDF = async () => {
  const el = document.getElementById('content')
  if (!el) return
  try {
    const c = await html2canvas(el, { backgroundColor: '#fff', scale: 2, useCORS: true })
    const pdf = new jsPDF('p', 'mm', 'a4')
    const w = 210
    pdf.addImage(c.toDataURL('image/png'), 'PNG', 0, 0, w, (c.height * w) / c.width)
    pdf.save(`${trip.city}-trip.pdf`)
    message.success('PDF exported')
  } catch { message.error('Export failed — try a screenshot instead') }
}

const scrollTo = ({ key }: { key: string }) => {
  activeKey.value = key
  document.getElementById(key)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const weatherCols = [
  { title: 'Date', dataIndex: 'date' },
  { title: 'Day', dataIndex: 'day_weather' },
  { title: 'Night', dataIndex: 'night_weather' },
  { title: 'High (°C)', dataIndex: 'day_temp' },
  { title: 'Low (°C)', dataIndex: 'night_temp' },
  { title: 'Wind', dataIndex: 'wind_direction' },
  { title: 'Force', dataIndex: 'wind_power' },
]

onMounted(() => { if (raw) initMap() })
</script>

<template>
  <div v-if="trip.city" class="page">

    <!-- Top bar -->
    <div class="topbar">
      <a-button @click="router.push({ name: 'home' })">← New trip</a-button>
      <h2>{{ trip.city }} &nbsp;·&nbsp; {{ trip.start_date }} → {{ trip.end_date }}</h2>
      <div class="actions">
        <template v-if="!editMode">
          <a-button @click="startEdit">Edit</a-button>
        </template>
        <template v-else>
          <a-button type="primary" @click="saveEdit">Save</a-button>
          <a-button @click="cancelEdit">Cancel</a-button>
        </template>
        <a-dropdown>
          <a-button>Export ▾</a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="exportImage">Save as image</a-menu-item>
              <a-menu-item @click="exportPDF">Save as PDF</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>

    <a-layout style="min-height:calc(100vh - 56px)">

      <!-- Sidebar nav -->
      <a-layout-sider width="160" style="background:#fff;border-right:1px solid #f0f0f0">
        <a-menu mode="inline" :selected-keys="[activeKey]" style="border:0;height:100%" @click="scrollTo">
          <a-menu-item key="overview">Overview</a-menu-item>
          <a-menu-item key="budget">Budget</a-menu-item>
          <a-menu-item key="map">Map</a-menu-item>
          <a-menu-item key="days">Itinerary</a-menu-item>
          <a-menu-item key="weather">Weather</a-menu-item>
        </a-menu>
      </a-layout-sider>

      <!-- Main content -->
      <a-layout-content style="padding:24px;overflow-y:auto" id="content">

        <div id="overview" class="section">
          <a-card title="Overview">
            <p style="line-height:1.8;color:#444">{{ trip.overall_suggestions }}</p>
          </a-card>
        </div>

        <div id="budget" class="section">
          <a-card v-if="trip.budget" title="Budget breakdown">
            <a-row :gutter="16">
              <a-col :span="6"><a-statistic title="Attractions" :value="trip.budget.total_attractions" suffix="¥" /></a-col>
              <a-col :span="6"><a-statistic title="Hotels" :value="trip.budget.total_hotels" suffix="¥" /></a-col>
              <a-col :span="6"><a-statistic title="Food" :value="trip.budget.total_meals" suffix="¥" /></a-col>
              <a-col :span="6"><a-statistic title="Transport" :value="trip.budget.total_transportation" suffix="¥" /></a-col>
            </a-row>
            <a-divider />
            <div style="text-align:center">
              <a-statistic
                title="Estimated total"
                :value="trip.budget.total"
                suffix="¥"
                :value-style="{ color:'#cf1322', fontSize:'32px', fontWeight:'bold' }"
              />
            </div>
          </a-card>
        </div>

        <div id="map" class="section">
          <a-card title="Map">
            <div id="map" style="height:440px;border-radius:8px;overflow:hidden" />
          </a-card>
        </div>

        <div id="days" class="section">
          <a-card
            v-for="(day, di) in trip.days"
            :key="di"
            :title="`Day ${day.day_index + 1} — ${day.date}`"
            style="margin-bottom:16px"
          >
            <p style="color:#666;margin-bottom:10px">{{ day.description }}</p>
            <a-tag color="blue">{{ day.transportation }}</a-tag>
            <a-tag color="green">{{ day.accommodation }}</a-tag>

            <a-divider orientation="left">Attractions</a-divider>
            <div v-for="(a, ai) in day.attractions" :key="ai" class="spot">
              <div class="spot-header">
                <span class="spot-num">{{ ai + 1 }}</span>
                <strong>{{ a.name }}</strong>
                <a-tag v-if="a.category" style="margin-left:8px">{{ a.category }}</a-tag>
                <span v-if="a.rating" style="margin-left:8px;color:#faad14">★ {{ a.rating }}</span>
              </div>
              <div class="spot-meta">
                <span>📍 {{ a.address }}</span>
                <span>· {{ a.visit_duration }} min</span>
                <span>· ¥{{ a.ticket_price ?? 0 }} entry</span>
              </div>
              <p style="color:#999;font-size:13px;margin:4px 0 0">{{ a.description }}</p>
              <img v-if="a.image_url" :src="a.image_url" :alt="a.name" class="spot-img" />
              <div v-if="editMode" class="spot-edit">
                <a-button size="small" :disabled="ai === 0" @click="move(di, ai, 'up')">↑</a-button>
                <a-button size="small" :disabled="ai === day.attractions.length - 1" @click="move(di, ai, 'down')">↓</a-button>
                <a-button size="small" danger @click="remove(di, ai)">Remove</a-button>
              </div>
            </div>

            <a-divider orientation="left">Meals</a-divider>
            <a-row :gutter="12">
              <a-col v-for="(m, mi) in day.meals" :key="mi" :span="8">
                <a-card size="small" style="border-radius:8px">
                  <a-tag :color="mealColor(m.type)">{{ mealLabel(m.type) }}</a-tag>
                  <div style="margin-top:6px"><strong>{{ m.name }}</strong></div>
                  <p style="color:#999;font-size:13px;margin:4px 0 0">{{ m.description }}</p>
                  <p style="color:#1677ff;margin:4px 0 0">~¥{{ m.estimated_cost ?? 0 }}</p>
                </a-card>
              </a-col>
            </a-row>

            <template v-if="day.hotel">
              <a-divider orientation="left">Accommodation</a-divider>
              <a-card size="small" style="background:#fafafa;border-radius:8px">
                <strong>{{ day.hotel.name }}</strong>
                <span v-if="day.hotel.rating" style="margin-left:10px;color:#faad14">★ {{ day.hotel.rating }}</span>
                <p style="margin:4px 0 0;color:#666">{{ day.hotel.address }}</p>
                <p style="margin:4px 0 0;color:#1677ff">~¥{{ day.hotel.estimated_cost ?? 0 }} / night</p>
              </a-card>
            </template>
          </a-card>
        </div>

        <div id="weather" class="section">
          <a-card title="Weather forecast">
            <a-table
              :columns="weatherCols"
              :data-source="trip.weather_info"
              :pagination="false"
              size="small"
              :row-key="(r: any) => r.date"
            />
          </a-card>
        </div>

      </a-layout-content>
    </a-layout>
  </div>
</template>

<style scoped>
.page { height: 100vh; display: flex; flex-direction: column; }
.topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 24px; background: #fff; border-bottom: 1px solid #f0f0f0;
  position: sticky; top: 0; z-index: 100;
}
.topbar h2 { margin: 0; font-size: 16px; }
.actions { display: flex; gap: 8px; }
.section { margin-bottom: 24px; }
.spot {
  padding: 12px; border: 1px solid #f0f0f0;
  border-radius: 8px; margin-bottom: 10px; background: #fafafa;
}
.spot-header { display: flex; align-items: center; margin-bottom: 4px; }
.spot-num {
  width: 22px; height: 22px; background: #1677ff; color: #fff;
  border-radius: 50%; display: inline-flex; align-items: center;
  justify-content: center; font-size: 11px; font-weight: 700;
  margin-right: 8px; flex-shrink: 0;
}
.spot-meta { font-size: 13px; color: #888; display: flex; gap: 8px; flex-wrap: wrap; }
.spot-img { max-width: 100%; border-radius: 6px; margin-top: 8px; max-height: 180px; object-fit: cover; }
.spot-edit { display: flex; gap: 6px; margin-top: 8px; }
</style>
