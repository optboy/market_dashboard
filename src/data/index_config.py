from __future__ import annotations

from pathlib import Path

import yaml


CONFIG_PATH = Path("config/indices.yaml")


def load_indices(config_path: Path = CONFIG_PATH) -> list[dict]:
    """Load configured market indices."""
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return data.get("indices", [])
