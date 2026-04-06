from models.schemas import PlaceInfo, FilteredPlace

# Tier 1: contentTypeId 기반
INDOOR_TYPES = {14, 38, 39}    # 문화시설, 쇼핑, 음식점
OUTDOOR_TYPES = {12, 28}       # 관광지, 레포츠

# Tier 2: cat2/cat3 키워드 기반
INDOOR_KEYWORDS = {"박물관", "미술관", "전시관", "극장", "영화��", "백화점", "쇼핑몰"}
OUTDOOR_KEYWORDS = {"해수욕장", "산", "공원", "계곡", "폭��", "섬", "둘레길", "해변"}


def classify_by_rules(place: PlaceInfo) -> tuple[str | None, str]:
    """Tier 1+2 규칙 분류. (분류결과, 방법) 반환. 분류 불가 시 (None, '')."""
    # Tier 1
    if place.content_type_id in INDOOR_TYPES:
        return "indoor", "rule_type"
    if place.content_type_id in OUTDOOR_TYPES:
        return "outdoor", "rule_type"

    # Tier 2
    cats = f"{place.cat2 or ''} {place.cat3 or ''}"
    for kw in INDOOR_KEYWORDS:
        if kw in cats:
            return "indoor", "rule_category"
    for kw in OUTDOOR_KEYWORDS:
        if kw in cats:
            return "outdoor", "rule_category"

    return None, ""


def filter_places_by_rules(places: list[PlaceInfo]) -> list[FilteredPlace]:
    """Tier 1+2 규칙만으로 분류. Tier 3(LLM)은 Phase 4에서 추가."""
    result = []
    for place in places:
        classification, method = classify_by_rules(place)
        if classification is None:
            classification = "outdoor"
            method = "default"

        result.append(FilteredPlace(
            **place.model_dump(),
            indoor_outdoor=classification,
            filter_method=method,
        ))
    return result
