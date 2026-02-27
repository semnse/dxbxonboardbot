import os
os.environ['BITRIX_WEBHOOK_URL'] = 'test123'

from pydantic_settings import BaseSettings, SettingsConfigDict

class S(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)
    bitrix_webhook_url: str = ''
    
s = S()
print(f"bitrix_webhook_url: '{s.bitrix_webhook_url}'")
print(f"BITRIX_WEBHOOK_URL in env: '{os.environ.get('BITRIX_WEBHOOK_URL')}'")
