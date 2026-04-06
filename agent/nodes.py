from datetime import date

from agent.state import AgentState
from models.schemas import ParsedRequest, PlaceInfo
from tools.weather import get_weather_mock
from tools.place_search import search_places_mock
from tools.place_filter import (
    filter_places_by_rules,
    filter_places_with_llm,
)
from tools.tag_search import match_tags_mock
from tools.vector_search import vector_search_mock
from tools.route_optimize import optimize_route_mock


def parse_request(state: AgentState) -> dict:
    raw = state["raw_request"]
    parsed = ParsedRequest(
        latitude=raw["latitude"],
        longitude=raw["longitude"],
        travel_date=raw.get("travel_date") or date.today().isoformat(),
        mobility_type=raw.get("mobility_type", "walk"),
        selected_tags=raw.get("selected_tags", []),
        free_text=raw.get("free_text", ""),
        num_places=raw.get("num_places", 5),
    )
    return {"parsed_request": parsed.model_dump()}


def fetch_weather(state: AgentState) -> dict:
    req = state["parsed_request"]
    weather = get_weather_mock(req["latitude"], req["longitude"])
    return {"weather": weather.model_dump()}


def search_places(state: AgentState) -> dict:
    req = state["parsed_request"]
    places = search_places_mock(
        req["latitude"], req["longitude"], req["radius_m"],
    )
    return {"raw_places": [p.model_dump() for p in places]}


async def filter_places(state: AgentState) -> dict:
    places = [PlaceInfo(**p) for p in state["raw_places"]]

    from config import get_llm
    llm = get_llm()

    if llm:
        filtered = await filter_places_with_llm(places, llm)
    else:
        filtered = filter_places_by_rules(places)

    return {"filtered_places": [f.model_dump() for f in filtered]}


def match_tags(state: AgentState) -> dict:
    place_ids = [p["content_id"] for p in state["filtered_places"]]
    user_tags = state["parsed_request"].get("selected_tags", [])
    scores = match_tags_mock(place_ids, user_tags)
    return {"tag_scores": scores}


def vector_search(state: AgentState) -> dict:
    place_ids = [p["content_id"] for p in state["filtered_places"]]
    free_text = state["parsed_request"].get("free_text", "")
    scores = vector_search_mock(place_ids, free_text)
    return {"vector_scores": scores}


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

        is_bad = weather["is_bad_weather"]
        is_indoor = place["indoor_outdoor"] == "indoor"
        weather_s = (
            1.0
            if (is_bad and is_indoor) or (not is_bad and not is_indoor)
            else 0.5
        )

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


def optimize_route(state: AgentState) -> dict:
    places = state["selected_places"]
    req = state["parsed_request"]
    route = optimize_route_mock(
        places, req["latitude"], req["longitude"],
    )
    return {"route": route}


async def generate_response(state: AgentState) -> dict:
    if state.get("error") or not state.get("selected_places"):
        return {"response": {
            "places": [],
            "route": None,
            "weather": state.get("weather"),
            "reasoning": "주변에 추천할 장소를 찾지 못했습니다.",
        }}

    reasoning = ""
    from config import get_llm
    llm = get_llm()
    if llm:
        from agent.prompts import generate_reasoning
        weather_desc = state["weather"]["description"]
        place_names = [
            p["name"] for p in state["selected_places"][:3]
        ]
        reasoning = await generate_reasoning(
            llm, weather_desc, place_names,
        )

    return {"response": {
        "places": state["selected_places"],
        "route": state.get("route"),
        "weather": state["weather"],
        "reasoning": reasoning,
    }}
