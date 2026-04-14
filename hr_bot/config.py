import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    bot_token: SecretStr
    database_url: SecretStr

    model_config = SettingsConfigDict(env_file=os.path.join(BASE_DIR, '.env'), env_file_encoding='utf-8')

config = Settings()