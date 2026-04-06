# MAP AI 에이전트 — LangGraph 구현 가이드

> **작성일**: 2026-04-06  
> **대상 레포**: map-service-agent (FastAPI)  
> **현재 상태**: 소스코드 없음 (Dockerfile, README만 존재)  
> **목적**: LangGraph PoC 구현을 위한 실행 가능한 참고 문서

---

## 목차

1. [아키텍처 결정](#1-아키텍처-결정)
2. [그래프 구조](#2-그래프-구조)
3. [AgentState 설계](#3-agentstate-설계)
4. [Pydantic 스키마](#4-pydantic-스키마)
5. [노드별 구현 상세](#5-노드별-구현-상세)
6. [그래프 조립](#6-그래프-조립)
7. [FastAPI 엔드포인트](#7-fastapi-엔드포인트)
8. [Gemini 연동](#8-gemini-연동)
9. [PoC 범위 및 Mock 전략](#9-poc-범위-및-mock-전략)
10. [파일 구조 및 구현 순서](#10-파일-구조-및-구현-순서)
11. [필수 패키지](#11-필수-패키지)
12. [잠재적 문제 및 대응](#12-잠재적-문제-및-대응)

---

## 1. 아키텍처 결정

### 순차 StateGraph (고정 파이프라인 + 노드 내 LLM)

아키텍처 문서에는 "ReAct 패턴"으로 명시되어 있으나, 실제 추천 플로우는 고정 순서이다. 순수 ReAct(LLM이 매 단계 도구 선택)는 다음 이유로 부적합:

| 항목 | 순수 ReAct | 순차 StateGraph |
|------|-----------|---------------|
| 요청당 LLM 호출 | 10회+ | 2~3회 |
| Gemini 무료 티어(15RPM) | 1~2명 동시 처리 | 5~7명 동시 처리 |
| 실행 순서 | 비결정적 (LLM 의존) | 결정적 (코드 보장) |
| 디버깅 난이도 | 높음 | 낮음 |
| LangGraph API 활용 | create_react_agent | StateGraph + add_edge |

**결정**: `langgraph.graph.StateGraph`로 고정 파이프라인 구성. LLM은 특정 노드 내부에서만 사용:
- `filter_places` — 규칙으로 분류 불가한 장소의 실내/실외 판단
- `generate_response` — 추천 이유 자연어 생성

---

## 2. 그래프 구조

```
parse_request
      │
      ▼
fetch_weather
      │
      ▼
search_places ──(결과 없음)──▶ generate_response ──▶ END
      │
      ▼
filter_places        ← Gemini (Tier 3 실내/외 판단)
      │
      ▼
match_tags
      │
      ▼
vector_search
      │
      ▼
score_and_select
      │
      ▼
optimize_route
      │
      ▼
generate_response    ← Gemini (추천 이유 생성)
      │
      ▼
     END
```

**조건 분기**: `search_places`에서 장소를 못 찾으면 `generate_response`로 직행하여 에러 응답 생성.

---

## 3. AgentState 설계

```python
# agent/state.py
from typing import TypedDict, Optional

class AgentState(TypedDict):
    # 입력
    raw_request: dict

    # Node 1: parse_request
    parsed_request: Optional[dict]       # ParsedRequest.model_dump()

    # Node 2: fetch_weather
    weather: Optional[dict]              # WeatherData.model_dump()

    # Node 3: search_places
    raw_places: Optional[list[dict]]     # list[PlaceInfo]

    # Node 4: filter_places
    filtered_places: Optional[list[dict]]  # list[FilteredPlace]

    # Node 5: match_tags
    tag_scores: Optional[dict[str, float]]  # content_id → 점수

    # Node 6: vector_search
    vector_scores: Optional[dict[str, float]]  # content_id → 유사도

    # Node 7: score_and_select
    selected_places: Optional[list[dict]]  # list[ScoredPlace]

    # Node 8: optimize_route
    route: Optional[dict]                # RouteResult

    # 최종 출력
    response: Optional[dict]

    # 에러 추적
    error: Optional[str]
```

**설계 원칙**:
- 각 노드는 **정확히 하나의 필드**에만 쓴다 (단일 작성자 원칙)
- 모든 중간 필드는 `Optional` — 그래프 시작 시 `raw_request`만 채워짐
- 점수는 `content_id`(TourAPI 장소 ID) 문자열을 키로 사용

---

## 4. Pydantic 스키마

```python
# models/schemas.py
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
    travel_date: str | None = None       # YYYY-MM-DD, 기본값 오늘
    mobility_type: str = "walk"
    selected_tags: list[str] = []        # ["#힐링", "#조용한"]
    free_text: str = ""                  # 자연어 쿼리
    num_places: int = 5

class RecommendResponse(BaseModel):
    places: list["ScoredPlace"]
    route: "RouteResult | None" = None
    weather: "WeatherData | None" = None
    reasoning: str = ""                  # LLM 생성 추천 이유


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
    condition: str                       # "Clear", "Rain", "Snow" 등
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    description: str                     # 한글 설명
    is_bad_weather: bool                 # 비/눈/극한 기온 여부
    icon: str

class PlaceInfo(BaseModel):
    content_id: str                      # TourAPI 장소 ID
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
    indoor_outdoor: str                  # "indoor" 또는 "outdoor" (확정)
    filter_method: str                   # "rule_type", "rule_category", "llm"

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
```

---

## 5. 노드별 구현 상세

### Node 1: `parse_request` — 요청 파싱

```python
def parse_request(state: AgentState) -> dict:
    raw = state["raw_request"]
    parsed = ParsedRequest(
        latitude=raw["latitude"],
        longitude=raw["longitude"],
        travel_date=raw.get("travel_date", date.today().isoformat()),
        mobility_type=raw.get("mobility_type", "walk"),
        selected_tags=raw.get("selected_tags", []),
        free_text=raw.get("free_text", ""),
        num_places=raw.get("num_places", 5),
    )
    return {"parsed_request": parsed.model_dump()}
```

LLM 미사용. 직접 필드 매핑.

---

### Node 2: `fetch_weather` — 날씨 조회

**실제 연동** (OpenWeatherMap Current Weather API)

```python
# tools/weather.py
import httpx

async def get_weather(lat: float, lon: float, api_key: str) -> WeatherData:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat, "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "kr"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    condition = data["weather"][0]["main"]
    bad_conditions = {"Rain", "Snow", "Thunderstorm", "Drizzle"}

    return WeatherData(
        condition=condition,
        temperature=data["main"]["temp"],
        feels_like=data["main"]["feels_like"],
        humidity=data["main"]["humidity"],
        wind_speed=data["wind"]["speed"],
        description=data["weather"][0]["description"],
        is_bad_weather=condition in bad_conditions,
        icon=data["weather"][0]["icon"],
    )
```

**노드**:
```python
async def fetch_weather(state: AgentState) -> dict:
    req = state["parsed_request"]
    weather = await get_weather(req["latitude"], req["longitude"], settings.OPENWEATHER_API_KEY)
    return {"weather": weather.model_dump()}
```

---

### Node 3: `search_places` — 장소 검색

**실제 연동** (TourAPI locationBasedList1)

```python
# tools/place_search.py
import httpx

TOURAPI_BASE = "https://apis.data.go.kr/B551011/KorService1"

async def search_places_tourapi(
    lat: float, lon: float, radius: int, service_key: str
) -> list[PlaceInfo]:
    url = f"{TOURAPI_BASE}/locationBasedList1"
    params = {
        "serviceKey": service_key,
        "MobileOS": "ETC",
        "MobileApp": "MAP",
        "_type": "json",
        "mapX": lon,          # TourAPI: X=경도, Y=위도
        "mapY": lat,
        "radius": radius,
        "numOfRows": 30,
        "pageNo": 1,
        "contentTypeId": "",  # 전체
        "arrange": "E",       # 거리순
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, dict):  # 단일 결과일 때 dict로 옴
        items = [items]

    places = []
    for item in items:
        places.append(PlaceInfo(
            content_id=str(item["contentid"]),
            name=item["title"],
            address=item.get("addr1", ""),
            latitude=float(item["mapy"]),
            longitude=float(item["mapx"]),
            content_type_id=int(item.get("contenttypeid", 0)),
            cat1=item.get("cat1"),
            cat2=item.get("cat2"),
            cat3=item.get("cat3"),
        ))
    return places
```

**주의사항**:
- TourAPI는 `mapX`=경도, `mapY`=위도 (일반적인 lat/lon 순서와 반대)
- 결과가 1건이면 `items`가 dict로 반환됨 (배열 아님) → 방어 코드 필요
- `_type=json` 파라미터 필수 (기본값은 XML)

---

### Node 4: `filter_places` — 실내/실외 필터링

**3단계 규칙 (아키텍처 문서 5.3절)**

```python
# tools/place_filter.py

# Tier 1: contentTypeId 기반
INDOOR_TYPES = {14, 38, 39}    # 문화시설, 쇼핑, 음식점
OUTDOOR_TYPES = {12, 28}       # 관광지, 레포츠

# Tier 2: cat2/cat3 키워드 기반
INDOOR_KEYWORDS = {"박물관", "미술관", "전시관", "극장", "영화관", "백화점", "쇼핑몰"}
OUTDOOR_KEYWORDS = {"해수욕장", "산", "공원", "계곡", "폭포", "섬", "둘레길", "해변"}

def classify_by_rules(place: PlaceInfo) -> str | None:
    """Tier 1+2 규칙 분류. 분류 불가 시 None 반환."""
    # Tier 1
    if place.content_type_id in INDOOR_TYPES:
        return "indoor"
    if place.content_type_id in OUTDOOR_TYPES:
        return "outdoor"

    # Tier 2
    cats = f"{place.cat2 or ''} {place.cat3 or ''}"
    for kw in INDOOR_KEYWORDS:
        if kw in cats:
            return "indoor"
    for kw in OUTDOOR_KEYWORDS:
        if kw in cats:
            return "outdoor"

    return None  # Tier 3 필요


async def classify_with_llm(place_name: str, overview: str, llm) -> str:
    """Tier 3: Gemini로 실내/실외 판단"""
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = f"""다음 장소가 실내(indoor)인지 실외(outdoor)인지 판단하세요.
장소명: {place_name}
설명: {overview or '정보 없음'}

반드시 "indoor" 또는 "outdoor" 중 하나만 답하세요."""

    response = await llm.ainvoke([
        SystemMessage(content="당신은 장소 분류 전문가입니다."),
        HumanMessage(content=prompt),
    ])
    result = response.content.strip().lower()
    return "indoor" if "indoor" in result else "outdoor"


async def filter_places(
    places: list[PlaceInfo], llm=None
) -> list[FilteredPlace]:
    result = []
    for place in places:
        classification = classify_by_rules(place)
        method = "rule_type" if classification and place.content_type_id else "rule_category"

        if classification is None:
            if llm and place.overview:
                classification = await classify_with_llm(place.name, place.overview, llm)
                method = "llm"
            else:
                classification = "outdoor"  # 기본값
                method = "default"

        result.append(FilteredPlace(
            **place.model_dump(),
            indoor_outdoor=classification,
            filter_method=method,
        ))
    return result
```

---

### Node 5: `match_tags` — 태그 매칭

**PoC: Mock** (DB 미연결)

```python
# tools/tag_search.py

async def match_tags_mock(
    place_ids: list[str], user_tags: list[str]
) -> dict[str, float]:
    """PoC Mock: 랜덤 점수 반환. 실제 구현 시 SQL 쿼리로 교체."""
    import random
    if not user_tags:
        return {pid: 0.0 for pid in place_ids}
    return {pid: round(random.uniform(0.2, 0.9), 2) for pid in place_ids}


# === 실제 구현 (DB 연동 시) ===
async def match_tags_real(
    pool, place_ids: list[str], user_tags: list[str]
) -> dict[str, float]:
    if not user_tags:
        return {pid: 0.0 for pid in place_ids}

    query = """
    SELECT p.content_id,
           COUNT(*)::float / $1 AS tag_score
    FROM place_tags pt
    JOIN tags t ON t.id = pt.tag_id
    JOIN places p ON p.id = pt.place_id
    WHERE p.content_id = ANY($2)
      AND t.name = ANY($3)
    GROUP BY p.content_id
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, len(user_tags), place_ids, user_tags)
    scores = {row["content_id"]: row["tag_score"] for row in rows}
    # 매칭 안 된 장소는 0.0
    for pid in place_ids:
        scores.setdefault(pid, 0.0)
    return scores
```

---

### Node 6: `vector_search` — RAG 의미 검색

**PoC: Mock** (DB + 임베딩 미연결)

```python
# tools/vector_search.py

async def vector_search_mock(
    place_ids: list[str], free_text: str
) -> dict[str, float]:
    """PoC Mock: free_text가 있으면 랜덤 유사도, 없으면 0.0"""
    import random
    if not free_text:
        return {pid: 0.0 for pid in place_ids}
    return {pid: round(random.uniform(0.3, 0.95), 2) for pid in place_ids}


# === 실제 구현 (DB 연동 시) ===
async def vector_search_real(
    pool, place_ids: list[str], query_embedding: list[float]
) -> dict[str, float]:
    query = """
    SELECT p.content_id,
           1 - (pe.embedding <=> $1::vector) AS similarity
    FROM place_embeddings pe
    JOIN places p ON p.id = pe.place_id
    WHERE p.content_id = ANY($2)
    ORDER BY pe.embedding <=> $1::vector
    LIMIT 20
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, str(query_embedding), place_ids)
    return {row["content_id"]: row["similarity"] for row in rows}
```

---

### Node 7: `score_and_select` — 점수 산출 및 선정

```python
def score_and_select(state: AgentState) -> dict:
    filtered = state["filtered_places"]
    tag_scores = state.get("tag_scores") or {}
    vector_scores = state.get("vector_scores") or {}
    weather = state["weather"]
    num_places = state["parsed_request"]["num_places"]

    scored = []
    for place in filtered:
        cid = place["content_id"]
        tag_s = tag_scores.get(cid, 0.0)
        vec_s = vector_scores.get(cid, 0.0)

        # 날씨 적합도: 악천후+실내 또는 좋은날씨+실외 = 1.0, 그 외 = 0.5
        is_bad = weather["is_bad_weather"]
        is_indoor = place["indoor_outdoor"] == "indoor"
        weather_s = 1.0 if (is_bad and is_indoor) or (not is_bad and not is_indoor) else 0.5

        total = (tag_s * 0.4) + (vec_s * 0.4) + (weather_s * 0.2)

        scored.append({
            "content_id": cid,
            "name": place["name"],
            "address": place["address"],
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "indoor_outdoor": place["indoor_outdoor"],
            "tag_score": tag_s,
            "vector_score": vec_s,
            "weather_score": weather_s,
            "total_score": round(total, 3),
            "overview": place.get("overview"),
        })

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return {"selected_places": scored[:num_places]}
```

**점수 공식** (아키텍처 문서 6.2절):
```
최종 점수 = (태그 매칭 점수 × 0.4) + (벡터 유사도 × 0.4) + (날씨 적합도 × 0.2)
```

---

### Node 8: `optimize_route` — 경로 최적화

**PoC: Mock** (네이버 API 미연결)

```python
# tools/route_optimize.py
import math

def haversine(lat1, lon1, lat2, lon2) -> float:
    """두 좌표 간 직선 거리(m)"""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def optimize_route_mock(
    places: list[dict], start_lat: float, start_lon: float
) -> dict:
    """PoC Mock: 최근접 이웃 휴리스틱으로 방문 순서 결정"""
    if not places:
        return {"ordered_places": [], "legs": [],
                "total_distance_m": 0, "total_duration_min": 0}

    remaining = list(places)
    ordered = []
    current_lat, current_lon = start_lat, start_lon
    legs = []
    total_dist = 0

    while remaining:
        nearest_idx = min(range(len(remaining)),
            key=lambda i: haversine(current_lat, current_lon,
                                     remaining[i]["latitude"], remaining[i]["longitude"]))
        nearest = remaining.pop(nearest_idx)
        dist = haversine(current_lat, current_lon, nearest["latitude"], nearest["longitude"])

        if ordered:
            legs.append({
                "from_place": ordered[-1]["name"],
                "to_place": nearest["name"],
                "distance_m": int(dist),
                "duration_min": int(dist / 80),  # 도보 기준 약 80m/min
            })

        ordered.append(nearest)
        total_dist += dist
        current_lat, current_lon = nearest["latitude"], nearest["longitude"]

    return {
        "ordered_places": ordered,
        "legs": legs,
        "total_distance_m": int(total_dist),
        "total_duration_min": int(total_dist / 80),
    }
```

---

### Node 9: `generate_response` — 응답 생성

```python
async def generate_response(state: AgentState) -> dict:
    # 에러 케이스
    if state.get("error") or not state.get("selected_places"):
        return {"response": {
            "places": [],
            "route": None,
            "weather": state.get("weather"),
            "reasoning": "주변에 추천할 장소를 찾지 못했습니다.",
        }}

    # LLM으로 추천 이유 생성
    reasoning = ""
    if llm:
        weather_desc = state["weather"]["description"]
        place_names = [p["name"] for p in state["selected_places"][:3]]
        prompt = f"""날씨: {weather_desc}
추천 장소: {', '.join(place_names)}
위 장소를 추천한 이유를 2~3문장으로 한국어로 설명하세요."""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        reasoning = response.content.strip()

    return {"response": {
        "places": state["selected_places"],
        "route": state.get("route"),
        "weather": state["weather"],
        "reasoning": reasoning,
    }}
```

---

## 6. 그래프 조립

```python
# agent/graph.py
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    parse_request, fetch_weather, search_places,
    filter_places, match_tags, vector_search,
    score_and_select, optimize_route, generate_response,
)


def has_places(state: AgentState) -> str:
    if state.get("raw_places"):
        return "continue"
    return "no_results"


def build_graph():
    graph = StateGraph(AgentState)

    # 노드 등록
    graph.add_node("parse_request", parse_request)
    graph.add_node("fetch_weather", fetch_weather)
    graph.add_node("search_places", search_places)
    graph.add_node("filter_places", filter_places)
    graph.add_node("match_tags", match_tags)
    graph.add_node("vector_search", vector_search)
    graph.add_node("score_and_select", score_and_select)
    graph.add_node("optimize_route", optimize_route)
    graph.add_node("generate_response", generate_response)

    # 엣지 연결
    graph.set_entry_point("parse_request")
    graph.add_edge("parse_request", "fetch_weather")
    graph.add_edge("fetch_weather", "search_places")

    # 조건 분기: 장소 못 찾으면 에러 응답으로 직행
    graph.add_conditional_edges(
        "search_places",
        has_places,
        {"continue": "filter_places", "no_results": "generate_response"},
    )

    graph.add_edge("filter_places", "match_tags")
    graph.add_edge("match_tags", "vector_search")
    graph.add_edge("vector_search", "score_and_select")
    graph.add_edge("score_and_select", "optimize_route")
    graph.add_edge("optimize_route", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
```

---

## 7. FastAPI 엔드포인트

```python
# main.py
from fastapi import FastAPI
from models.schemas import RecommendRequest, RecommendResponse
from agent.graph import build_graph

app = FastAPI(title="MAP AI Agent", version="0.1.0")


@app.on_event("startup")
async def startup():
    app.state.agent = build_graph()


@app.post("/api/v1/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    initial_state = {"raw_request": request.model_dump()}
    result = await app.state.agent.ainvoke(initial_state)
    return result["response"]


@app.get("/health")
async def health():
    return {"status": "ok"}
```

Spring Boot는 `POST http://fastapi:8000/api/v1/recommend`를 WebClient로 호출한다.

---

## 8. Gemini 연동

### LLM 초기화

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    OPENWEATHER_API_KEY: str
    TOURAPI_SERVICE_KEY: str
    DATABASE_URL: str = ""
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    GOOGLE_PLACES_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()


# Gemini LLM 인스턴스
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )
```

### 임베딩 (실제 구현 시)

```python
# rag/embeddings.py
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

async def embed_text(text: str) -> list[float]:
    """text-embedding-004로 768차원 벡터 생성"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="RETRIEVAL_QUERY",
    )
    return result["embedding"]  # 768-dim
```

### Gemini 무료 티어 제한 사항

| 항목 | 제한 |
|------|------|
| RPM (분당 요청) | 15 |
| RPD (일당 요청) | 1,500 |
| TPM (분당 토큰) | 1,000,000 |

요청당 LLM 2~3회 호출 → 분당 최대 5~7건 처리 가능. PoC 시연에는 충분.

---

## 9. PoC 범위 및 Mock 전략

### 실제 연동 (3개)

| 컴포넌트 | API | 필요한 키 |
|---------|-----|----------|
| 날씨 조회 | OpenWeatherMap Current Weather | `OPENWEATHER_API_KEY` |
| 장소 검색 | TourAPI locationBasedList1 | `TOURAPI_SERVICE_KEY` |
| LLM | Gemini 2.0 Flash | `GEMINI_API_KEY` |

### Mock (3개)

| 컴포넌트 | Mock 방식 |
|---------|----------|
| 태그 매칭 | 랜덤 점수 (0.2~0.9) 반환 |
| 벡터 검색 | free_text 존재 시 랜덤 유사도, 없으면 0.0 |
| 경로 최적화 | 최근접 이웃 휴리스틱 + haversine 직선 거리 |

### Mock → 실제 전환 체크리스트

```
□ 태그 매칭 → DB 연동 시:
  - asyncpg 연결 풀 설정 (db/connection.py)
  - place_tags, tags 테이블에 시드 데이터 적재
  - match_tags_mock → match_tags_real 교체

□ 벡터 검색 → DB 연동 시:
  - rag/embeddings.py로 text-embedding-004 호출
  - place_embeddings 테이블에 벡터 데이터 적재 (rag/loader.py)
  - vector_search_mock → vector_search_real 교체

□ 경로 최적화 → 네이버 API 연동 시:
  - 네이버 길찾기 API (Directions 5) 연동
  - optimize_route_mock → optimize_route_real 교체
  - 도보/자가용: 동일 API (옵션 차이)
  - 대중교통: 별도 API 엔드포인트
```

---

## 10. 파일 구조 및 구현 순서

### 디렉토리 구조

```
map-service-agent/
├── main.py                          # FastAPI 앱, /recommend, /health
├── config.py                        # 환경변수 로딩 (pydantic-settings)
├── requirements.txt                 # Python 의존성
├── agent/
│   ├── __init__.py
│   ├── state.py                     # AgentState TypedDict
│   ├── graph.py                     # StateGraph 빌드 + 컴파일
│   ├── nodes.py                     # 9개 노드 함수
│   └── prompts.py                   # Gemini 프롬프트 템플릿
├── tools/
│   ├── __init__.py
│   ├── weather.py                   # OpenWeatherMap 클라이언트
│   ├── place_search.py              # TourAPI 클라이언트
│   ├── place_filter.py              # 3단계 실내/실외 분류
│   ├── tag_search.py                # SQL 태그 매칭 (+ Mock)
│   ├── vector_search.py             # pgvector 검색 (+ Mock)
│   └── route_optimize.py            # 경로 최적화 (+ Mock)
├── rag/
│   ├── __init__.py
│   ├── embeddings.py                # text-embedding-004 래퍼
│   ├── loader.py                    # 배치 데이터 적재 (초기 1회 실행)
│   └── retriever.py                 # pgvector 쿼리 빌더
├── models/
│   ├── __init__.py
│   └── schemas.py                   # Pydantic 스키마 전체
├── db/
│   ├── __init__.py
│   └── connection.py                # asyncpg 연결 풀 (향후)
├── tests/
│   ├── __init__.py
│   └── test_graph.py                # E2E 그래프 테스트
├── docker/
│   └── Dockerfile                   # [기존]
├── .env.example                     # [기존]
├── .dockerignore                    # [기존]
├── .gitignore                       # [기존]
├── LICENSE                          # [기존]
└── README.md                        # [기존, 갱신 필요]
```

### 구현 순서

| Step | 작업 | 파일 |
|------|------|------|
| 1 | 프로젝트 스캐폴딩 (디렉토리 + `__init__.py`) | 전체 |
| 2 | 환경변수 설정 | `config.py`, `requirements.txt` |
| 3 | Pydantic 스키마 정의 | `models/schemas.py` |
| 4 | AgentState 정의 | `agent/state.py` |
| 5 | 모든 노드를 stub으로 작성 | `agent/nodes.py` |
| 6 | 그래프 조립 + 컴파일 확인 | `agent/graph.py` |
| 7 | FastAPI 엔드포인트 | `main.py` |
| 8 | **검증**: `uvicorn main:app --reload` → curl 테스트 (stub 응답 확인) |
| 9 | 날씨 도구 실제 구현 | `tools/weather.py`, `agent/nodes.py` |
| 10 | 장소 검색 실제 구현 | `tools/place_search.py`, `agent/nodes.py` |
| 11 | 실내/실외 필터 (Tier 1+2 규칙) | `tools/place_filter.py`, `agent/nodes.py` |
| 12 | 점수 산출 + 선정 | `agent/nodes.py` |
| 13 | 경로 최적화 (Mock) | `tools/route_optimize.py`, `agent/nodes.py` |
| 14 | 태그 매칭 (Mock) | `tools/tag_search.py`, `agent/nodes.py` |
| 15 | 벡터 검색 (Mock) | `tools/vector_search.py`, `agent/nodes.py` |
| 16 | LLM 연동: 실내/실외 Tier 3 | `tools/place_filter.py`, `agent/prompts.py` |
| 17 | LLM 연동: 추천 이유 생성 | `agent/nodes.py`, `agent/prompts.py` |
| 18 | **최종 검증**: 전체 파이프라인 E2E 테스트 |

---

## 11. 필수 패키지

```
# requirements.txt

# === Web Framework ===
fastapi==0.115.0
uvicorn[standard]==0.30.0

# === LangGraph ===
langgraph==0.4.1
langchain-core==0.3.0

# === LLM - Gemini ===
langchain-google-genai==2.1.0
google-generativeai==0.8.0

# === HTTP Client ===
httpx==0.28.0

# === Data Validation ===
pydantic==2.10.0
pydantic-settings==2.7.0

# === Environment ===
python-dotenv==1.0.1

# === Database (향후 DB 연동 시) ===
# asyncpg==0.30.0
# pgvector==0.3.6

# === Testing ===
pytest==8.3.0
pytest-asyncio==0.24.0
```

PoC 단계에서는 DB 패키지 주석 처리. DB 연동 시 주석 해제.

---

## 12. 잠재적 문제 및 대응

| 문제 | 영향 | 대응 |
|------|------|------|
| **TourAPI 응답 불일치** | 단일 결과 시 dict, 복수 시 list 반환 | `isinstance(items, dict)` 체크로 방어 |
| **TourAPI 좌표 순서** | mapX=경도, mapY=위도 (일반적 순서와 반대) | 코드 내 명시적 주석 + 변수명으로 혼동 방지 |
| **Gemini 15RPM 제한** | 동시 사용자 많으면 429 에러 | 요청당 LLM 2~3회로 제한, 캐시 적용 (향후) |
| **LLM 응답 파싱 실패** | 실내/실외 판단에서 예상 외 응답 | `"indoor" in result` 패턴 매칭, 실패 시 기본값 "outdoor" |
| **TourAPI 서비스 키 인코딩** | URL 인코딩된 키를 다시 인코딩하면 실패 | httpx가 자동 인코딩하므로 원본 키 사용 |
| **asyncio 호환성** | `google-generativeai` SDK가 동기식 | `asyncio.to_thread()`로 래핑 |
| **TourAPI overview 미포함** | locationBasedList1은 overview 미반환 | 필요 시 `detailCommon1`을 별도 호출하여 overview 조회 |

### TourAPI overview 조회 보충

`locationBasedList1`은 장소 기본 정보만 반환하고 `overview`(장소 설명)를 포함하지 않는다. Tier 3 LLM 판단과 RAG에 overview가 필요하므로, 별도로 `detailCommon1` API를 호출해야 한다:

```python
async def get_place_detail(content_id: str, service_key: str) -> str | None:
    url = f"{TOURAPI_BASE}/detailCommon1"
    params = {
        "serviceKey": service_key,
        "MobileOS": "ETC",
        "MobileApp": "MAP",
        "_type": "json",
        "contentId": content_id,
        "overviewYN": "Y",
        "defaultYN": "Y",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    item = data["response"]["body"]["items"]["item"]
    if isinstance(item, list):
        item = item[0]
    return item.get("overview")
```

**PoC 전략**: 검색된 장소 중 `indoor_outdoor="unknown"`인 것들만 `detailCommon1`을 호출하여 API 호출 수 절약.
