from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def _config_toml() -> str | None:
    """
    Attempts to find the config file by searching upwards for the project root,
    marked by a pyproject.toml file.
    :return: The path of config.toml as a string, or None if none
    """
    search = [Path.cwd(), *Path.cwd().parents]
    for parent in search:
        if (parent / "pyproject.toml").exists() and (parent / "config.toml").exists():
            return str(parent / "config.toml")
    return None


def _check_address(v: str) -> str:
    """Validate the configured address."""
    parts = v.rsplit(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1].isdigit():
        raise ValueError("address must be in host:port format")
    port = int(parts[1])
    if not (1 <= port <= 65535):
        raise ValueError("port must be between 1 and 65535")
    return v


class ManagerConfig(BaseModel):
    address: str
    retry_interval_s: int

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        return _check_address(v)


class ServiceConfig(BaseModel):
    name: str
    description: str
    address: str
    reflection: bool = True

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        return _check_address(v)


class ServerConfig(BaseSettings):
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
    def load(cls) -> "ServerConfig":
        return cls.model_validate({})
