from typing import TypedDict, Optional


class AgentState(TypedDict):
    # 입력
    raw_request: dict

    # Node 1: parse_request
    parsed_request: Optional[dict]

    # Node 2: fetch_weather
    weather: Optional[dict]

    # Node 3: search_places
    raw_places: Optional[list[dict]]

    # Node 4: filter_places
    filtered_places: Optional[list[dict]]

    # Node 5: match_tags
    tag_scores: Optional[dict[str, float]]

    # Node 6: vector_search
    vector_scores: Optional[dict[str, float]]

    # Node 7: score_and_select
    selected_places: Optional[list[dict]]

    # Node 8: optimize_route
    route: Optional[dict]

    # 최종 출력
    response: Optional[dict]

    # 에러 추적
    error: Optional[str]
