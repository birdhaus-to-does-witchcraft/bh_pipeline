"""
Configuration management for the Wix API data pipeline.

This module handles loading configuration from environment variables and YAML files,
with validation and sensible defaults.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class WixAPIConfig(BaseModel):
    """Configuration for Wix API credentials and settings."""

    api_key: str = Field(..., description="Wix API key")
    account_id: Optional[str] = Field(None, description="Wix account ID")
    site_id: Optional[str] = Field(None, description="Wix site ID")
    base_url: str = Field("https://www.wixapis.com", description="Wix API base URL")

    @validator('api_key')
    def api_key_not_empty(cls, v):
        """Validate that API key is not empty."""
        if not v or v == "your_api_key_here":
            raise ValueError("WIX_API_KEY must be set to a valid API key")
        return v


class RateLimitConfig(BaseModel):
    """Configuration for API rate limiting."""

    max_calls: int = Field(100, description="Maximum calls per period")
    period: int = Field(60, description="Time period in seconds")


class RetryConfig(BaseModel):
    """Configuration for retry logic."""

    max_attempts: int = Field(3, description="Maximum retry attempts")
    min_wait: int = Field(4, description="Minimum wait time in seconds")
    max_wait: int = Field(10, description="Maximum wait time in seconds")


class DataPathConfig(BaseModel):
    """Configuration for data storage paths."""

    base_path: Path = Field(
        Path("/mnt/c/Users/saaku/the-lab/technologist/birdhaus_projects/birdhaus_data"),
        description="Base path for data storage"
    )
    raw_path: Optional[Path] = None
    processed_path: Optional[Path] = None
    archive_path: Optional[Path] = None
    metadata_path: Optional[Path] = None

    def __init__(self, **data):
        """Initialize and set up derived paths."""
        super().__init__(**data)
        if not self.raw_path:
            self.raw_path = self.base_path / "raw"
        if not self.processed_path:
            self.processed_path = self.base_path / "processed"
        if not self.archive_path:
            self.archive_path = self.base_path / "archive"
        if not self.metadata_path:
            self.metadata_path = self.base_path / "metadata"

    def ensure_paths_exist(self):
        """Create all data directories if they don't exist."""
        for path in [self.raw_path, self.processed_path, self.archive_path, self.metadata_path]:
            path.mkdir(parents=True, exist_ok=True)


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field("INFO", description="Logging level")
    log_dir: Path = Field(Path("logs"), description="Directory for log files")

    @validator('level')
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""

    wix_api: WixAPIConfig
    rate_limit: RateLimitConfig = RateLimitConfig()
    retry: RetryConfig = RetryConfig()
    data_paths: DataPathConfig = DataPathConfig()
    logging: LoggingConfig = LoggingConfig()

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "PipelineConfig":
        """
        Load configuration from environment variables.

        Args:
            env_file: Path to .env file (optional, defaults to .env in project root)

        Returns:
            PipelineConfig instance

        Example:
            >>> config = PipelineConfig.from_env()
            >>> print(config.wix_api.api_key)
        """
        # Load environment variables from .env file
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to find .env in current directory or parent directories
            load_dotenv(dotenv_path=".env", verbose=False)

        # Build configuration from environment variables
        return cls(
            wix_api=WixAPIConfig(
                api_key=os.getenv("WIX_API_KEY", ""),
                account_id=os.getenv("WIX_ACCOUNT_ID"),
                site_id=os.getenv("WIX_SITE_ID"),
                base_url=os.getenv("WIX_BASE_URL", "https://www.wixapis.com")
            ),
            rate_limit=RateLimitConfig(
                max_calls=int(os.getenv("RATE_LIMIT_MAX_CALLS", 100)),
                period=int(os.getenv("RATE_LIMIT_PERIOD", 60))
            ),
            retry=RetryConfig(
                max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", 3)),
                min_wait=int(os.getenv("RETRY_MIN_WAIT", 4)),
                max_wait=int(os.getenv("RETRY_MAX_WAIT", 10))
            ),
            data_paths=DataPathConfig(
                base_path=Path(os.getenv(
                    "DATA_BASE_PATH",
                    "/mnt/c/Users/saaku/the-lab/technologist/birdhaus_projects/birdhaus_data"
                ))
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                log_dir=Path(os.getenv("LOG_DIR", "logs"))
            )
        )

    @classmethod
    def from_yaml(cls, yaml_file: str) -> "PipelineConfig":
        """
        Load configuration from YAML file.

        Args:
            yaml_file: Path to YAML configuration file

        Returns:
            PipelineConfig instance

        Example:
            >>> config = PipelineConfig.from_yaml("config/pipeline_config.yaml")
        """
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_yaml(self, yaml_file: str):
        """
        Save configuration to YAML file.

        Args:
            yaml_file: Path to save YAML configuration file
        """
        with open(yaml_file, 'w') as f:
            yaml.dump(self.dict(), f, default_flow_style=False)


def load_config(
    env_file: Optional[str] = None,
    yaml_file: Optional[str] = None
) -> PipelineConfig:
    """
    Load configuration from environment or YAML file.

    Args:
        env_file: Path to .env file (optional)
        yaml_file: Path to YAML config file (optional, takes precedence over env)

    Returns:
        PipelineConfig instance

    Example:
        >>> config = load_config()  # Load from .env
        >>> config = load_config(yaml_file="config/pipeline_config.yaml")  # Load from YAML
    """
    if yaml_file:
        return PipelineConfig.from_yaml(yaml_file)
    else:
        return PipelineConfig.from_env(env_file)
