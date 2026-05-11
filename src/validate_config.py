from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from calendar_utils import build_snapshot_filename, get_day_type, get_today
from config_loader import load_config


ROOT_DIR = Path(__file__).resolve().parents[1]


def read_columns(path: Path, layer_format: str) -> list[str]:
    if layer_format == "csv":
        df = pd.read_csv(path, dtype=str, nrows=5)
        return list(df.columns)

    if layer_format == "geojson":
        gdf = gpd.read_file(path, rows=5)
        return list(gdf.columns)

    raise ValueError(f"Formato não suportado: {layer_format}")


def main() -> None:
    config = load_config()

    timezone = config["project"].get("timezone", "America/Sao_Paulo")
    today = get_today(timezone)
    day_type = get_day_type(today)

    errors: list[str] = []

    print(f"Validando configuração para {today} ({day_type})")
    print()

    for layer_id, layer_cfg in config["layers"].items():
        extension = layer_cfg["extension"]
        snapshot_name = build_snapshot_filename(today, day_type, extension)
        snapshot_path = ROOT_DIR / "data" / "snapshots" / layer_id / snapshot_name

        print("=" * 80)
        print(f"Camada: {layer_cfg['title']}")
        print(f"Arquivo: {snapshot_path}")

        if not snapshot_path.exists():
            msg = f"Arquivo não encontrado para {layer_id}: {snapshot_path}"
            print(f"ERRO: {msg}")
            errors.append(msg)
            continue

        columns = read_columns(snapshot_path, layer_cfg["format"])
        required_columns = []

        configured_keys = layer_cfg.get("key", [])

        # Algumas colunas são derivadas na normalização, não existem no arquivo bruto.
        derived_columns = {
            "tipo_dia_operacional",
        }

        required_columns.extend(
            [col for col in configured_keys if col not in derived_columns]
        )

        required_columns.extend(layer_cfg.get("group_by", []))
        required_columns.extend(layer_cfg.get("summary_fields", []))

        if layer_id == "viagens_programadas_linha":
            required_columns.extend(layer_cfg.get("schedule_columns", {}).values())

        missing = sorted(set(required_columns) - set(columns))

        if missing:
            msg = f"{layer_id}: colunas ausentes: {missing}"
            print(f"ERRO: {msg}")
            errors.append(msg)
        else:
            print("OK: todas as colunas configuradas existem.")

        print()

    if errors:
        print("Validação final: ERRO")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Validação final: OK")


if __name__ == "__main__":
    main()