from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "trouvels360_demo"
    DB_USER: str = "laravel"
    DB_PASSWORD: str = "secret"
    
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = int(os.getenv("PORT", "8001"))  # Railway usa PORT dinámico
    SERVER_RELOAD: bool = False
    
    # CORS - Permitir múltiples orígenes separados por coma
    FRONTEND_URL: str = "http://localhost:4200"
    ALLOWED_ORIGINS: str = "http://localhost:4200,http://localhost:8000"
    
    # App
    APP_NAME: str = "Itinerarios Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "http://localhost:8000"
    JWT_AUDIENCE: str = "fastapi-itinerarios"

    # Business Rules
    HORAS_DISPONIBLES_POR_DIA: int = 8
    
    class Config:
        env_file = ".env.fastapi"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()
