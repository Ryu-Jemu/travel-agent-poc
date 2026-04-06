from pydantic import BaseModel
from enum import Enum


class MobilityType(str, Enum):
    WALK = "walk"
    TRANSIT = "transit"
    CAR = "car"


# === 입력/출력 ===

class RecommendRequest(BaseModel):
    latitude: float
    longitude: float
    travel_date: str | None = None
    mobility_type: str = "walk"
    selected_tags: list[str] = []
    free_text: str = ""
    num_places: int = 5


class RecommendResponse(BaseModel):
    places: list["ScoredPlace"]
    route: "RouteResult | None" = None
    weather: "WeatherData | None" = None
    reasoning: str = ""


# === 파이프라인 중간 데이터 ===

class ParsedRequest(BaseModel):
    latitude: float
    longitude: float
    radius_m: int = 5000
    travel_date: str
    mobility_type: MobilityType
    selected_tags: list[str] = []
    free_text: str = ""
    num_places: int = 5


class WeatherData(BaseModel):
    condition: str
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    description: str
    is_bad_weather: bool
    icon: str


class PlaceInfo(BaseModel):
    content_id: str
    google_place_id: str | None = None
    name: str
    address: str
    latitude: float
    longitude: float
    content_type_id: int | None = None
    cat1: str | None = None
    cat2: str | None = None
    cat3: str | None = None
    overview: str | None = None
    indoor_outdoor: str = "unknown"


class FilteredPlace(PlaceInfo):
    indoor_outdoor: str
    filter_method: str


class ScoredPlace(BaseModel):
    content_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    indoor_outdoor: str
    tag_score: float = 0.0
    vector_score: float = 0.0
    weather_score: float = 0.0
    total_score: float = 0.0
    overview: str | None = None


class RouteLeg(BaseModel):
    from_place: str
    to_place: str
    distance_m: int
    duration_min: int


class RouteResult(BaseModel):
    ordered_places: list[ScoredPlace]
    legs: list[RouteLeg]
    total_distance_m: int
    total_duration_min: int
