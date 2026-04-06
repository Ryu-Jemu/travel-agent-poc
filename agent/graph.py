from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes import (
    parse_request,
    fetch_weather,
    search_places,
    filter_places,
    match_tags,
    vector_search,
    score_and_select,
    optimize_route,
    generate_response,
)


def has_places(state: AgentState) -> str:
    if state.get("raw_places"):
        return "continue"
    return "no_results"


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("parse_request", parse_request)
    builder.add_node("fetch_weather", fetch_weather)
    builder.add_node("search_places", search_places)
    builder.add_node("filter_places", filter_places)
    builder.add_node("match_tags", match_tags)
    builder.add_node("vector_search", vector_search)
    builder.add_node("score_and_select", score_and_select)
    builder.add_node("optimize_route", optimize_route)
    builder.add_node("generate_response", generate_response)

    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "fetch_weather")
    builder.add_edge("fetch_weather", "search_places")

    builder.add_conditional_edges(
        "search_places",
        has_places,
        {"continue": "filter_places", "no_results": "generate_response"},
    )

    builder.add_edge("filter_places", "match_tags")
    builder.add_edge("match_tags", "vector_search")
    builder.add_edge("vector_search", "score_and_select")
    builder.add_edge("score_and_select", "optimize_route")
    builder.add_edge("optimize_route", "generate_response")
    builder.add_edge("generate_response", END)

    return builder.compile()


graph = build_graph()
