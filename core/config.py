import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Search Engine API"
    DEBUG: bool = False
    
    # MongoDB Settings
    MONGO_URI: str = "mongodb+srv://yosef0102233_db_user:Abc%40123456@clustergermany.oodrnem.mongodb.net/"
    MONGO_DB_NAME: str = "search_engine_matrial"

    # Automatically find the .env file in the root
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra env vars not defined here
    )

settings = Settings()

