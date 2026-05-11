from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from calendar_utils import build_snapshot_filename, get_day_type, get_today
from config_loader import load_config


ROOT_DIR = Path(__file__).resolve().parents[1]


def inspect_csv(path: Path) -> None:
    df = pd.read_csv(path, dtype=str)

    print(f"  Linhas: {len(df)}")
    print(f"  Colunas ({len(df.columns)}):")
    for col in df.columns:
        print(f"    - {col}")

    print()
    print("  Primeiros registros:")
    print(df.head(3).to_string(index=False))


def inspect_geojson(path: Path) -> None:
    gdf = gpd.read_file(path)

    print(f"  Features: {len(gdf)}")
    print(f"  Colunas ({len(gdf.columns)}):")
    for col in gdf.columns:
        print(f"    - {col}")

    print()
    print("  Primeiros registros sem geometria:")
    cols_without_geometry = [c for c in gdf.columns if c != "geometry"]
    print(gdf[cols_without_geometry].head(3).to_string(index=False))


def main() -> None:
    config = load_config()

    timezone = config["project"].get("timezone", "America/Sao_Paulo")
    today = get_today(timezone)
    day_type = get_day_type(today)

    print(f"Data: {today}")
    print(f"Tipo de dia: {day_type}")
    print()

    for layer_id, layer_cfg in config["layers"].items():
        extension = layer_cfg["extension"]
        snapshot_name = build_snapshot_filename(today, day_type, extension)
        snapshot_path = ROOT_DIR / "data" / "snapshots" / layer_id / snapshot_name

        print("=" * 80)
        print(f"Camada: {layer_cfg['title']}")
        print(f"Arquivo: {snapshot_path}")
        print("=" * 80)

        if not snapshot_path.exists():
            print("  Arquivo não encontrado.")
            print()
            continue

        try:
            if layer_cfg["format"] == "csv":
                inspect_csv(snapshot_path)
            elif layer_cfg["format"] == "geojson":
                inspect_geojson(snapshot_path)
            else:
                print(f"  Formato não suportado: {layer_cfg['format']}")
        except Exception as exc:
            print(f"  ERRO AO INSPECIONAR: {exc}")

        print()


if __name__ == "__main__":
    main()