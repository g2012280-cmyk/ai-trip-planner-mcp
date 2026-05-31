import asyncio
import json
import logging
import os
import re
from typing import Optional, Tuple

from app.config import get_settings
from app.models.schemas import TripPlan, TripPlanRequest

logger = logging.getLogger(__name__)

# ── Prompt 模板 ────────────────────────────────────────────────────────────────

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。

**工具调用格式:**
`[TOOL_CALL:amap_maps_text_search:keywords=景点,city=城市名]`

**示例:**
- `[TOOL_CALL:amap_maps_text_search:keywords=景点,city=北京]`
- `[TOOL_CALL:amap_maps_text_search:keywords=博物馆,city=上海]`

**重要:**
- 必须使用工具搜索，不要编造信息
- 根据用户偏好({preferences})搜索{city}的景点

**输出要求:**
在回答末尾，用以下格式列出各景点的经纬度（从搜索结果中提取，不要编造）：
SCENE_COORDS:经度1,纬度1;经度2,纬度2;经度3,纬度3
示例：SCENE_COORDS:116.3975,39.9087;116.4551,39.9279;116.3913,39.9067"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。

**工具调用格式:**
`[TOOL_CALL:amap_maps_weather:city=城市名]`

请查询{city}的天气信息。"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。

**工具调用格式:**
`[TOOL_CALL:amap_maps_text_search:keywords=酒店,city=城市名]`

请搜索{city}的{accommodation}酒店。"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。

**输出格式:**
严格按照以下JSON格式返回（不要输出任何其他内容）:
{{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "当日概述",
      "transportation": "交通方式",
      "accommodation": "住宿安排",
      "hotel": {{
        "name": "酒店名",
        "address": "地址",
        "price_range": "价格范围",
        "rating": "评分",
        "distance": "距离",
        "type": "类型",
        "estimated_cost": 300
      }},
      "attractions": [
        {{
          "name": "景点名",
          "address": "地址",
          "location": {{"longitude": 116.4, "latitude": 39.9}},
          "visit_duration": 120,
          "description": "描述",
          "category": "景点",
          "rating": 4.5,
          "ticket_price": 0
        }}
      ],
      "meals": [
        {{
          "type": "breakfast",
          "name": "餐厅名",
          "description": "描述",
          "estimated_cost": 30
        }}
      ]
    }}
  ],
  "weather_info": [
    {{
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "北风",
      "wind_power": "3级"
    }}
  ],
  "overall_suggestions": "总体建议",
  "budget": {{
    "total_attractions": 0,
    "total_hotels": 0,
    "total_meals": 0,
    "total_transportation": 0,
    "total": 0
  }}
}}

**规划要求:**
1. weather_info 必须包含每天的天气，温度为纯整数（不带°C）
2. 每天安排 2-3 个景点，考虑景点距离和游览时间
3. 包含早中晚三餐
4. 提供实用建议
5. 包含详细预算明细"""


# ── 坐标提取 ────────────────────────────────────────────────────────────────────

def _extract_centroid(text: str) -> Optional[Tuple[float, float]]:
    """从景点 Agent 输出的 SCENE_COORDS 块中提取坐标并计算中心点。"""
    match = re.search(r'SCENE_COORDS:([0-9.,;]+)', text)
    if not match:
        return None
    try:
        pairs = [p.strip() for p in match.group(1).split(';') if p.strip()]
        coords = []
        for p in pairs:
            parts = p.split(',')
            if len(parts) == 2:
                lng, lat = float(parts[0]), float(parts[1])
                if 73 < lng < 135 and 15 < lat < 55:  # 中国大陆坐标范围校验
                    coords.append((lng, lat))
        if not coords:
            return None
        return (
            sum(c[0] for c in coords) / len(coords),
            sum(c[1] for c in coords) / len(coords),
        )
    except Exception as e:
        logger.warning(f"坐标解析失败: {e}")
        return None


# ── Agent 系统 ──────────────────────────────────────────────────────────────────

class TripPlannerAgent:
    """旅行规划多 Agent 系统 v2
    改进：
    - AttractionAgent + WeatherAgent 并行执行（无数据依赖）
    - 从景点搜索结果提取真实坐标中心点
    - HotelAgent 依赖景点坐标，推荐地理位置匹配的酒店
    """

    def __init__(self):
        settings = get_settings()
        self._setup_llm(settings)
        self._setup_agents(settings)

    def _setup_llm(self, settings):
        try:
            from hello_agents.llm import HelloAgentsLLM
            os.environ.setdefault("OPENAI_API_KEY", settings.deepseek_api_key)
            os.environ.setdefault("OPENAI_BASE_URL", settings.deepseek_base_url)
            os.environ.setdefault("OPENAI_MODEL", settings.deepseek_model)
            self.llm = HelloAgentsLLM()
            self._use_hello_agents = True
            logger.info("使用 hello_agents + DeepSeek")
        except ImportError:
            logger.warning("hello_agents 未安装，降级为直接调用 DeepSeek API")
            self.llm = None
            self._use_hello_agents = False

    def _setup_agents(self, settings):
        if not self._use_hello_agents:
            return

        from hello_agents.agents import SimpleAgent
        from hello_agents.tools import MCPTool

        # 并行 Agent 各用独立 MCP 实例，避免共享进程的并发冲突
        def _make_mcp(name: str) -> "MCPTool":
            return MCPTool(
                name=name,
                command="npx",
                args=["-y", "@amap/amap-maps-mcp-server"],
                env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
                auto_expand=True,
            )

        self.attraction_agent = SimpleAgent(
            name="AttractionSearchAgent",
            llm=self.llm,
            system_prompt=ATTRACTION_AGENT_PROMPT,
        )
        self.attraction_agent.add_tool(_make_mcp("amap_attraction"))

        self.weather_agent = SimpleAgent(
            name="WeatherQueryAgent",
            llm=self.llm,
            system_prompt=WEATHER_AGENT_PROMPT,
        )
        self.weather_agent.add_tool(_make_mcp("amap_weather"))

        self.hotel_agent = SimpleAgent(
            name="HotelAgent",
            llm=self.llm,
            system_prompt=HOTEL_AGENT_PROMPT,
        )
        self.hotel_agent.add_tool(_make_mcp("amap_hotel"))

        self.planner_agent = SimpleAgent(
            name="PlannerAgent",
            llm=self.llm,
            system_prompt=PLANNER_AGENT_PROMPT,
        )

    # ── 主入口 ──────────────────────────────────────────────────────────────────

    async def plan_trip(self, request: TripPlanRequest) -> TripPlan:
        if self._use_hello_agents:
            return await self._plan_with_hello_agents(request)
        return await asyncio.to_thread(self._plan_with_direct_api, request)

    # ── hello_agents 路径 ───────────────────────────────────────────────────────

    async def _plan_with_hello_agents(self, request: TripPlanRequest) -> TripPlan:
        # Step 1: 景点 + 天气并行（互相无依赖）
        logger.info(f"[parallel] 并行搜索景点 + 查询天气: {request.city}")
        attraction_resp, weather_resp = await asyncio.gather(
            asyncio.to_thread(
                self.attraction_agent.run,
                f"请搜索{request.city}的{request.preferences}景点",
            ),
            asyncio.to_thread(
                self.weather_agent.run,
                f"请查询{request.city}的{request.days}天天气",
            ),
        )

        # Step 2: 提取景点坐标中心，指导酒店搜索
        centroid = _extract_centroid(attraction_resp)
        if centroid:
            lng, lat = centroid
            logger.info(f"[centroid] 景点中心坐标: ({lng:.4f}, {lat:.4f})")
            hotel_query = (
                f"请搜索{request.city}的{request.accommodation}酒店，"
                f"优先推荐靠近景点集中区域（中心坐标约 {lng:.4f},{lat:.4f}）的酒店"
            )
        else:
            logger.warning("[centroid] 未能提取景点坐标，使用默认搜索")
            hotel_query = f"请搜索{request.city}的{request.accommodation}酒店"

        logger.info(f"[serial] 推荐酒店: {request.city}")
        hotel_resp = await asyncio.to_thread(self.hotel_agent.run, hotel_query)

        # Step 3: PlannerAgent 汇总
        logger.info("[serial] 生成行程计划")
        planner_resp = await asyncio.to_thread(
            self.planner_agent.run,
            self._build_planner_query(request, attraction_resp, weather_resp, hotel_resp),
        )
        return self._parse_trip_plan(planner_resp)

    # ── 直接调用 DeepSeek API 路径（fallback）──────────────────────────────────

    def _plan_with_direct_api(self, request: TripPlanRequest) -> TripPlan:
        from openai import OpenAI
        settings = get_settings()
        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        prompt = f"""请为以下旅行需求生成详细计划：
目的地: {request.city}
日期: {request.start_date} 至 {request.end_date}（共{request.days}天）
偏好: {request.preferences}
预算: {request.budget}
交通方式: {request.transportation}
住宿类型: {request.accommodation}

{PLANNER_AGENT_PROMPT}
"""
        logger.info(f"[direct_api] 调用 DeepSeek 生成 {request.city} 旅行计划")
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return self._parse_trip_plan(response.choices[0].message.content)

    # ── 工具方法 ────────────────────────────────────────────────────────────────

    def _build_planner_query(self, request, attraction_response, weather_response, hotel_response):
        return f"""
请根据以下信息生成{request.city}的{request.days}日旅行计划：

**用户需求:**
- 目的地: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.days}天
- 偏好: {request.preferences}
- 预算: {request.budget}
- 交通方式: {request.transportation}
- 住宿类型: {request.accommodation}

**景点信息:**
{attraction_response}

**天气信息:**
{weather_response}

**酒店信息:**
{hotel_response}

请生成详细的旅行计划，包括每天的景点安排、餐饮推荐、住宿信息和预算明细。
"""

    def _parse_trip_plan(self, response: str) -> TripPlan:
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start == -1 or json_end <= json_start:
                raise ValueError("响应中未找到 JSON")
            data = json.loads(response[json_start:json_end])
            return TripPlan(**data)
        except Exception as e:
            logger.error(f"解析 TripPlan 失败: {e}\n原始响应: {response[:500]}")
            raise
