from __future__ import annotations

from pathlib import Path

from calendar_utils import (
    build_snapshot_filename,
    find_previous_snapshot,
    get_day_type,
    get_today,
)
from comparator_geo import compare_geo_layer, save_geo_diff_outputs
from comparator_table import compare_table_layer, save_table_diff_outputs
from config_loader import load_config
from downloader import download_layer
from normalizer import normalize_layer
from reporter import build_report, save_report
from teams import send_teams_message


ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    config = load_config()

    timezone = config["project"].get("timezone", "America/Sao_Paulo")
    today = get_today(timezone)
    day_type = get_day_type(today)

    geoserver_cfg = config["geoserver"]
    base_wfs_url = geoserver_cfg["base_wfs_url"]
    version = geoserver_cfg.get("version", "1.0.0")

    run_id = f"{today.isoformat()}_{day_type}"
    diff_dir = ROOT_DIR / "data" / "diffs" / run_id
    comparison_results = []

    print("Configuração carregada com sucesso.")
    print(f"Projeto: {config['project']['name']}")
    print(f"Data atual: {today}")
    print(f"Tipo de dia: {day_type}")
    print(f"Diretório de diferenças: {diff_dir}")
    print()

    for layer_id, layer_cfg in config["layers"].items():
        extension = layer_cfg["extension"]
        snapshot_name = build_snapshot_filename(today, day_type, extension)

        snapshot_dir = ROOT_DIR / "data" / "snapshots" / layer_id
        snapshot_path = snapshot_dir / snapshot_name

        normalized_dir = ROOT_DIR / "data" / "normalized" / layer_id
        normalized_path = normalized_dir / snapshot_name

        previous_normalized = find_previous_snapshot(
            normalized_dir,
            today,
            day_type,
            extension,
        )

        print(f"Camada: {layer_cfg['title']}")
        print(f"  ID: {layer_id}")
        print(f"  GeoServer: {layer_cfg['geoserver_name']}")
        print(f"  Snapshot bruto de hoje: {snapshot_path}")
        print(f"  Snapshot normalizado de hoje: {normalized_path}")
        print(
            "  Snapshot normalizado anterior comparável: "
            f"{previous_normalized if previous_normalized else 'não encontrado'}"
        )

        try:
            url = download_layer(
                base_wfs_url=base_wfs_url,
                version=version,
                layer_name=layer_cfg["geoserver_name"],
                layer_format=layer_cfg["format"],
                output_path=snapshot_path,
            )
            print("  Download: OK")
            print(f"  URL WFS: {url}")

            normalize_layer(
                layer_id=layer_id,
                layer_cfg=layer_cfg,
                input_path=snapshot_path,
                output_path=normalized_path,
                day_type=day_type,
            )
            print("  Normalização: OK")

            if previous_normalized is None:
                print("  Comparação: ignorada, pois não há snapshot anterior.")

            elif layer_cfg["format"] == "csv":
                result = compare_table_layer(
                    previous_path=previous_normalized,
                    current_path=normalized_path,
                    layer_id=layer_id,
                    layer_cfg=layer_cfg,
                )

                layer_diff_dir = diff_dir / layer_id
                save_table_diff_outputs(result, layer_diff_dir)
                comparison_results.append(result)

                print("  Comparação tabular: OK")
                print(f"    Adicionados: {result['counts']['added']}")
                print(f"    Removidos: {result['counts']['removed']}")
                print(f"    Registros modificados: {result['counts']['modified_records']}")
                print(f"    Células modificadas: {result['counts']['modified_cells']}")
                print(f"    Saída: {layer_diff_dir}")

            elif layer_cfg["format"] == "geojson":
                result = compare_geo_layer(
                    previous_path=previous_normalized,
                    current_path=normalized_path,
                    layer_id=layer_id,
                    layer_cfg=layer_cfg,
                )

                layer_diff_dir = diff_dir / layer_id
                save_geo_diff_outputs(result, layer_diff_dir)
                comparison_results.append(result)

                print("  Comparação espacial: OK")
                print(f"    Adicionados: {result['counts']['added']}")
                print(f"    Removidos: {result['counts']['removed']}")
                print(f"    Geometrias alteradas: {result['counts']['geometry_changed']}")
                print(
                    "    Registros com atributos modificados: "
                    f"{result['counts']['attribute_changed_records']}"
                )
                print(
                    "    Células de atributos modificadas: "
                    f"{result['counts']['attribute_changed_cells']}"
                )
                print(f"    Saída: {layer_diff_dir}")

        except Exception as exc:
            print("  ERRO")
            print(f"  Motivo: {exc}")

        print()

    report_text = build_report(
        run_id=run_id,
        current_date=today.isoformat(),
        day_type=day_type,
        results=comparison_results,
    )

    report_path = ROOT_DIR / "data" / "reports" / f"{run_id}.md"
    save_report(report_text, report_path)

    print("=" * 80)
    print(f"Relatório salvo em: {report_path}")

    send_teams = config.get("output", {}).get("send_teams", False)

    if send_teams:
        try:
            send_teams_message(report_text)
            print("Mensagem enviada ao Teams: OK")
        except Exception as exc:
            print("Mensagem enviada ao Teams: ERRO")
            print(f"Motivo: {exc}")
    else:
        print("Envio ao Teams: desativado em config/layers.yaml")


if __name__ == "__main__":
    main()