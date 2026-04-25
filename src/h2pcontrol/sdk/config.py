from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def _config_toml() -> str | None:
    search = [Path.cwd(), *Path.cwd().parents]
    for parent in search:
        if (parent / "pyproject.toml").exists():
            return str(parent / "config.toml")
    return None


class ManagerConfig(BaseModel):
    address: str
    heartbeat_interval_s: int


class ServiceConfig(BaseModel):
    name: str
    description: str
    host: str
    port: int


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=_config_toml(),
        env_nested_delimiter="__",
    )
    manager: ManagerConfig
    service: ServiceConfig

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return env_settings, TomlConfigSettingsSource(settings_cls)

    @classmethod
    def load(cls) -> "Config":
        return cls.model_validate({})
