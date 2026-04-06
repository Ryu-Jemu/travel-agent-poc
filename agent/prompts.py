import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

CLASSIFY_SYSTEM = "당신은 장소 분류 전문가입니다."

CLASSIFY_TEMPLATE = """다음 장소가 실내(indoor)인지 실외(outdoor)인지 판단하세요.
장소명: {place_name}
설명: {overview}

반드시 "indoor" 또는 "outdoor" 중 하나만 답하세요."""

REASONING_TEMPLATE = """날씨: {weather_desc}
추천 장소: {place_names}
위 장소를 추천한 이유를 2~3문장으로 한국어로 설명하세요."""


def _invoke_sync(llm, messages):
    """동기 호출 (ainvoke 비동기 버그 우회용)."""
    return llm.invoke(messages)


async def classify_indoor_outdoor(
    llm, place_name: str, overview: str
) -> str:
    """Gemini로 실내/실외 판단. 실패 시 'outdoor' 반환."""
    prompt = CLASSIFY_TEMPLATE.format(
        place_name=place_name,
        overview=overview or "정보 없음",
    )
    messages = [
        SystemMessage(content=CLASSIFY_SYSTEM),
        HumanMessage(content=prompt),
    ]
    try:
        response = await asyncio.to_thread(_invoke_sync, llm, messages)
        result = response.content.strip().lower()
        return "indoor" if "indoor" in result else "outdoor"
    except Exception:
        return "outdoor"


async def generate_reasoning(
    llm, weather_desc: str, place_names: list[str]
) -> str:
    """Gemini로 추천 이유 생성. 실패 시 빈 문자열 반환."""
    prompt = REASONING_TEMPLATE.format(
        weather_desc=weather_desc,
        place_names=", ".join(place_names),
    )
    messages = [HumanMessage(content=prompt)]
    try:
        response = await asyncio.to_thread(_invoke_sync, llm, messages)
        return response.content.strip()
    except Exception:
        return ""
