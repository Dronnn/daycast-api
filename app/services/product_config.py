from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "product.yml"
_config: dict | None = None


def get_product_config() -> dict:
    global _config
    if _config is None:
        _config = yaml.safe_load(_CONFIG_PATH.read_text())
    return _config


def get_channels() -> dict:
    return get_product_config()["channels"]


def get_lengths() -> dict:
    return get_product_config().get("lengths", {})


def get_ai_config() -> dict:
    return get_product_config()["ai"]
