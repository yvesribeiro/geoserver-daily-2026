from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def get_today(timezone: str = "America/Sao_Paulo") -> date:
    """
    Retorna a data atual conforme o fuso configurado.
    """
    return datetime.now(ZoneInfo(timezone)).date()


def get_day_type(current_date: date) -> str:
    """
    Classifica a data em:
    - util
    - sabado
    - domingo
    """
    weekday = current_date.weekday()

    if weekday <= 4:
        return "util"
    if weekday == 5:
        return "sabado"
    return "domingo"


def build_snapshot_filename(current_date: date, day_type: str, extension: str) -> str:
    """
    Monta o nome do snapshot diário.

    Exemplo:
    2026-05-11_util.csv
    """
    return f"{current_date.isoformat()}_{day_type}.{extension}"


def find_previous_snapshot(
    snapshot_dir: Path,
    current_date: date,
    day_type: str,
    extension: str,
) -> Path | None:
    """
    Encontra o snapshot anterior mais recente do mesmo tipo de dia.

    Se hoje é util, busca o último *_util.csv ou *_util.geojson anterior a hoje.
    Se hoje é sabado, busca o último *_sabado.
    Se hoje é domingo, busca o último *_domingo.
    """
    if not snapshot_dir.exists():
        return None

    candidates: list[tuple[date, Path]] = []

    pattern = f"*_{day_type}.{extension}"

    for path in snapshot_dir.glob(pattern):
        try:
            file_date_str = path.name.split("_")[0]
            file_date = date.fromisoformat(file_date_str)
        except Exception:
            continue

        if file_date < current_date:
            candidates.append((file_date, path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]