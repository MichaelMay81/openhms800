from typing import Optional, Tuple, Type
from pydantic_settings import (
    BaseSettings, 
    SettingsConfigDict, 
    PydanticBaseSettingsSource,
    JsonConfigSettingsSource
)
import json
import os

class AppConfig(BaseSettings):
    ble_address: str = ""
    inverter_sn: str = ""
    activation_id: str = ""
    
    mqtt_enabled: bool = False
    mqtt_broker: str = "192.168.66.102"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_client_id: str = "hms800-ble"
    mqtt_prefix: str = "hoymiles/hms800"
    mqtt_keepalive: int = 60
    mqtt_qos: int = 1

    
    scan_interval: int = 30
    web_port: int = 8080
    
    model_config = SettingsConfigDict(env_prefix="HMS_", json_file="config.json")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            JsonConfigSettingsSource(settings_cls),
        )

    @classmethod
    def load(cls, path: str = "config.json"):
        # The new Pydantic source handles the file loading automatically
        return cls()

    def save(self, path: str = "config.json"):
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=4))
