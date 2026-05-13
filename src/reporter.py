from __future__ import annotations

from pathlib import Path
from typing import Any


MAX_ITEMS_PER_SECTION = 10


def build_report(
    run_id: str,
    current_date: str,
    day_type: str,
    results: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append("📊 Auditor automático dos dados STPC/DF - SEMOB")
    lines.append(f"📅 Data: {current_date}")
    lines.append(f"🗓️ Tipo de dia: {format_day_type(day_type)}")
    lines.append("")

    if not results:
        lines.append("ℹ️ Situação geral")
        lines.append("Primeira execução ou ausência de base anterior comparável.")
        lines.append("")
        lines.append("Os dados foram salvos para permitir comparação nas próximas execuções.")
        return "\n".join(lines)

    changed_results = [result for result in results if has_changes(result)]

    if not changed_results:
        lines.append("✅ Situação geral")
        lines.append("Nenhuma alteração identificada nas bases monitoradas.")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        lines.extend(render_all_layers_status(results))
        return "\n".join(lines).strip()

    lines.append("⚠️ Situação geral")
    lines.append(
        f"Foram identificadas alterações em {len(changed_results)} de "
        f"{len(results)} bases monitoradas."
    )
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.extend(render_all_layers_status(results))

    return "\n".join(lines).strip()


def format_day_type(day_type: str) -> str:
    mapping = {
        "util": "Útil",
        "sabado": "Sábado",
        "domingo": "Domingo",
    }
    return mapping.get(day_type, day_type)


def render_all_layers_status(results: list[dict[str, Any]]) -> list[str]:
    layer_order = [
        "frota_operadora",
        "viagens_programadas_linha",
        "ponto_parada_v2025",
        "itinerario_espacial_linhas",
    ]

    result_by_layer = {result["layer_id"]: result for result in results}

    lines: list[str] = []

    for layer_id in layer_order:
        result = result_by_layer.get(layer_id)

        if result is None:
            continue

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

    return lines


def get_total_changes(result: dict[str, Any]) -> int:
    counts = result.get("counts", {})

    return int(
        counts.get("added", 0)
        + counts.get("removed", 0)
        + counts.get("modified_records", 0)
        + counts.get("geometry_changed", 0)
        + counts.get("attribute_changed_records", 0)
    )


def has_changes(result: dict[str, Any]) -> bool:
    return get_total_changes(result) > 0


def render_frota(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.append("🚍 Frota por Operadora")

    if not has_changes(result):
        lines.append("✅ Sem alterações identificadas.")
        return lines

    counts = result.get("counts", {})
    summary = result.get("summary", {})

    added_count = int(counts.get("added", 0))
    removed_count = int(counts.get("removed", 0))
    modified_count = int(counts.get("modified_records", 0))

    if added_count:
        lines.append(f"➕ {added_count} veículos adicionados.")

    if removed_count:
        lines.append(f"➖ {removed_count} veículos removidos.")

    if modified_count:
        lines.append(f"📝 {modified_count} veículos com alteração cadastral.")

    added = summary.get("added_by_operator", [])
    removed = summary.get("removed_by_operator", [])

    for item in added[:MAX_ITEMS_PER_SECTION]:
        operadora = item.get("operadora", "")
        total = item.get("total", 0)
        lines.append(f"• {operadora}: adicionados {total} veículos.")

        for tipo in item.get("tipos", []):
            anos_txt = ", ".join(
                f"{ano.get('quantidade', 0)} do ano {ano.get('ano_fabrica', '')}"
                for ano in tipo.get("anos", [])
            )
            tipo_onibus = tipo.get("tipo_onibus", "")
            total_tipo = tipo.get("total", 0)
            lines.append(f"  - {total_tipo} do tipo {tipo_onibus}: {anos_txt}.")

    if len(added) > MAX_ITEMS_PER_SECTION:
        lines.append(f"• Outros {len(added) - MAX_ITEMS_PER_SECTION} agrupamentos não listados.")

    for item in removed[:MAX_ITEMS_PER_SECTION]:
        operadora = item.get("operadora", "")
        total = item.get("total", 0)
        lines.append(f"• {operadora}: removidos {total} veículos.")

        for tipo in item.get("tipos", []):
            anos_txt = ", ".join(
                f"{ano.get('quantidade', 0)} do ano {ano.get('ano_fabrica', '')}"
                for ano in tipo.get("anos", [])
            )
            tipo_onibus = tipo.get("tipo_onibus", "")
            total_tipo = tipo.get("total", 0)
            lines.append(f"  - {total_tipo} do tipo {tipo_onibus}: {anos_txt}.")

    if len(removed) > MAX_ITEMS_PER_SECTION:
        lines.append(f"• Outros {len(removed) - MAX_ITEMS_PER_SECTION} agrupamentos não listados.")

    return lines


def render_viagens(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.append("🚌 Viagens programadas por linha")

    if not has_changes(result):
        lines.append("✅ Sem alterações identificadas.")
        return lines

    counts = result.get("counts", {})
    summary = result.get("summary", [])

    added_count = int(counts.get("added", 0))
    removed_count = int(counts.get("removed", 0))

    if added_count:
        lines.append(f"➕ {added_count} viagens adicionadas.")

    if removed_count:
        lines.append(f"➖ {removed_count} viagens removidas.")

    visible_summary = [
        item
        for item in summary
        if int(item.get("adicionadas", 0)) or int(item.get("removidas", 0))
    ]

    for item in visible_summary[:MAX_ITEMS_PER_SECTION]:
        sg_operadora = item.get("sg_operadora", "")
        cd_linha = item.get("cd_linha", "")
        cs_sentido = item.get("cs_sentido", "")
        adicionadas = int(item.get("adicionadas", 0))
        removidas = int(item.get("removidas", 0))

        partes = []
        if adicionadas:
            partes.append(f"{adicionadas} adicionadas")
        if removidas:
            partes.append(f"{removidas} removidas")

        lines.append(
            f"• {sg_operadora} - Linha {cd_linha}, sentido {cs_sentido}: "
            + ", ".join(partes)
            + "."
        )

    if len(visible_summary) > MAX_ITEMS_PER_SECTION:
        lines.append(
            f"• Outros {len(visible_summary) - MAX_ITEMS_PER_SECTION} agrupamentos não listados."
        )

    return lines


def render_pontos(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.append("📍 Pontos de parada")

    if not has_changes(result):
        lines.append("✅ Sem alterações identificadas.")
        return lines

    counts = result.get("counts", {})
    summary = result.get("summary", {})

    added_count = int(counts.get("added", 0))
    removed_count = int(counts.get("removed", 0))
    geometry_count = int(counts.get("geometry_changed", 0))
    attribute_count = int(counts.get("attribute_changed_records", 0))

    if added_count:
        lines.append(f"➕ {added_count} pontos adicionados.")
        add_codes(lines, "Códigos adicionados", summary.get("added_codes", []))

    if removed_count:
        lines.append(f"➖ {removed_count} pontos removidos.")
        add_codes(lines, "Códigos removidos", summary.get("removed_codes", []))

    if geometry_count:
        lines.append(f"📍 {geometry_count} pontos com localização alterada.")
        add_codes(
            lines,
            "Códigos com localização alterada",
            summary.get("geometry_changed_codes", []),
        )

    if attribute_count:
        lines.append(f"📝 {attribute_count} pontos com dados cadastrais alterados.")
        add_codes(
            lines,
            "Códigos com dados cadastrais alterados",
            summary.get("attribute_changed_codes", []),
        )

    return lines


def render_itinerarios(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.append("🗺️ Itinerário espacial")

    if not has_changes(result):
        lines.append("✅ Sem alterações identificadas.")
        return lines

    counts = result.get("counts", {})
    summary = result.get("summary", {})

    added_count = int(counts.get("added", 0))
    removed_count = int(counts.get("removed", 0))
    geometry_count = int(counts.get("geometry_changed", 0))
    attribute_count = int(counts.get("attribute_changed_records", 0))

    if added_count:
        lines.append(f"➕ {added_count} itinerários adicionados.")
        add_lines(lines, summary.get("added_lines", []))

    if removed_count:
        lines.append(f"➖ {removed_count} itinerários removidos.")
        add_lines(lines, summary.get("removed_lines", []))

    if geometry_count:
        lines.append(f"🛣️ {geometry_count} itinerários com trajeto alterado.")
        add_lines(lines, summary.get("geometry_changed_lines", []))

    if attribute_count:
        lines.append(f"📝 {attribute_count} itinerários com dados cadastrais alterados.")
        add_lines(lines, summary.get("attribute_changed_lines", []))

    return lines


def add_codes(lines: list[str], title: str, codes: list[str]) -> None:
    if not codes:
        return

    shown = codes[:MAX_ITEMS_PER_SECTION]
    lines.append(f"  {title}: {', '.join(shown)}.")

    if len(codes) > MAX_ITEMS_PER_SECTION:
        lines.append(f"  Outros {len(codes) - MAX_ITEMS_PER_SECTION} registros não listados.")


def add_lines(lines: list[str], records: list[dict[str, Any]]) -> None:
    if not records:
        return

    for record in records[:MAX_ITEMS_PER_SECTION]:
        id_linha = record.get("id_linha", "")
        sentido = record.get("lin_sentido", "")
        lines.append(f"  • Linha {id_linha}, sentido {sentido}.")

    if len(records) > MAX_ITEMS_PER_SECTION:
        lines.append(f"  Outros {len(records) - MAX_ITEMS_PER_SECTION} registros não listados.")


def render_generic(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    title = result.get("title", result.get("layer_id", "Camada"))
    lines.append(f"📌 {title}")

    if not has_changes(result):
        lines.append("✅ Sem alterações identificadas.")
        return lines

    counts = result.get("counts", {})

    for key, value in counts.items():
        try:
            number = int(value)
        except Exception:
            continue

        if number:
            lines.append(f"• {key}: {number}")

    return lines


def save_report(report_text: str, report_path: Path) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path