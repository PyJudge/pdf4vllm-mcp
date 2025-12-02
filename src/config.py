"""
PDF MCP Server configuration
Supports presets via environment variables or config.json
"""
import json
import logging
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """PDF MCP Server configuration using Pydantic BaseSettings"""

    model_config = SettingsConfigDict(
        env_prefix='PDF_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # Core limits
    max_pages_per_request: int = 10
    max_images_per_request: int = 50
    max_recursion_depth: int = 2
    max_suggested_ranges: int = 5  # Number of suggested ranges when limit exceeded

    # Image processing
    max_image_dimension: int = 842  # A4 height in pixels
    min_image_dimension: int = 28
    max_aspect_ratio: float = 15.0
    page_image_dpi: int = 100
    jpeg_quality: int = 85

    # Header/Footer filtering
    header_footer_ratio: float = 0.06
    footer_start_ratio: float = 0.94

    # Text corruption detection
    corruption_threshold: float = 0.3

    # Extraction mode
    default_extraction_mode: Literal["auto", "text_only", "image_only"] = "auto"

    def model_post_init(self, __context) -> None:
        """Load additional config from config.json if exists"""
        config_path = Path(__file__).parent.parent / "config.json"

        if not config_path.exists():
            return

        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Update from file (only if not set by environment variables)
            for key, value in config_data.items():
                if hasattr(self, key):
                    # Check if current value is still the default
                    field_info = self.model_fields.get(key)
                    if field_info and getattr(self, key) == field_info.default:
                        setattr(self, key, value)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in config file {config_path}: {e}. Using default values.")
        except Exception as e:
            logger.warning(f"Failed to load config file {config_path}: {e}. Using default values.")



# Global configuration instance
config = Config()