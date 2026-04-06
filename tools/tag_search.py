import random


def match_tags_mock(place_ids: list[str], user_tags: list[str]) -> dict[str, float]:
    """Mock: 태그 있으면 랜덤 점수(0.2~0.9), 없으면 0.0."""
    if not user_tags:
        return {pid: 0.0 for pid in place_ids}
    return {pid: round(random.uniform(0.2, 0.9), 2) for pid in place_ids}
