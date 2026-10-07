"""Avisa por Telegram cuando termina un estudio de GGAL.

Lo llama ggal_estudio.ps1 al final de cada corrida. Manda lo que alcanza para
decidir si hace falta abrir el informe: el encabezado con precio e indicadores,
"Que cambio desde el informe anterior" y "Escenarios". El informe entero pasa los
4096 caracteres que admite un mensaje.

Credenciales: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en el .env de la raiz del repo
(gitignoreado) o en el entorno. Sin ellas no manda nada y sale con codigo 2: el
wrapper lo anota en el log y sigue, un aviso que falla no es una corrida que falla.

Uso:
    python scripts/telegram_aviso.py --informe estudios/ggal/2026-10-07-apertura.md
    python scripts/telegram_aviso.py --texto "GGAL apertura: la corrida fallo (codigo 1)"
    python scripts/telegram_aviso.py --chat-id     # muestra el chat id despues de escribirle al bot

Para configurarlo: en Telegram, @BotFather -> /newbot -> copiar el token al .env.
Escribirle cualquier cosa al bot nuevo y correr --chat-id para saber el otro dato.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
TOPE = 3900  # Telegram corta en 4096
PAGINA_SEMANAL = "https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67"
SECCIONES = ("Qué cambió desde el informe anterior", "Escenarios")


def credenciales():
    env = {}
    archivo = REPO / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    leer = lambda k: os.getenv(k) or env.get(k)
    return leer("TELEGRAM_BOT_TOKEN"), leer("TELEGRAM_CHAT_ID")


def llamar(token, metodo, **datos):
    cuerpo = urllib.parse.urlencode(datos).encode("utf-8") if datos else None
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{metodo}", data=cuerpo, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:   # Telegram explica el rechazo en el cuerpo
        return json.load(e)


def plano(md):
    """Markdown del informe a texto que se lee bien en el celular (sin parse_mode: un asterisco suelto lo rompe)."""
    md = re.sub(r"\*\*(.+?)\*\*", r"\1", md, flags=re.S)
    md = re.sub(r"`([^`]*)`", r"\1", md)
    md = re.sub(r"^\*([^*\n]+)\*$", r"\1", md, flags=re.M)   # el descargo final va en cursiva
    md = re.sub(r"^---+$", "", md, flags=re.M)
    md = re.sub(r"^#+\s*(.+)$", lambda m: m.group(1).upper(), md, flags=re.M)
    # Los informes cortan las lineas a ~110 columnas: se vuelven a unir los parrafos y las viñetas.
    md = re.sub(r"(?<=\S)\n(?=[^\n\-|#\s])", " ", md)
    md = re.sub(r"\n  +(?=\S)", " ", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def seccion(md, titulo):
    m = re.search(rf"^## {re.escape(titulo)}\s*\n(.*?)(?=^## |\Z)", md, flags=re.S | re.M)
    return f"## {titulo}\n\n{m.group(1).strip()}" if m else ""


def de_informe(ruta):
    ruta = pathlib.Path(ruta)
    texto = ruta.read_text(encoding="utf-8")
    if ruta.suffix == ".json":   # reporte semanal
        d = json.loads(texto)
        resumen = d.get("resumen", "")
        if isinstance(resumen, list):
            resumen = "\n".join(f"- {x}" for x in resumen)
        partes = [f"GGAL · REPORTE SEMANAL · {d.get('semana', '')}", str(d.get("titular", "")), str(resumen),
                  f"La página sigue en la semana anterior hasta republicarla (/semanal en Claude Code):\n{PAGINA_SEMANAL}"]
        return "\n\n".join(p for p in partes if p.strip())
    cabeza = texto.split("\n## ", 1)[0]
    partes = [cabeza] + [seccion(texto, s) for s in SECCIONES]
    if not any(partes[1:]):      # auditoria u otro formato: lo que entre desde el principio
        partes = [texto]
    return plano("\n\n".join(p for p in partes if p))


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--informe")
    a.add_argument("--texto")
    a.add_argument("--chat-id", action="store_true")
    arg = a.parse_args()
    token, chat = credenciales()

    if arg.chat_id:
        if not token:
            sys.exit("Falta TELEGRAM_BOT_TOKEN en el .env de la raíz del repo.")
        r = llamar(token, "getUpdates")
        chats = {(u["message"]["chat"]["id"], u["message"]["chat"].get("first_name") or u["message"]["chat"].get("title"))
                 for u in r.get("result", []) if "message" in u}
        if not chats:
            sys.exit(f"Sin mensajes: escribile algo al bot desde Telegram y volvé a correr esto. ({r.get('description', 'ok')})")
        for i, nombre in chats:
            print(f"TELEGRAM_CHAT_ID={i}   ({nombre})")
        return

    if not token or not chat:
        print("telegram: sin credenciales (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID), no se avisa")
        sys.exit(2)
    mensaje = arg.texto or de_informe(arg.informe)
    if len(mensaje) > TOPE:
        mensaje = mensaje[:TOPE].rsplit("\n", 1)[0] + "\n\n[sigue en el informe]"
    r = llamar(token, "sendMessage", chat_id=chat, text=mensaje, disable_web_page_preview="true")
    if not r.get("ok"):
        print(f"telegram: rechazado ({r.get('description')})")
        sys.exit(1)
    print(f"telegram: enviado ({len(mensaje)} caracteres)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as e:   # sin red, archivo que no esta, JSON roto
        print(f"telegram: no se pudo avisar ({type(e).__name__}: {e})")
        sys.exit(1)
