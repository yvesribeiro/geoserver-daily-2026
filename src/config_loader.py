from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config" / "layers.yaml"


def load_config() -> dict[str, Any]:
    """
    Carrega o arquivo central de configuração da automação.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("O arquivo layers.yaml não retornou um dicionário válido.")

    if "layers" not in config:
        raise ValueError("O arquivo layers.yaml precisa conter a chave 'layers'.")

    return config