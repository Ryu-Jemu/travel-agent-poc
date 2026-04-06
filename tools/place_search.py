from models.schemas import PlaceInfo

MOCK_PLACES = [
    PlaceInfo(
        content_id="126508", name="경복궁", address="서울특별시 종로구 사직로 161",
        latitude=37.5796, longitude=126.9770, content_type_id=12,
        cat1="A02", cat2="A0201", cat3="A02010100",
        overview="조선 왕조의 법궁으로 서울의 대표적인 궁궐입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="264337", name="국립중앙박물관", address="서울특별시 용산구 서빙고로 137",
        latitude=37.5239, longitude=126.9806, content_type_id=14,
        cat1="A02", cat2="A0206", cat3="A02060100",
        overview="한국의 역사와 문화유산을 전시하는 대한민국 최대 규모 박물관입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="774843", name="북촌한옥마을", address="서울특별시 종로구 계동길 37",
        latitude=37.5829, longitude=126.9836, content_type_id=12,
        cat1="A02", cat2="A0201", cat3="A02010800",
        overview="600년 역사의 전통 한옥이 밀집한 마을입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="264312", name="인사동거리", address="서울특별시 종로구 인사동길",
        latitude=37.5741, longitude=126.9858, content_type_id=38,
        cat1="A04", cat2="A0401", cat3="A04010200",
        overview="전통 공예품과 갤러리가 모여 있는 문화 거리입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="126535", name="남산서울타워", address="서울특별시 용산구 남산공원길 105",
        latitude=37.5512, longitude=126.9882, content_type_id=12,
        cat1="A02", cat2="A0201", cat3="A02010700",
        overview="서울의 상징적인 전망 타워로 도시 전경을 감상할 수 있습니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="264570", name="덕수궁", address="서울특별시 중구 세종대로 99",
        latitude=37.5659, longitude=126.9751, content_type_id=12,
        cat1="A02", cat2="A0201", cat3="A02010100",
        overview="근대 역사의 현장이자 아름다운 돌담길로 유명한 궁궐입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="132914", name="서울숲", address="서울특별시 성동구 뚝섬로 273",
        latitude=37.5444, longitude=127.0374, content_type_id=12,
        cat1="A02", cat2="A0202", cat3="A02020600",
        cat2_name="공원", overview="도심 속 자연 휴식 공간으로 넓은 산책로가 있습니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="789012", name="동대문디자인플라자", address="서울특별시 중구 을지로 281",
        latitude=37.5673, longitude=127.0095, content_type_id=14,
        cat1="A02", cat2="A0206", cat3="A02060300",
        overview="자하 하디드가 설계한 문화 복합 공간입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="345678", name="이태원앤틱가구거리", address="서울특별시 용산구 이태원로 200",
        latitude=37.5340, longitude=126.9948, content_type_id=38,
        cat1="A04", cat2="A0401", cat3="A04010300",
        overview="다양한 앤틱 가구와 소품을 판매하는 쇼핑 거리입니다.",
        indoor_outdoor="unknown",
    ),
    PlaceInfo(
        content_id="567890", name="청계천", address="서울특별시 종로구 청계천로",
        latitude=37.5696, longitude=126.9784, content_type_id=12,
        cat1="A02", cat2="A0202", cat3="A02020400",
        overview="도심을 관통하는 생태 하천으로 산책과 휴식에 좋습니다.",
        indoor_outdoor="unknown",
    ),
]


def search_places_mock(lat: float, lon: float, radius: int = 5000) -> list[PlaceInfo]:
    """Mock: 서울 주요 장소 10곳 반환."""
    return MOCK_PLACES
