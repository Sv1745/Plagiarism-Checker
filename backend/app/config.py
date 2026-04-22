from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    gemini_api_key: str = Field(default='')
    gemini_model: str = Field(default='models/gemini-1.5-flash')
    max_candidate_papers: int = Field(default=5)
    similarity_threshold: float = Field(default=0.72)
    frontend_origin: str = Field(default='http://localhost:5173')
    auto_cleanup: bool = Field(default=True)


settings = Settings()
