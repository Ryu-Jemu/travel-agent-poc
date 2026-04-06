from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEMINI_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    TOURAPI_SERVICE_KEY: str = ""


settings = Settings()


def get_llm():
    """Gemini LLM 인스턴스를 lazy 생성. 키 미설정 시 None 반환."""
    if not settings.GEMINI_API_KEY:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )
