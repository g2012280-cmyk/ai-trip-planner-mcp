from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union


class Location(BaseModel):
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)


class Attraction(BaseModel):
    name: str
    address: str
    location: Location
    visit_duration: int = Field(..., gt=0, description="Suggested visit time in minutes")
    description: str
    category: Optional[str] = "Attraction"
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    image_url: Optional[str] = None
    ticket_price: int = Field(default=0, ge=0, description="Ticket price in CNY")


class Meal(BaseModel):
    type: str = Field(..., description="breakfast / lunch / dinner / snack")
    name: str
    address: Optional[str] = None
    location: Optional[Location] = None
    description: Optional[str] = None
    estimated_cost: int = Field(default=0, description="Estimated cost in CNY")


class Hotel(BaseModel):
    name: str
    address: str = ""
    location: Optional[Location] = None
    price_range: str = ""
    rating: Optional[Union[str, float]] = ""
    distance: str = ""
    type: str = ""
    estimated_cost: int = Field(default=0, description="Estimated cost per night in CNY")


class Budget(BaseModel):
    total_attractions: int = 0
    total_hotels: int = 0
    total_meals: int = 0
    total_transportation: int = 0
    total: int = 0


class WeatherInfo(BaseModel):
    date: str
    day_weather: str
    night_weather: str
    day_temp: int
    night_temp: int
    wind_direction: str
    wind_power: str

    @field_validator("day_temp", "night_temp", mode="before")
    def parse_temperature(cls, v):
        if isinstance(v, str):
            v = v.replace("°C", "").replace("℃", "").replace("°", "").strip()
            try:
                return int(v)
            except ValueError:
                return 0
        return v


class DayPlan(BaseModel):
    date: str
    day_index: int
    description: str
    transportation: str
    accommodation: str
    hotel: Optional[Hotel] = None
    attractions: List[Attraction] = []
    meals: List[Meal] = []


class TripPlan(BaseModel):
    city: str
    start_date: str
    end_date: str
    days: List[DayPlan] = []
    weather_info: List[WeatherInfo] = []
    overall_suggestions: str
    budget: Optional[Budget] = None


class TripPlanRequest(BaseModel):
    city: str
    start_date: str
    end_date: str
    days: int = Field(..., gt=0)
    preferences: str
    budget: str
    transportation: str
    accommodation: str
