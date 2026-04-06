import random


def vector_search_mock(place_ids: list[str], free_text: str) -> dict[str, float]:
    """Mock: free_text 있으면 랜덤 유사도(0.3~0.95), 없으면 0.0."""
    if not free_text:
        return {pid: 0.0 for pid in place_ids}
    return {pid: round(random.uniform(0.3, 0.95), 2) for pid in place_ids}
