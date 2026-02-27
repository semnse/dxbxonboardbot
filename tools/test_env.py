from pydantic_settings import BaseSettings, SettingsConfigDict

class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    bitrix_webhook_url: str = ""

s = TestSettings()
print(f"BITRIX_WEBHOOK_URL: '{s.bitrix_webhook_url}'")
