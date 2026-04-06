import math


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 직선 거리(m)."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def optimize_route_mock(
    places: list[dict], start_lat: float, start_lon: float
) -> dict:
    """Mock: 최근접 이웃 휴리스틱으로 방문 순서 결정."""
    if not places:
        return {
            "ordered_places": [], "legs": [],
            "total_distance_m": 0, "total_duration_min": 0,
        }

    remaining = list(places)
    ordered = []
    current_lat, current_lon = start_lat, start_lon
    legs = []
    total_dist = 0.0

    while remaining:
        nearest_idx = min(
            range(len(remaining)),
            key=lambda i: haversine(
                current_lat, current_lon,
                remaining[i]["latitude"], remaining[i]["longitude"],
            ),
        )
        nearest = remaining.pop(nearest_idx)
        dist = haversine(current_lat, current_lon, nearest["latitude"], nearest["longitude"])

        if ordered:
            legs.append({
                "from_place": ordered[-1]["name"],
                "to_place": nearest["name"],
                "distance_m": int(dist),
                "duration_min": max(1, int(dist / 80)),  # 도보 약 80m/min
            })

        ordered.append(nearest)
        total_dist += dist
        current_lat, current_lon = nearest["latitude"], nearest["longitude"]

    return {
        "ordered_places": ordered,
        "legs": legs,
        "total_distance_m": int(total_dist),
        "total_duration_min": max(1, int(total_dist / 80)),
    }
