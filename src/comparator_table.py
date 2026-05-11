from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def make_key(df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
    """
    Cria chave composta textual para comparação.
    """
    missing = sorted(set(key_cols) - set(df.columns))
    if missing:
        raise ValueError(f"Colunas de chave ausentes: {missing}")

    return df[key_cols].astype(str).agg("||".join, axis=1)


def read_csv_normalized(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")


def compare_table_layer(
    previous_path: Path,
    current_path: Path,
    layer_id: str,
    layer_cfg: dict[str, Any],
) -> dict[str, Any]:
    """
    Compara duas camadas tabulares normalizadas.

    Retorna:
    - adicionados
    - removidos
    - alterações cadastrais em chaves existentes
    - resumos agrupados
    """
    previous_df = read_csv_normalized(previous_path)
    current_df = read_csv_normalized(current_path)

    key_cols = layer_cfg["key"]
    group_by = layer_cfg.get("group_by", [])

    previous_df["_comparison_key"] = make_key(previous_df, key_cols)
    current_df["_comparison_key"] = make_key(current_df, key_cols)

    previous_keys = set(previous_df["_comparison_key"])
    current_keys = set(current_df["_comparison_key"])

    added_keys = current_keys - previous_keys
    removed_keys = previous_keys - current_keys
    common_keys = previous_keys & current_keys

    added_df = current_df[current_df["_comparison_key"].isin(added_keys)].copy()
    removed_df = previous_df[previous_df["_comparison_key"].isin(removed_keys)].copy()

    modifications = compare_common_rows(
        previous_df=previous_df,
        current_df=current_df,
        common_keys=common_keys,
        key_cols=key_cols,
        ignore_cols={"_comparison_key", "FID"},
    )

    result = {
        "layer_id": layer_id,
        "title": layer_cfg["title"],
        "previous_path": str(previous_path),
        "current_path": str(current_path),
        "counts": {
            "added": int(len(added_df)),
            "removed": int(len(removed_df)),
            "modified_cells": int(len(modifications)),
            "modified_records": int(
                modifications["_comparison_key"].nunique()
                if not modifications.empty
                else 0
            ),
        },
        "added": added_df.drop(columns=["_comparison_key"], errors="ignore"),
        "removed": removed_df.drop(columns=["_comparison_key"], errors="ignore"),
        "modifications": modifications,
        "summary": {},
    }

    if layer_id == "frota_operadora":
        result["summary"] = summarize_frota(
            added_df=added_df,
            removed_df=removed_df,
            layer_cfg=layer_cfg,
        )

    elif layer_id == "viagens_programadas_linha":
        result["summary"] = summarize_viagens(
            added_df=added_df,
            removed_df=removed_df,
            group_by=group_by,
        )

    return result


def compare_common_rows(
    previous_df: pd.DataFrame,
    current_df: pd.DataFrame,
    common_keys: set[str],
    key_cols: list[str],
    ignore_cols: set[str] | None = None,
) -> pd.DataFrame:
    """
    Compara registros que existem nos dois snapshots.
    Retorna um DataFrame linha a linha com as células alteradas.
    """
    ignore_cols = ignore_cols or set()

    previous_common = previous_df[
        previous_df["_comparison_key"].isin(common_keys)
    ].copy()
    current_common = current_df[
        current_df["_comparison_key"].isin(common_keys)
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

        if isinstance(previous_row, pd.DataFrame):
            previous_row = previous_row.iloc[0]
        if isinstance(current_row, pd.DataFrame):
            current_row = current_row.iloc[0]

        key_values = {}
        for col in key_cols:
            if col in current_row.index:
                key_values[col] = current_row[col]
            elif col in previous_row.index:
                key_values[col] = previous_row[col]
            else:
                key_values[col] = ""

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


def summarize_frota(
    added_df: pd.DataFrame,
    removed_df: pd.DataFrame,
    layer_cfg: dict[str, Any],
) -> dict[str, Any]:
    """
    Resume frota por operadora, tipo_onibus e ano_fabrica.
    """
    group_col = "operadora"
    tipo_col = "tipo_onibus"
    ano_col = "ano_fabrica"

    return {
        "added_by_operator": summarize_frota_side(
            added_df,
            group_col=group_col,
            tipo_col=tipo_col,
            ano_col=ano_col,
        ),
        "removed_by_operator": summarize_frota_side(
            removed_df,
            group_col=group_col,
            tipo_col=tipo_col,
            ano_col=ano_col,
        ),
    }


def summarize_frota_side(
    df: pd.DataFrame,
    group_col: str,
    tipo_col: str,
    ano_col: str,
) -> list[dict[str, Any]]:
    if df.empty:
        return []

    records: list[dict[str, Any]] = []

    for operadora, df_operadora in df.groupby(group_col, dropna=False):
        tipos = []

        for tipo, df_tipo in df_operadora.groupby(tipo_col, dropna=False):
            anos = (
                df_tipo.groupby(ano_col, dropna=False)
                .size()
                .reset_index(name="quantidade")
                .sort_values(ano_col)
            )

            tipos.append(
                {
                    "tipo_onibus": str(tipo),
                    "total": int(len(df_tipo)),
                    "anos": [
                        {
                            "ano_fabrica": str(row[ano_col]),
                            "quantidade": int(row["quantidade"]),
                        }
                        for _, row in anos.iterrows()
                    ],
                }
            )

        records.append(
            {
                "operadora": str(operadora),
                "total": int(len(df_operadora)),
                "tipos": tipos,
            }
        )

    return records


def summarize_viagens(
    added_df: pd.DataFrame,
    removed_df: pd.DataFrame,
    group_by: list[str],
) -> list[dict[str, Any]]:
    """
    Resume viagens adicionadas/removidas por sg_operadora, cd_linha e cs_sentido.
    """
    added_summary = count_by_group(added_df, group_by, "adicionadas")
    removed_summary = count_by_group(removed_df, group_by, "removidas")

    merged: dict[tuple[str, ...], dict[str, Any]] = {}

    for item in added_summary + removed_summary:
        key = tuple(str(item[col]) for col in group_by)

        if key not in merged:
            merged[key] = {col: item[col] for col in group_by}
            merged[key]["adicionadas"] = 0
            merged[key]["removidas"] = 0

        merged[key]["adicionadas"] += int(item.get("adicionadas", 0))
        merged[key]["removidas"] += int(item.get("removidas", 0))

    return list(merged.values())


def count_by_group(
    df: pd.DataFrame,
    group_by: list[str],
    count_name: str,
) -> list[dict[str, Any]]:
    if df.empty:
        return []

    grouped = (
        df.groupby(group_by, dropna=False)
        .size()
        .reset_index(name=count_name)
        .sort_values(group_by)
    )

    return grouped.to_dict(orient="records")


def save_table_diff_outputs(
    result: dict[str, Any],
    output_dir: Path,
) -> None:
    """
    Salva CSVs detalhados de adicionados, removidos e modificações.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    layer_id = result["layer_id"]

    result["added"].to_csv(
        output_dir / f"{layer_id}_adicionados.csv",
        index=False,
        encoding="utf-8-sig",
    )

    result["removed"].to_csv(
        output_dir / f"{layer_id}_removidos.csv",
        index=False,
        encoding="utf-8-sig",
    )

    result["modifications"].to_csv(
        output_dir / f"{layer_id}_alteracoes_atributos.csv",
        index=False,
        encoding="utf-8-sig",
    )