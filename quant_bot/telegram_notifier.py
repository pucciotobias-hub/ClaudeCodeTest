"""
telegram_notifier.py
====================
Entrega del reporte por Telegram.

Toma el archivo recien generado (PDF o HTML de fallback) y lo envia al CHAT_ID
configurado usando la Bot API de Telegram via `requests` (sin dependencias
pesadas). Las credenciales se leen de variables de entorno (.env):

    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

Como crear el bot:
  1. Habla con @BotFather en Telegram -> /newbot -> copia el token.
  2. Escribile algo a tu bot, luego visita
     https://api.telegram.org/bot<TOKEN>/getUpdates para ver tu chat id.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

log = logging.getLogger("quant_bot.telegram")

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
_TIMEOUT = 60


def _credentials() -> tuple[Optional[str], Optional[str]]:
    return os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")


def send_message(text: str) -> bool:
    """Envia un mensaje de texto simple (usado para avisos / errores)."""
    token, chat_id = _credentials()
    if not token or not chat_id:
        log.error("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el entorno.")
        return False
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.error("Error enviando mensaje a Telegram: %s", exc)
        return False


def send_report(file_path: str, caption: Optional[str] = None) -> bool:
    """
    Envia el archivo de reporte como documento adjunto.

    Devuelve True si Telegram confirma la recepcion, False en caso contrario.
    Nunca lanza: los errores se loguean para no romper el pipeline.
    """
    token, chat_id = _credentials()
    if not token or not chat_id:
        log.error("Faltan credenciales de Telegram; no se envia el reporte.")
        return False

    if not os.path.exists(file_path):
        log.error("El archivo a enviar no existe: %s", file_path)
        return False

    caption = caption or "Reporte semanal Quant Equity Research"
    url = TELEGRAM_API.format(token=token, method="sendDocument")

    try:
        with open(file_path, "rb") as fh:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (os.path.basename(file_path), fh)},
                timeout=_TIMEOUT,
            )
        resp.raise_for_status()
        ok = resp.json().get("ok", False)
        if ok:
            log.info("Reporte enviado por Telegram: %s", file_path)
        else:
            log.error("Telegram rechazo el documento: %s", resp.text)
        return ok
    except requests.RequestException as exc:
        log.error("Error enviando documento a Telegram: %s", exc)
        return False
