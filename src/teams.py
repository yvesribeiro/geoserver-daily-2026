from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
TEAMS_ENV_PATH = ROOT_DIR / "config" / "teams_webhook.env"


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
    Converte o relatório Markdown para um texto simples compatível com mensagens básicas.
    Mantém boa legibilidade no Teams.
    """
    text = markdown_text

    replacements = {
        "# ": "",
        "## ": "",
        "### ": "",
        "**": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def build_teams_payload(report_text: str) -> dict:
    """
    Monta payload simples para webhook do Teams.

    Esse formato funciona com muitos webhooks que aceitam:
    {
      "text": "mensagem"
    }
    """
    plain_text = markdown_to_plain_text(report_text)

    return {
        "text": plain_text,
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