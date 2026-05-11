from __future__ import annotations

from pathlib import Path
from typing import Any


def build_report(
    run_id: str,
    current_date: str,
    day_type: str,
    results: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append(f"# Relatório diário GeoServer — {current_date}")
    lines.append("")
    lines.append(f"**Tipo de dia:** {day_type}")
    lines.append(f"**Execução:** {run_id}")
    lines.append("")

    if not results:
        lines.append("Nenhuma comparação foi executada, pois não havia snapshots anteriores disponíveis.")
        return "\n".join(lines)

    total_changes = sum(get_total_changes(result) for result in results)

    if total_changes == 0:
        lines.append("✅ Nenhuma alteração identificada nas camadas comparadas.")
        lines.append("")

    for result in results:
        layer_id = result["layer_id"]

        if layer_id == "frota_operadora":
            lines.extend(render_frota(result))
        elif layer_id == "viagens_programadas_linha":
            lines.extend(render_viagens(result))
        elif layer_id == "ponto_parada_v2025":
            lines.extend(render_pontos(result))
        elif layer_id == "itinerario_espacial_linhas":
            lines.extend(render_itinerarios(result))
        else:
            lines.extend(render_generic(result))

        lines.append("")

    return "\n".join(lines)


def get_total_changes(result: dict[str, Any]) -> int:
    counts = result.get("counts", {})

    return int(
        counts.get("added", 0)
        + counts.get("removed", 0)
        + counts.get("modified_records", 0)
        + counts.get("geometry_changed", 0)
        + counts.get("attribute_changed_records", 0)
    )


def render_frota(result: dict[str, Any]) -> list[str]:
    counts = result["counts"]
    summary = result.get("summary", {})

    lines = []
    lines.append("## 🚍 Frota por Operadora")
    lines.append("")
    lines.append(f"- Veículos adicionados: **{counts.get('added', 0)}**")
    lines.append(f"- Veículos removidos: **{counts.get('removed', 0)}**")
    lines.append(f"- Veículos com alteração cadastral: **{counts.get('modified_records', 0)}**")
    lines.append("")

    added = summary.get("added_by_operator", [])
    removed = summary.get("removed_by_operator", [])

    if added:
        lines.append("### Adições por operadora")
        lines.append("")
        for item in added:
            lines.append(f"**{item['operadora']}** — adicionados {item['total']} veículos.")
            for tipo in item["tipos"]:
                anos_txt = ", ".join(
                    f"{ano['quantidade']} do ano {ano['ano_fabrica']}"
                    for ano in tipo["anos"]
                )
                lines.append(f"- {tipo['total']} do tipo {tipo['tipo_onibus']}: {anos_txt}.")
            lines.append("")

    if removed:
        lines.append("### Remoções por operadora")
        lines.append("")
        for item in removed:
            lines.append(f"**{item['operadora']}** — removidos {item['total']} veículos.")
            for tipo in item["tipos"]:
                anos_txt = ", ".join(
                    f"{ano['quantidade']} do ano {ano['ano_fabrica']}"
                    for ano in tipo["anos"]
                )
                lines.append(f"- {tipo['total']} do tipo {tipo['tipo_onibus']}: {anos_txt}.")
            lines.append("")

    if counts.get("modified_records", 0):
        lines.append("Alterações cadastrais em veículos existentes foram salvas no log técnico.")
        lines.append("")

    return lines


def render_viagens(result: dict[str, Any]) -> list[str]:
    counts = result["counts"]
    summary = result.get("summary", [])

    lines = []
    lines.append("## 🚌 Viagens Programadas por Linha")
    lines.append("")
    lines.append(f"- Viagens adicionadas: **{counts.get('added', 0)}**")
    lines.append(f"- Viagens removidas: **{counts.get('removed', 0)}**")
    lines.append("")

    if summary:
        lines.append("### Alterações por operadora, linha e sentido")
        lines.append("")
        for item in summary:
            sg_operadora = item.get("sg_operadora", "")
            cd_linha = item.get("cd_linha", "")
            cs_sentido = item.get("cs_sentido", "")
            adicionadas = item.get("adicionadas", 0)
            removidas = item.get("removidas", 0)

            lines.append(
                f"- **{sg_operadora}** — Linha **{cd_linha}**, sentido **{cs_sentido}**: "
                f"{adicionadas} adicionadas, {removidas} removidas."
            )
        lines.append("")

    return lines


def render_pontos(result: dict[str, Any]) -> list[str]:
    counts = result["counts"]
    summary = result.get("summary", {})

    lines = []
    lines.append("## 📍 Ponto de paradas 2025")
    lines.append("")
    lines.append(f"- Paradas adicionadas: **{counts.get('added', 0)}**")
    lines.append(f"- Paradas removidas: **{counts.get('removed', 0)}**")
    lines.append(f"- Paradas com geometria alterada: **{counts.get('geometry_changed', 0)}**")
    lines.append(
        f"- Paradas com atributos alterados: **{counts.get('attribute_changed_records', 0)}**"
    )
    lines.append("")

    added_codes = summary.get("added_codes", [])
    removed_codes = summary.get("removed_codes", [])
    geometry_codes = summary.get("geometry_changed_codes", [])
    attribute_codes = summary.get("attribute_changed_codes", [])

    if added_codes:
        lines.append(f"**Códigos adicionados:** {', '.join(added_codes)}")
        lines.append("")

    if removed_codes:
        lines.append(f"**Códigos removidos:** {', '.join(removed_codes)}")
        lines.append("")

    if geometry_codes:
        lines.append(f"**Códigos com geometria alterada:** {', '.join(geometry_codes)}")
        lines.append("")

    if attribute_codes:
        lines.append(f"**Códigos com atributos alterados:** {', '.join(attribute_codes)}")
        lines.append("")

    return lines


def render_itinerarios(result: dict[str, Any]) -> list[str]:
    counts = result["counts"]
    summary = result.get("summary", {})

    lines = []
    lines.append("## 🗺️ Itinerário Espacial das Linhas")
    lines.append("")
    lines.append(f"- Itinerários adicionados: **{counts.get('added', 0)}**")
    lines.append(f"- Itinerários removidos: **{counts.get('removed', 0)}**")
    lines.append(f"- Itinerários com trajeto alterado: **{counts.get('geometry_changed', 0)}**")
    lines.append(
        f"- Itinerários com atributos alterados: **{counts.get('attribute_changed_records', 0)}**"
    )
    lines.append("")

    added = summary.get("added_lines", [])
    removed = summary.get("removed_lines", [])
    geometry_changed = summary.get("geometry_changed_lines", [])
    attribute_changed = summary.get("attribute_changed_lines", [])

    if added:
        lines.append("### Itinerários adicionados")
        lines.extend(render_line_records(added))
        lines.append("")

    if removed:
        lines.append("### Itinerários removidos")
        lines.extend(render_line_records(removed))
        lines.append("")

    if geometry_changed:
        lines.append("### Itinerários com trajeto alterado")
        lines.extend(render_line_records(geometry_changed))
        lines.append("")

    if attribute_changed:
        lines.append("### Itinerários com atributos alterados")
        lines.extend(render_line_records(attribute_changed))
        lines.append("")

    return lines


def render_line_records(records: list[dict[str, Any]]) -> list[str]:
    lines = []

    for record in records:
        id_linha = record.get("id_linha", "")
        sentido = record.get("lin_sentido", "")
        lines.append(f"- id_linha **{id_linha}** | sentido **{sentido}**")

    return lines


def render_generic(result: dict[str, Any]) -> list[str]:
    counts = result.get("counts", {})

    lines = []
    lines.append(f"## {result.get('title', result.get('layer_id'))}")
    lines.append("")
    for key, value in counts.items():
        lines.append(f"- {key}: **{value}**")
    lines.append("")

    return lines


def save_report(report_text: str, report_path: Path) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path