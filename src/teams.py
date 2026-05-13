from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
TEAMS_ENV_PATH = ROOT_DIR / "config" / "teams_webhook.env"

# Mantém a mensagem curta para evitar limite do Teams/Workflow.
MAX_TEAMS_MESSAGE_CHARS = 8000


def load_teams_webhook_url() -> str:
    """
    Carrega a URL do webhook do Teams a partir de config/teams_webhook.env.
    """
    load_dotenv(TEAMS_ENV_PATH)

    webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()

    if not webhook_url:
        raise ValueError(
            "TEAMS_WEBHOOK_URL não foi configurada em config/teams_webhook.env"
        )

    return webhook_url


def markdown_to_plain_text(markdown_text: str) -> str:
    """
    Mantém a mensagem legível no Teams.
    Remove apenas marcações básicas de Markdown, preservando quebras de linha.
    """
    text = markdown_text

    replacements = {
        "#": "",
        "**": "",
        "`": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Preserva linhas em branco, mas evita excesso.
    lines = []
    blank_count = 0

    for line in text.splitlines():
        clean = line.rstrip()

        if clean.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                lines.append("")
        else:
            blank_count = 0
            lines.append(clean)

    return "\n".join(lines).strip()


def compact_report_for_teams(
    report_text: str,
    max_chars: int = MAX_TEAMS_MESSAGE_CHARS,
) -> str:
    """
    Reduz o relatório caso fique grande demais para o Teams.
    """
    plain_text = markdown_to_plain_text(report_text)

    if len(plain_text) <= max_chars:
        return plain_text

    footer = (
        "\n\n[Mensagem resumida para evitar limite de tamanho do Teams.]"
        "\nDetalhes técnicos disponíveis nos arquivos locais de data/diffs e data/reports."
    )

    allowed = max_chars - len(footer) - 50

    if allowed < 1000:
        allowed = max_chars - 300

    return plain_text[:allowed].rstrip() + footer


def build_teams_payload(report_text: str) -> dict:
    """
    Monta payload simples para webhook do Teams.
    """
    compact_text = compact_report_for_teams(report_text)

    return {
        "text": compact_text,
    }


def send_teams_message(report_text: str, timeout_seconds: int = 60) -> None:
    """
    Envia o relatório para o Microsoft Teams via webhook.
    """
    webhook_url = load_teams_webhook_url()
    payload = build_teams_payload(report_text)

    response = requests.post(
        webhook_url,
        json=payload,
        timeout=timeout_seconds,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Erro ao enviar mensagem para o Teams. "
            f"Status: {response.status_code}. Resposta: {response.text[:500]}"
        )