from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


NULL_LIKE_VALUES = {
    "",
    " ",
    "nan",
    "NaN",
    "None",
    "none",
    "NULL",
    "null",
}


def clean_value(value: Any) -> str:
    """
    Converte valores para string limpa, evitando diferenças falsas.
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text in NULL_LIKE_VALUES:
        return ""

    return text


def normalize_dataframe_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza todos os valores do DataFrame para string limpa.
    """
    out = df.copy()

    for col in out.columns:
        out[col] = out[col].map(clean_value)

    return out


def is_active_day_marker(value: Any) -> bool:
    """
    Interpreta marcação de dia ativo nas colunas st_*.

    Pela inspeção da camada, os valores vêm como S/N.
    """
    text = clean_value(value).upper()
    return text in {"S", "SIM", "TRUE", "1", "Y", "YES"}


def normalize_frota_operadora(
    input_path: Path,
    output_path: Path,
) -> Path:
    df = pd.read_csv(input_path, dtype=str)
    df = normalize_dataframe_values(df)

    # Remove duplicatas exatas, se existirem.
    df = df.drop_duplicates()

    # Garante ordenação estável para facilitar comparação/log.
    sort_cols = [col for col in ["operadora", "numero_veiculo"] if col in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


def normalize_viagens_programadas_linha(
    input_path: Path,
    output_path: Path,
    layer_cfg: dict[str, Any],
    day_type: str,
) -> Path:
    df = pd.read_csv(input_path, dtype=str)
    df = normalize_dataframe_values(df)

    day_columns = layer_cfg["day_type_filter"][day_type]

    existing_day_columns = [col for col in day_columns if col in df.columns]
    if not existing_day_columns:
        raise ValueError(
            f"Nenhuma coluna de dia encontrada para day_type={day_type}. "
            f"Esperadas: {day_columns}"
        )

    # Mantém apenas viagens ativas para o tipo de dia da execução.
    active_mask = df[existing_day_columns].apply(
        lambda row: any(is_active_day_marker(value) for value in row),
        axis=1,
    )

    df = df.loc[active_mask].copy()
    df["tipo_dia_operacional"] = day_type

    # Remove duplicatas de chave operacional, se houver.
    key_cols = layer_cfg["key"]
    existing_key_cols = [col for col in key_cols if col in df.columns]

    if len(existing_key_cols) != len(key_cols):
        missing = sorted(set(key_cols) - set(existing_key_cols))
        raise ValueError(f"Colunas de chave ausentes após normalização: {missing}")

    df = df.drop_duplicates(subset=key_cols)

    sort_cols = [
        col
        for col in ["sg_operadora", "cd_linha", "cs_sentido", "hora_prevista"]
        if col in df.columns
    ]
    if sort_cols:
        df = df.sort_values(sort_cols)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


def normalize_geojson_layer(
    input_path: Path,
    output_path: Path,
    layer_cfg: dict[str, Any],
) -> Path:
    gdf = gpd.read_file(input_path)

    # Normaliza atributos, mas preserva a geometria.
    geometry_col = gdf.geometry.name
    attr_cols = [col for col in gdf.columns if col != geometry_col]

    for col in attr_cols:
        gdf[col] = gdf[col].map(clean_value)

    key_cols = layer_cfg["key"]

    missing = sorted(set(key_cols) - set(gdf.columns))
    if missing:
        raise ValueError(f"Colunas de chave ausentes no GeoJSON: {missing}")

    # Remove duplicatas exatas pela chave, se houver.
    # Se houver duplicidade de chave com geometria diferente, isso precisará ser tratado depois.
    gdf = gdf.drop_duplicates(subset=key_cols, keep="first")

    if key_cols:
        gdf = gdf.sort_values(key_cols)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")

    return output_path


def normalize_layer(
    layer_id: str,
    layer_cfg: dict[str, Any],
    input_path: Path,
    output_path: Path,
    day_type: str,
) -> Path:
    """
    Normaliza uma camada conforme sua regra.
    """
    if layer_id == "frota_operadora":
        return normalize_frota_operadora(input_path, output_path)

    if layer_id == "viagens_programadas_linha":
        return normalize_viagens_programadas_linha(
            input_path=input_path,
            output_path=output_path,
            layer_cfg=layer_cfg,
            day_type=day_type,
        )

    if layer_cfg["format"] == "geojson":
        return normalize_geojson_layer(
            input_path=input_path,
            output_path=output_path,
            layer_cfg=layer_cfg,
        )

    raise ValueError(f"Normalização não implementada para layer_id={layer_id}")