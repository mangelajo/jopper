"""Configuration management for Jopper.

Loads configuration from:
1. Environment variables (highest priority)
2. YAML config file
3. Default values (lowest priority)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class JoplinConfig:
    """Joplin API configuration."""

    token: str
    host: str = "localhost"
    port: int = 41184

    @property
    def url(self) -> str:
        """Return the full Joplin API URL."""
        return f"http://{self.host}:{self.port}"


@dataclass
class OpenWebUIConfig:
    """OpenWebUI API configuration."""

    url: str
    api_key: str
    knowledge_base_name: str = "Joplin Notes"
    collection_id: str | None = None  # Optional: specify collection ID directly


@dataclass
class SyncConfig:
    """Synchronization configuration."""

    mode: str = "all"  # "all" or "tagged"
    tags: list[str] = None
    interval_minutes: int = 60

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class Config:
    """Main configuration for Jopper."""

    joplin: JoplinConfig
    openwebui: OpenWebUIConfig
    sync: SyncConfig
    state_db_path: Path


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from environment variables and config file.

    Args:
        config_file: Path to YAML config file. If None, uses default location.

    Returns:
        Config object with all settings loaded.

    Raises:
        ValueError: If required configuration is missing.
    """
    # Default config file location
    if config_file is None:
        config_file = os.environ.get(
            "JOPPER_CONFIG_FILE", str(Path.home() / ".config" / "jopper" / "config.yaml")
        )

    # Load from YAML file if it exists
    yaml_config = {}
    config_path = Path(config_file)
    try:
        if config_path.exists():
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f) or {}
    except (PermissionError, OSError):
        # If we can't access the config file (e.g., in containers),
        # just use environment variables
        pass

    # Helper to get config value with priority: env var > yaml > default
    def get_config(
        env_key: str, yaml_keys: list[str], default: Optional[str] = None
    ) -> Optional[str]:
        """Get config value with priority: env var > yaml > default."""
        # Check environment variable first
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value

        # Check YAML config
        current = yaml_config
        for key in yaml_keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current if current is not None else default

    # Load Joplin config
    joplin_token = get_config("JOPPER_JOPLIN_TOKEN", ["joplin", "token"])
    if not joplin_token:
        raise ValueError(
            "Joplin token is required. Set JOPPER_JOPLIN_TOKEN env var or joplin.token in config."
        )

    joplin = JoplinConfig(
        token=joplin_token,
        host=get_config("JOPPER_JOPLIN_HOST", ["joplin", "host"], "localhost"),
        port=int(get_config("JOPPER_JOPLIN_PORT", ["joplin", "port"], "41184")),
    )

    # Load OpenWebUI config
    openwebui_url = get_config("JOPPER_OPENWEBUI_URL", ["openwebui", "url"])
    openwebui_api_key = get_config("JOPPER_OPENWEBUI_API_KEY", ["openwebui", "api_key"])

    if not openwebui_url:
        raise ValueError(
            "OpenWebUI URL is required. Set JOPPER_OPENWEBUI_URL env var or openwebui.url in config."
        )
    if not openwebui_api_key:
        raise ValueError(
            "OpenWebUI API key is required. Set JOPPER_OPENWEBUI_API_KEY env var or openwebui.api_key in config."
        )

    openwebui = OpenWebUIConfig(
        url=openwebui_url.rstrip("/"),
        api_key=openwebui_api_key,
        knowledge_base_name=get_config(
            "JOPPER_OPENWEBUI_KB_NAME", ["openwebui", "knowledge_base_name"], "Joplin Notes"
        ),
        collection_id=get_config(
            "JOPPER_OPENWEBUI_COLLECTION_ID", ["openwebui", "collection_id"], None
        ),
    )

    # Load Sync config
    sync_tags_str = get_config("JOPPER_SYNC_TAGS", ["sync", "tags"])
    sync_tags = []
    if sync_tags_str:
        if isinstance(sync_tags_str, str):
            sync_tags = [t.strip() for t in sync_tags_str.split(",") if t.strip()]
        elif isinstance(sync_tags_str, list):
            sync_tags = sync_tags_str

    sync = SyncConfig(
        mode=get_config("JOPPER_SYNC_MODE", ["sync", "mode"], "all"),
        tags=sync_tags,
        interval_minutes=int(
            get_config("JOPPER_SYNC_INTERVAL_MINUTES", ["sync", "interval_minutes"], "60")
        ),
    )

    # Load state DB path
    default_state_path = Path.home() / ".local" / "share" / "jopper" / "state.db"
    state_db_path = Path(
        get_config("JOPPER_STATE_DB_PATH", ["state_db_path"], str(default_state_path))
    )

    return Config(joplin=joplin, openwebui=openwebui, sync=sync, state_db_path=state_db_path)
