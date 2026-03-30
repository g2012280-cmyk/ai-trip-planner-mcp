import json
import logging
import os

from app.config import get_settings
from app.models.schemas import TripPlan, TripPlanRequest

logger = logging.getLogger(__name__)

ATTRACTION_PROMPT = """You are an attraction search specialist for Chinese cities.

Tool call format: [TOOL_CALL:amap_maps_text_search:keywords=attractions,city=CityName]

Always use the search tool — do not fabricate results.
Search based on user preferences ({preferences}) in {city}."""

WEATHER_PROMPT = """You are a weather information specialist.

Tool call format: [TOOL_CALL:amap_maps_weather:city=CityName]

Query the weather forecast for {city}."""

HOTEL_PROMPT = """You are a hotel recommendation specialist.

Tool call format: [TOOL_CALL:amap_maps_text_search:keywords=hotel,city=CityName]

Search for {accommodation} hotels in {city}."""

PLANNER_PROMPT = """You are a travel itinerary planner.

Return ONLY valid JSON in the following structure (no extra text):
{{
  "city": "City name",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "Day summary",
      "transportation": "Transport mode",
      "accommodation": "Where to stay",
      "hotel": {{
        "name": "Hotel name",
        "address": "Address",
        "price_range": "Price range",
        "rating": "4.5",
        "distance": "Distance from center",
        "type": "Hotel type",
        "estimated_cost": 300
      }},
      "attractions": [
        {{
          "name": "Attraction name",
          "address": "Address",
          "location": {{"longitude": 116.4, "latitude": 39.9}},
          "visit_duration": 120,
          "description": "Description",
          "category": "Category",
          "rating": 4.5,
          "ticket_price": 0
        }}
      ],
      "meals": [
        {{
          "type": "breakfast",
          "name": "Restaurant name",
          "description": "Description",
          "estimated_cost": 30
        }}
      ]
    }}
  ],
  "weather_info": [
    {{
      "date": "YYYY-MM-DD",
      "day_weather": "Sunny",
      "night_weather": "Cloudy",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "North",
      "wind_power": "Level 3"
    }}
  ],
  "overall_suggestions": "Travel tips",
  "budget": {{
    "total_attractions": 0,
    "total_hotels": 0,
    "total_meals": 0,
    "total_transportation": 0,
    "total": 0
  }}
}}

Rules:
- weather_info must cover every day; temperatures are plain integers (no °C)
- Plan 2-3 attractions per day, considering proximity and visit time
- Include breakfast, lunch, and dinner each day
- Provide practical travel tips in overall_suggestions
- Include a realistic budget breakdown"""


class TripPlannerAgent:
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
        except ImportError:
            logger.warning("hello_agents not installed, falling back to direct DeepSeek API")
            self.llm = None
            self._use_hello_agents = False

    def _setup_agents(self, settings):
        if not self._use_hello_agents:
            return

        from hello_agents.agents import SimpleAgent
        from hello_agents.tools import MCPTool

        self.mcp_tool = MCPTool(
            name="amap_mcp",
            command="npx",
            args=["-y", "@amap/amap-maps-mcp-server"],
            env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
            auto_expand=True,
        )

        self.attraction_agent = SimpleAgent(
            name="AttractionSearchAgent", llm=self.llm, system_prompt=ATTRACTION_PROMPT
        )
        self.attraction_agent.add_tool(self.mcp_tool)

        self.weather_agent = SimpleAgent(
            name="WeatherAgent", llm=self.llm, system_prompt=WEATHER_PROMPT
        )
        self.weather_agent.add_tool(self.mcp_tool)

        self.hotel_agent = SimpleAgent(
            name="HotelAgent", llm=self.llm, system_prompt=HOTEL_PROMPT
        )
        self.hotel_agent.add_tool(self.mcp_tool)

        self.planner_agent = SimpleAgent(
            name="PlannerAgent", llm=self.llm, system_prompt=PLANNER_PROMPT
        )

    def plan_trip(self, request: TripPlanRequest) -> TripPlan:
        if self._use_hello_agents:
            return self._plan_with_agents(request)
        return self._plan_direct(request)

    def _plan_with_agents(self, request: TripPlanRequest) -> TripPlan:
        logger.info(f"Searching attractions in {request.city}")
        attractions = self.attraction_agent.run(
            f"Search for {request.preferences} attractions in {request.city}"
        )

        logger.info(f"Fetching weather for {request.city}")
        weather = self.weather_agent.run(
            f"Get {request.days}-day weather forecast for {request.city}"
        )

        logger.info(f"Finding hotels in {request.city}")
        hotels = self.hotel_agent.run(
            f"Find {request.accommodation} hotels in {request.city}"
        )

        logger.info("Generating itinerary")
        query = self._build_planner_query(request, attractions, weather, hotels)
        result = self.planner_agent.run(query)
        return self._parse(result)

    def _plan_direct(self, request: TripPlanRequest) -> TripPlan:
        from openai import OpenAI
        settings = get_settings()

        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        prompt = f"""Plan a {request.days}-day trip to {request.city}.

Dates: {request.start_date} to {request.end_date}
Preferences: {request.preferences}
Budget: {request.budget}
Transportation: {request.transportation}
Accommodation: {request.accommodation}

{PLANNER_PROMPT}"""

        logger.info(f"Calling DeepSeek to plan trip to {request.city}")
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return self._parse(response.choices[0].message.content)

    def _build_planner_query(self, request, attractions, weather, hotels) -> str:
        return f"""Generate a {request.days}-day itinerary for {request.city}.

Trip details:
- Destination: {request.city}
- Dates: {request.start_date} to {request.end_date}
- Days: {request.days}
- Preferences: {request.preferences}
- Budget: {request.budget}
- Transportation: {request.transportation}
- Accommodation: {request.accommodation}

Attractions found:
{attractions}

Weather forecast:
{weather}

Hotels found:
{hotels}"""

    def _parse(self, response: str) -> TripPlan:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start == -1 or end <= start:
                raise ValueError("No JSON found in response")
            return TripPlan(**json.loads(response[start:end]))
        except Exception as e:
            logger.error(f"Failed to parse TripPlan: {e}\nResponse preview: {response[:300]}")
            raise
