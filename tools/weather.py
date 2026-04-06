from models.schemas import WeatherData


def get_weather_mock(lat: float, lon: float) -> WeatherData:
    """Mock: 맑은 날씨 22도 고정 반환."""
    return WeatherData(
        condition="Clear",
        temperature=22.0,
        feels_like=21.5,
        humidity=45,
        wind_speed=2.3,
        description="맑음",
        is_bad_weather=False,
        icon="01d",
    )
