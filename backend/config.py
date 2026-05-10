from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TMDB_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE: str = "https://image.tmdb.org/t/p"

    class Config:
        env_file = ".env"

settings = Settings()
