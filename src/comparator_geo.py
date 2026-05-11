from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


def make_key(df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
    missing = sorted(set(key_cols) - set(df.columns))
    if missing:
        raise ValueError(f"Colunas de chave ausentes: {missing}")

    return df[key_cols].astype(str).agg("||".join, axis=1)


def geometry_to_wkt_series(gdf: gpd.GeoDataFrame) -> pd.Series:
    """
    Converte geometria para WKT.
    Como a tolerância é zero, qualquer diferença textual na geometria conta como alteração.
    """
    return gdf.geometry.apply(lambda geom: geom.wkt if geom is not None else "")


def compare_geo_layer(
    previous_path: Path,
    current_path: Path,
    layer_id: str,
    layer_cfg: dict[str, Any],
) -> dict[str, Any]:
    previous_gdf = gpd.read_file(previous_path)
    current_gdf = gpd.read_file(current_path)

    key_cols = layer_cfg["key"]

    previous_gdf["_comparison_key"] = make_key(previous_gdf, key_cols)
    current_gdf["_comparison_key"] = make_key(current_gdf, key_cols)

    previous_gdf["_geometry_wkt"] = geometry_to_wkt_series(previous_gdf)
    current_gdf["_geometry_wkt"] = geometry_to_wkt_series(current_gdf)

    previous_keys = set(previous_gdf["_comparison_key"])
    current_keys = set(current_gdf["_comparison_key"])

    added_keys = current_keys - previous_keys
    removed_keys = previous_keys - current_keys
    common_keys = previous_keys & current_keys

    added_gdf = current_gdf[current_gdf["_comparison_key"].isin(added_keys)].copy()
    removed_gdf = previous_gdf[previous_gdf["_comparison_key"].isin(removed_keys)].copy()

    geometry_changes = compare_common_geometries(
        previous_gdf=previous_gdf,
        current_gdf=current_gdf,
        common_keys=common_keys,
        key_cols=key_cols,
    )

    attribute_changes = compare_common_attributes(
        previous_gdf=previous_gdf,
        current_gdf=current_gdf,
        common_keys=common_keys,
        key_cols=key_cols,
        ignore_cols={
            "id",
            "FID",
            "geometry",
            "_comparison_key",
            "_geometry_wkt",
        },
    )

    result = {
        "layer_id": layer_id,
        "title": layer_cfg["title"],
        "previous_path": str(previous_path),
        "current_path": str(current_path),
        "counts": {
            "added": int(len(added_gdf)),
            "removed": int(len(removed_gdf)),
            "geometry_changed": int(len(geometry_changes)),
            "attribute_changed_cells": int(len(attribute_changes)),
            "attribute_changed_records": int(
                attribute_changes["_comparison_key"].nunique()
                if not attribute_changes.empty
                else 0
            ),
        },
        "added": added_gdf.drop(
            columns=["_comparison_key", "_geometry_wkt"],
            errors="ignore",
        ),
        "removed": removed_gdf.drop(
            columns=["_comparison_key", "_geometry_wkt"],
            errors="ignore",
        ),
        "geometry_changes": geometry_changes,
        "attribute_changes": attribute_changes,
        "summary": {},
    }

    if layer_id == "ponto_parada_v2025":
        result["summary"] = summarize_pontos(result, key_col="cod_parada_v2025")

    elif layer_id == "itinerario_espacial_linhas":
        result["summary"] = summarize_itinerarios(result)

    return result


def compare_common_geometries(
    previous_gdf: gpd.GeoDataFrame,
    current_gdf: gpd.GeoDataFrame,
    common_keys: set[str],
    key_cols: list[str],
) -> pd.DataFrame:
    previous_common = previous_gdf[
        previous_gdf["_comparison_key"].isin(common_keys)
    ].copy()
    current_common = current_gdf[
        current_gdf["_comparison_key"].isin(common_keys)
    ].copy()

    previous_common = previous_common.set_index("_comparison_key")
    current_common = current_common.set_index("_comparison_key")

    records: list[dict[str, Any]] = []

    for key in sorted(common_keys):
        previous_row = previous_common.loc[key]
        current_row = current_common.loc[key]

        if isinstance(previous_row, gpd.GeoDataFrame) or isinstance(previous_row, pd.DataFrame):
            previous_row = previous_row.iloc[0]
        if isinstance(current_row, gpd.GeoDataFrame) or isinstance(current_row, pd.DataFrame):
            current_row = current_row.iloc[0]

        old_wkt = str(previous_row.get("_geometry_wkt", ""))
        new_wkt = str(current_row.get("_geometry_wkt", ""))

        if old_wkt != new_wkt:
            record = {
                "_comparison_key": key,
                "tipo_mudanca": "geometria_alterada",
                "geometry_anterior_wkt": old_wkt,
                "geometry_atual_wkt": new_wkt,
            }

            for col in key_cols:
                record[col] = current_row.get(col, previous_row.get(col, ""))

            records.append(record)

    return pd.DataFrame(records)


def compare_common_attributes(
    previous_gdf: gpd.GeoDataFrame,
    current_gdf: gpd.GeoDataFrame,
    common_keys: set[str],
    key_cols: list[str],
    ignore_cols: set[str],
) -> pd.DataFrame:
    previous_common = previous_gdf[
        previous_gdf["_comparison_key"].isin(common_keys)
    ].copy()
    current_common = current_gdf[
        current_gdf["_comparison_key"].isin(common_keys)
    ].copy()

    previous_common = previous_common.set_index("_comparison_key")
    current_common = current_common.set_index("_comparison_key")

    comparable_cols = [
        col
        for col in previous_common.columns
        if col in current_common.columns
        and col not in ignore_cols
        and col not in key_cols
    ]

    records: list[dict[str, Any]] = []

    for key in sorted(common_keys):
        previous_row = previous_common.loc[key]
        current_row = current_common.loc[key]

        if isinstance(previous_row, gpd.GeoDataFrame) or isinstance(previous_row, pd.DataFrame):
            previous_row = previous_row.iloc[0]
        if isinstance(current_row, gpd.GeoDataFrame) or isinstance(current_row, pd.DataFrame):
            current_row = current_row.iloc[0]

        key_values = {}
        for col in key_cols:
            key_values[col] = current_row.get(col, previous_row.get(col, ""))

        for col in comparable_cols:
            old_value = str(previous_row.get(col, ""))
            new_value = str(current_row.get(col, ""))

            if old_value != new_value:
                record = {
                    "_comparison_key": key,
                    "coluna": col,
                    "valor_anterior": old_value,
                    "valor_atual": new_value,
                }
                record.update(key_values)
                records.append(record)

    return pd.DataFrame(records)


def summarize_pontos(result: dict[str, Any], key_col: str) -> dict[str, Any]:
    added = result["added"]
    removed = result["removed"]
    geometry_changes = result["geometry_changes"]
    attribute_changes = result["attribute_changes"]

    return {
        "added_codes": get_unique_values(added, key_col),
        "removed_codes": get_unique_values(removed, key_col),
        "geometry_changed_codes": get_unique_values(geometry_changes, key_col),
        "attribute_changed_codes": get_unique_values(attribute_changes, key_col),
    }


def summarize_itinerarios(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "added_lines": get_line_records(result["added"]),
        "removed_lines": get_line_records(result["removed"]),
        "geometry_changed_lines": get_line_records(result["geometry_changes"]),
        "attribute_changed_lines": get_line_records(result["attribute_changes"]),
    }


def get_unique_values(df: pd.DataFrame, col: str) -> list[str]:
    if df.empty or col not in df.columns:
        return []

    return sorted(df[col].astype(str).dropna().unique().tolist())


def get_line_records(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty:
        return []

    cols = [col for col in ["id_linha", "lin_sentido"] if col in df.columns]

    if not cols:
        return []

    out = df[cols].drop_duplicates().copy()
    return out.astype(str).to_dict(orient="records")


def save_geo_diff_outputs(
    result: dict[str, Any],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    layer_id = result["layer_id"]

    added = result["added"]
    removed = result["removed"]

    added.to_file(output_dir / f"{layer_id}_adicionados.geojson", driver="GeoJSON")
    removed.to_file(output_dir / f"{layer_id}_removidos.geojson", driver="GeoJSON")

    result["geometry_changes"].to_csv(
        output_dir / f"{layer_id}_alteracoes_geometria.csv",
        index=False,
        encoding="utf-8-sig",
    )

    result["attribute_changes"].to_csv(
        output_dir / f"{layer_id}_alteracoes_atributos.csv",
        index=False,
        encoding="utf-8-sig",
    )