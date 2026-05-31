<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { TripPlan, Attraction } from '@/types'

const router = useRouter()

// 从 router state 恢复数据
const rawState = history.state?.tripPlan
const tripPlan = reactive<TripPlan>(
  rawState ? JSON.parse(rawState) : ({} as TripPlan)
)

// 如果没有数据则返回首页
if (!rawState) {
  router.replace({ name: 'home' })
}

const editMode = ref(false)
const activeSection = ref('overview')
let map: any = null

// ── 地图初始化 ────────────────────────────────────────────────────────────────
const AMAP_KEY = '60ff8c58b093ad440e3de9d0a234a400'

const DAY_COLORS = ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1', '#13c2c2']

const initMap = async () => {
  try {
    const AMap = await AMapLoader.load({ key: AMAP_KEY, version: '1.4.15' })
    if (map) map.destroy()

    const firstAttr = tripPlan.days?.[0]?.attractions?.[0]
    const center = firstAttr
      ? [firstAttr.location.longitude, firstAttr.location.latitude]
      : [116.397128, 39.916527]

    map = new AMap.Map('amap-container', { zoom: 13, center })

    let infoWindow: any = null

    tripPlan.days?.forEach((day, di) => {
      const color = DAY_COLORS[di % DAY_COLORS.length]
      const path: [number, number][] = []

      day.attractions?.forEach((attr: Attraction, ai: number) => {
        const pos: [number, number] = [attr.location.longitude, attr.location.latitude]
        path.push(pos)

        // Numbered marker icon
        const marker = new AMap.Marker({
          position: pos,
          title: attr.name,
          content: `<div style="
            width:28px;height:28px;border-radius:50%;
            background:${color};color:#fff;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;font-weight:bold;
            box-shadow:0 2px 6px rgba(0,0,0,.3);
            cursor:pointer;
          ">${ai + 1}</div>`,
          offset: new AMap.Pixel(-14, -14),
        })

        // Click to show info popup
        marker.on('click', () => {
          if (infoWindow) infoWindow.close()
          infoWindow = new AMap.InfoWindow({
            content: `
              <div style="padding:10px 14px;min-width:200px;max-width:260px;font-size:13px;line-height:1.6">
                <div style="font-weight:600;font-size:14px;margin-bottom:4px">
                  <span style="background:${color};color:#fff;border-radius:4px;padding:1px 6px;margin-right:6px;font-size:11px">Day${di+1}-${ai+1}</span>
                  ${attr.name}
                </div>
                ${attr.category ? `<div style="color:#888;margin-bottom:2px">🏷️ ${attr.category}</div>` : ''}
                ${attr.rating ? `<div style="color:#faad14">★ ${attr.rating}</div>` : ''}
                <div style="color:#555;margin-top:4px">📍 ${attr.address || '—'}</div>
                <div style="color:#555">🕒 游览约 ${attr.visit_duration ?? '—'} 分钟 &nbsp;🎫 ${attr.ticket_price ?? 0} 元</div>
                ${attr.description ? `<div style="color:#888;margin-top:4px;font-size:12px">${attr.description}</div>` : ''}
              </div>`,
            offset: new AMap.Pixel(0, -30),
            isCustom: false,
          })
          infoWindow.open(map, pos)
        })

        map.add(marker)
      })

      // Route polyline for this day
      if (path.length > 1) {
        const polyline = new AMap.Polyline({
          path,
          strokeColor: color,
          strokeWeight: 3,
          strokeOpacity: 0.7,
          strokeStyle: 'dashed',
          lineJoin: 'round',
        })
        map.add(polyline)
      }
    })

    if (tripPlan.days?.length) map.setFitView()
  } catch (e) {
    console.warn('地图加载失败:', e)
  }
}

// ── 编辑功能 ──────────────────────────────────────────────────────────────────
let _backup: string = ''

const startEdit = () => {
  _backup = JSON.stringify(tripPlan)
  editMode.value = true
}

const saveEdit = () => {
  editMode.value = false
  message.success('修改已保存')
  initMap()
}

const cancelEdit = () => {
  const backup = JSON.parse(_backup)
  Object.assign(tripPlan, backup)
  editMode.value = false
}

const moveAttraction = (dayIdx: number, attrIdx: number, dir: 'up' | 'down') => {
  const attrs = tripPlan.days[dayIdx].attractions
  const target = dir === 'up' ? attrIdx - 1 : attrIdx + 1
  if (target >= 0 && target < attrs.length) {
    ;[attrs[attrIdx], attrs[target]] = [attrs[target], attrs[attrIdx]]
  }
}

const deleteAttraction = (dayIdx: number, attrIdx: number) => {
  tripPlan.days[dayIdx].attractions.splice(attrIdx, 1)
}

// ── 导出功能 ──────────────────────────────────────────────────────────────────
const captureFullContent = async (): Promise<HTMLCanvasElement | null> => {
  const el = document.getElementById('trip-plan-content')
  if (!el) return null

  // Clone into a detached div so flex/overflow constraints don't apply
  const wrapper = document.createElement('div')
  wrapper.style.cssText = 'position:fixed;top:0;left:-9999px;width:900px;background:#fff;z-index:-1'
  wrapper.innerHTML = el.innerHTML
  document.body.appendChild(wrapper)

  try {
    const canvas = await html2canvas(wrapper, { backgroundColor: '#fff', scale: 2, useCORS: true })
    return canvas
  } finally {
    document.body.removeChild(wrapper)
  }
}

const exportAsImage = async () => {
  try {
    const canvas = await captureFullContent()
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `${tripPlan.city}旅行计划.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    message.success('导出图片成功')
  } catch {
    message.error('导出失败，请截图保存')
  }
}

const exportAsPDF = async () => {
  try {
    const canvas = await captureFullContent()
    if (!canvas) return
    const pdf = new jsPDF('p', 'mm', 'a4')
    const imgW = 210
    const imgH = (canvas.height * imgW) / canvas.width
    // Split into multiple pages if content is taller than A4
    const pageH = 297
    let yOffset = 0
    while (yOffset < imgH) {
      if (yOffset > 0) pdf.addPage()
      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, -yOffset, imgW, imgH)
      yOffset += pageH
    }
    pdf.save(`${tripPlan.city}旅行计划.pdf`)
    message.success('导出 PDF 成功')
  } catch {
    message.error('导出失败，请截图保存')
  }
}

// ── 导航锚点 ──────────────────────────────────────────────────────────────────
const scrollTo = ({ key }: { key: string }) => {
  activeSection.value = key
  document.getElementById(key)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const weatherColumns = [
  { title: '日期', dataIndex: 'date', key: 'date' },
  { title: '白天', dataIndex: 'day_weather', key: 'day_weather' },
  { title: '夜间', dataIndex: 'night_weather', key: 'night_weather' },
  { title: '最高温(℃)', dataIndex: 'day_temp', key: 'day_temp' },
  { title: '最低温(℃)', dataIndex: 'night_temp', key: 'night_temp' },
  { title: '风向', dataIndex: 'wind_direction', key: 'wind_direction' },
  { title: '风力', dataIndex: 'wind_power', key: 'wind_power' }
]

onMounted(() => {
  if (rawState) initMap()
})
</script>

<template>
  <div v-if="tripPlan.city" class="result-container">
    <!-- 顶部操作栏 -->
    <div class="top-bar">
      <div>
        <a-button @click="router.push({ name: 'home' })">← 重新规划</a-button>
      </div>
      <h2 style="margin: 0">{{ tripPlan.city }} · {{ tripPlan.start_date }} ~ {{ tripPlan.end_date }}</h2>
      <div style="display: flex; gap: 8px">
        <template v-if="!editMode">
          <a-button type="default" @click="startEdit">编辑行程</a-button>
        </template>
        <template v-else>
          <a-button type="primary" @click="saveEdit">保存</a-button>
          <a-button @click="cancelEdit">取消</a-button>
        </template>
        <a-dropdown>
          <a-button>导出 ▼</a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="exportAsImage">导出为图片</a-menu-item>
              <a-menu-item @click="exportAsPDF">导出为 PDF</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>

    <a-layout style="min-height: calc(100vh - 64px)">
      <!-- 侧边导航 -->
      <a-layout-sider width="180" style="background: #fff; border-right: 1px solid #f0f0f0">
        <a-menu
          mode="inline"
          :selected-keys="[activeSection]"
          style="height: 100%; border-right: 0"
          @click="scrollTo"
        >
          <a-menu-item key="overview">📋 行程概览</a-menu-item>
          <a-menu-item key="budget">💰 预算明细</a-menu-item>
          <a-menu-item key="map">🗺️ 地图</a-menu-item>
          <a-menu-item key="days">📅 每日行程</a-menu-item>
          <a-menu-item key="weather">🌤️ 天气预报</a-menu-item>
        </a-menu>
      </a-layout-sider>

      <!-- 主内容区 -->
      <a-layout-content style="padding: 24px; overflow-y: auto" id="trip-plan-content">

        <!-- 概览 -->
        <div id="overview" style="margin-bottom: 24px">
          <a-card title="📋 行程概览">
            <p style="line-height: 1.8; color: #444">{{ tripPlan.overall_suggestions }}</p>
          </a-card>
        </div>

        <!-- 预算 -->
        <div id="budget" style="margin-bottom: 24px">
          <a-card v-if="tripPlan.budget" title="💰 预算明细">
            <a-row :gutter="16">
              <a-col :span="6">
                <a-statistic title="景点门票" :value="tripPlan.budget.total_attractions" suffix="元" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="酒店住宿" :value="tripPlan.budget.total_hotels" suffix="元" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="餐饮费用" :value="tripPlan.budget.total_meals" suffix="元" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="交通费用" :value="tripPlan.budget.total_transportation" suffix="元" />
              </a-col>
            </a-row>
            <a-divider />
            <div style="text-align: center">
              <a-statistic
                title="预估总费用"
                :value="tripPlan.budget.total"
                suffix="元"
                :value-style="{ color: '#cf1322', fontSize: '32px', fontWeight: 'bold' }"
              />
            </div>
          </a-card>
        </div>

        <!-- 地图 -->
        <div id="map" style="margin-bottom: 24px">
          <a-card title="🗺️ 景点地图">
            <div id="amap-container" style="height: 450px; border-radius: 8px; overflow: hidden" />
          </a-card>
        </div>

        <!-- 每日行程 -->
        <div id="days" style="margin-bottom: 24px">
          <a-card
            v-for="(day, di) in tripPlan.days"
            :key="di"
            :title="`📅 第 ${day.day_index + 1} 天 · ${day.date}`"
            style="margin-bottom: 16px"
          >
            <p style="color: #666; margin-bottom: 12px">{{ day.description }}</p>
            <a-tag color="blue">{{ day.transportation }}</a-tag>
            <a-tag color="green" style="margin-left: 8px">{{ day.accommodation }}</a-tag>

            <!-- 景点 -->
            <a-divider orientation="left">景点安排</a-divider>
            <div
              v-for="(attr, ai) in day.attractions"
              :key="ai"
              class="attraction-card"
            >
              <div class="attraction-header">
                <span class="attraction-index">{{ ai + 1 }}</span>
                <strong>{{ attr.name }}</strong>
                <a-tag v-if="attr.category" style="margin-left: 8px">{{ attr.category }}</a-tag>
                <span v-if="attr.rating" style="margin-left: 8px; color: #faad14">
                  ★ {{ attr.rating }}
                </span>
              </div>
              <div class="attraction-info">
                <span>📍 {{ attr.address }}</span>
                <span style="margin-left: 16px">🕒 {{ attr.visit_duration }} 分钟</span>
                <span style="margin-left: 16px">🎫 {{ attr.ticket_price ?? 0 }} 元</span>
              </div>
              <p style="color: #888; margin: 4px 0 0; font-size: 13px">{{ attr.description }}</p>
              <img
                v-if="attr.image_url"
                :src="attr.image_url"
                :alt="attr.name"
                style="max-width: 100%; border-radius: 6px; margin-top: 8px; max-height: 200px; object-fit: cover"
              />
              <div v-if="editMode" class="edit-actions">
                <a-button size="small" :disabled="ai === 0" @click="moveAttraction(di, ai, 'up')">↑ 上移</a-button>
                <a-button size="small" :disabled="ai === day.attractions.length - 1" @click="moveAttraction(di, ai, 'down')">↓ 下移</a-button>
                <a-button size="small" danger @click="deleteAttraction(di, ai)">删除</a-button>
              </div>
            </div>

            <!-- 餐饮 -->
            <a-divider orientation="left">餐饮安排</a-divider>
            <a-row :gutter="12">
              <a-col v-for="(meal, mi) in day.meals" :key="mi" :span="8">
                <a-card size="small" style="border-radius: 8px">
                  <div>
                    <a-tag :color="meal.type === 'breakfast' ? 'orange' : meal.type === 'lunch' ? 'green' : 'purple'">
                      {{ meal.type === 'breakfast' ? '早餐' : meal.type === 'lunch' ? '午餐' : meal.type === 'dinner' ? '晚餐' : '小吃' }}
                    </a-tag>
                  </div>
                  <strong>{{ meal.name }}</strong>
                  <p style="color: #888; font-size: 13px; margin: 4px 0 0">{{ meal.description }}</p>
                  <p style="color: #1677ff; margin: 4px 0 0">约 {{ meal.estimated_cost ?? 0 }} 元</p>
                </a-card>
              </a-col>
            </a-row>

            <!-- 酒店 -->
            <template v-if="day.hotel">
              <a-divider orientation="left">当晚住宿</a-divider>
              <a-card size="small" style="background: #fafafa; border-radius: 8px">
                <strong>🏨 {{ day.hotel.name }}</strong>
                <span style="margin-left: 12px; color: #faad14">★ {{ day.hotel.rating }}</span>
                <p style="margin: 4px 0 0; color: #666">{{ day.hotel.address }}</p>
                <p style="margin: 4px 0 0; color: #1677ff">约 {{ day.hotel.estimated_cost ?? 0 }} 元/晚</p>
              </a-card>
            </template>
          </a-card>
        </div>

        <!-- 天气 -->
        <div id="weather" style="margin-bottom: 24px">
          <a-card title="🌤️ 天气预报">
            <a-table
              :columns="weatherColumns"
              :data-source="tripPlan.weather_info"
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
.result-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 100;
}
.attraction-card {
  padding: 12px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  margin-bottom: 12px;
  background: #fafafa;
}
.attraction-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}
.attraction-index {
  display: inline-flex;
  width: 24px;
  height: 24px;
  background: #1677ff;
  color: #fff;
  border-radius: 50%;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  margin-right: 8px;
  flex-shrink: 0;
}
.attraction-info {
  font-size: 13px;
  color: #666;
}
.edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
