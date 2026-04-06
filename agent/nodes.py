from agent.state import AgentState


def parse_request(state: AgentState) -> dict:
    return {"parsed_request": state["raw_request"]}


def fetch_weather(state: AgentState) -> dict:
    return {"weather": {}}


def search_places(state: AgentState) -> dict:
    return {"raw_places": []}


def filter_places(state: AgentState) -> dict:
    return {"filtered_places": []}


def match_tags(state: AgentState) -> dict:
    return {"tag_scores": {}}


def vector_search(state: AgentState) -> dict:
    return {"vector_scores": {}}


def score_and_select(state: AgentState) -> dict:
    return {"selected_places": []}


def optimize_route(state: AgentState) -> dict:
    return {"route": {}}


def generate_response(state: AgentState) -> dict:
    return {"response": {
        "places": [],
        "route": None,
        "weather": state.get("weather"),
        "reasoning": "stub response",
    }}
