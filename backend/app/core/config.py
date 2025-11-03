from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file = ".env", env_file_encoding = "utf-8")

    GEMINI_API_KEY: str = ""
    S2_API_KEY: str = ""
    S2_SEARCH_API_URL: str = "https://api.semanticscholar.org/graph/v1/paper/search"

settings = Settings()