import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "WealthFam"
    API_V1_STR: str = "/api/v1"
    
    # Database
    APP_DATABASE_URL: str = "duckdb:///data/family_finance_v3.duckdb"
    @property
    def DATABASE_URL(self):
        return self.APP_DATABASE_URL
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_SECRET_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "*"
    
    # Parser Service
    PARSER_SERVICE_URL: str = "http://localhost:8001/v1"
    
    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()