from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "trouvels360_demo"
    DB_USER: str = "laravel"
    DB_PASSWORD: str = "secret"
    
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8001
    SERVER_RELOAD: bool = True
    
    # CORS
    FRONTEND_URL: str = "http://localhost:4200"
    
    # App
    APP_NAME: str = "Itinerarios Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "http://localhost:8000"
    JWT_AUDIENCE: str = "fastapi-itinerarios"

    # Business Rules
    HORAS_DISPONIBLES_POR_DIA: int = 8
    
    class Config:
        env_file = ".env.fastapi"
        extra = "ignore"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()
