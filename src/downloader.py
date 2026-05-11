from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

import requests


def build_wfs_url(
    base_wfs_url: str,
    type_name: str,
    output_format: str,
    version: str = "1.0.0",
) -> str:
    """
    Monta URL WFS para baixar uma camada do GeoServer.

    Exemplos de output_format:
    - csv
    - application/json
    """
    params = {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": output_format,
    }

    return f"{base_wfs_url}?{urlencode(params)}"


def output_format_for_layer(layer_format: str) -> str:
    """
    Converte o formato lógico da configuração para o outputFormat do GeoServer.
    """
    if layer_format == "csv":
        return "csv"

    if layer_format == "geojson":
        return "application/json"

    raise ValueError(f"Formato não suportado: {layer_format}")


def download_layer(
    base_wfs_url: str,
    version: str,
    layer_name: str,
    layer_format: str,
    output_path: Path,
    timeout_seconds: int = 120,
) -> str:
    """
    Baixa uma camada do GeoServer e salva no caminho informado.

    Se o arquivo já existir, ele será sobrescrito.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_format = output_format_for_layer(layer_format)
    url = build_wfs_url(
        base_wfs_url=base_wfs_url,
        type_name=layer_name,
        output_format=output_format,
        version=version,
    )

    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")

    if not response.content:
        raise RuntimeError(f"Resposta vazia para a camada {layer_name}")

    # Proteção simples contra erro XML/HTML salvo como CSV/GeoJSON.
    first_bytes = response.content[:300].decode("utf-8", errors="ignore").lower()
    if "<serviceexception" in first_bytes or "<html" in first_bytes:
        raise RuntimeError(
            f"O GeoServer retornou erro em vez de dados para {layer_name}. "
            f"Content-Type: {content_type}. Início da resposta: {first_bytes[:200]}"
        )

    output_path.write_bytes(response.content)

    return url