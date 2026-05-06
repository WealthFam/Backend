import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "WealthFam"
    API_V1_STR: str = "/api/v1"
    
    # Database
    # Priority: APP_DATABASE_URL (Env) -> DATABASE_URL (Env) -> Default
    APP_DATABASE_URL: Optional[str] = None
    DATABASE_URL_ENV: Optional[str] = Field(None, alias="DATABASE_URL")
    
    # Market Data Secondary Database
    MARKET_DATABASE_URL_ENV: Optional[str] = Field(None, alias="MARKET_DATABASE_URL")
    
    @property
    def DATABASE_URL(self) -> str:
        # 1. Try APP_DATABASE_URL
        url = self.APP_DATABASE_URL
        # 2. Try DATABASE_URL (aliased)
        if not url:
            url = self.DATABASE_URL_ENV
        # 3. Use default
        if not url:
            url = "duckdb:////data/family_finance_v3.duckdb"
            
        # Robustness Check: If running in Linux/Docker and path looks like relative but /data exists,
        # help out by making it absolute if it has 3 slashes instead of 4
        if url.startswith("duckdb:///data/") and os.path.exists("/data"):
             # duckdb:///data/foo -> duckdb:////data/foo
             url = url.replace("duckdb:///data/", "duckdb:////data/")
             
        return url

    @property
    def MARKET_DATABASE_URL(self) -> str:
        # 1. Try env variable
        url = self.MARKET_DATABASE_URL_ENV
        # 2. Default to secondary file in data folder
        if not url:
            url = "duckdb:///data/market_data.duckdb"
            
        # Robustness Check for Linux/Docker
        if url.startswith("duckdb:///data/") and os.path.exists("/data"):
             url = url.replace("duckdb:///data/", "duckdb:////data/")
             
        return url
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_SECRET_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "*"
    
    # Parser Service
    PARSER_SERVICE_URL: str = "http://localhost:8001/v1"
    
    # AI Agent Service (Internal)
    AGENT_SERVICE_URL: str = "http://localhost:8002/api/v1"
    
    model_config = ConfigDict(
        case_sensitive=True, 
        env_file=(".env", "backend/.env"), 
        extra="ignore", 
        populate_by_name=True
    )

settings = Settings()