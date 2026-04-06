import pytest

from agent.graph import graph


SAMPLE_REQUEST = {
    "raw_request": {
        "latitude": 37.5665,
        "longitude": 126.978,
        "travel_date": "2026-04-06",
        "mobility_type": "walk",
        "selected_tags": ["#힐링", "#조용한"],
        "free_text": "공원 근처 조용한 곳",
        "num_places": 5,
    }
}

MINIMAL_REQUEST = {
    "raw_request": {
        "latitude": 37.5665,
        "longitude": 126.978,
    }
}


@pytest.mark.asyncio
async def test_full_pipeline_returns_places():
    """정상 케이스: 5개 장소 + 경로 + 날씨 반환."""
    result = await graph.ainvoke(SAMPLE_REQUEST)
    resp = result["response"]

    assert len(resp["places"]) == 5
    assert resp["route"] is not None
    assert len(resp["route"]["legs"]) == 4
    assert resp["route"]["total_distance_m"] > 0
    assert resp["weather"] is not None
    assert resp["weather"]["condition"] == "Clear"


@pytest.mark.asyncio
async def test_places_have_required_fields():
    """각 장소에 필수 필드가 포함되어 있는지 확인."""
    result = await graph.ainvoke(SAMPLE_REQUEST)
    for place in result["response"]["places"]:
        assert "content_id" in place
        assert "name" in place
        assert "latitude" in place
        assert "longitude" in place
        assert "indoor_outdoor" in place
        assert "total_score" in place
        assert place["indoor_outdoor"] in ("indoor", "outdoor")


@pytest.mark.asyncio
async def test_places_sorted_by_score():
    """장소가 점수 내림차순으로 정렬되어 있는지 확인."""
    result = await graph.ainvoke(SAMPLE_REQUEST)
    places = result["response"]["places"]
    scores = [p["total_score"] for p in places]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_minimal_request_defaults():
    """최소 입력(lat, lon만)으로도 정상 동작."""
    result = await graph.ainvoke(MINIMAL_REQUEST)
    resp = result["response"]

    assert len(resp["places"]) == 5
    assert resp["weather"] is not None


@pytest.mark.asyncio
async def test_scoring_formula():
    """점수 공식: tag*0.4 + vector*0.4 + weather*0.2 검증."""
    result = await graph.ainvoke(SAMPLE_REQUEST)
    for place in result["response"]["places"]:
        expected = round(
            place["tag_score"] * 0.4
            + place["vector_score"] * 0.4
            + place["weather_score"] * 0.2,
            3,
        )
        assert place["total_score"] == expected


@pytest.mark.asyncio
async def test_no_results_branch():
    """검색 결과 없을 때 에러 응답 생성 확인."""
    from unittest.mock import patch

    with patch(
        "agent.nodes.search_places_mock", return_value=[]
    ):
        result = await graph.ainvoke(SAMPLE_REQUEST)

    resp = result["response"]
    assert resp["places"] == []
    assert "찾지 못했습니다" in resp["reasoning"]
