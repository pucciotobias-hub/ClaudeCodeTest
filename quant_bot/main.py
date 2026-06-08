"""
main.py
=======
Orquestador del Superbot de Equity Research.

Ejecuta el pipeline completo:
    1. data_fetcher.collect_universe()   -> fundamentals + sentimiento
    2. quant_models.run_models()         -> filtros, DCF, scoring
    3. pdf_generator.generate_pdf()      -> reporte institucional
    4. telegram_notifier.send_report()   -> entrega

Modos de uso:
    python main.py --once       # corre el pipeline una vez (test) y sale
    python main.py              # arranca el daemon: viernes 18:00 hs

Logging a nivel INFO/ERROR en bot_activity.log para auditar el funcionamiento.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Carga de .env (si python-dotenv esta instalado)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

import data_fetcher
import pdf_generator
import quant_models
import telegram_notifier

LOG_FILE = os.path.join(os.path.dirname(__file__), "bot_activity.log")
RUN_DAY = "friday"
RUN_TIME = "18:00"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logging() -> logging.Logger:
    """Configura logging dual (archivo rotativo + consola) a nivel INFO/ERROR."""
    logger = logging.getLogger("quant_bot")
    logger.setLevel(logging.INFO)
    if logger.handlers:  # evita duplicar handlers en re-imports
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console)
    return logger


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_pipeline() -> None:
    """Ejecuta el flujo completo, capturando cualquier error de punta a punta."""
    log = logging.getLogger("quant_bot")
    started = datetime.now()
    log.info("=" * 60)
    log.info("INICIO del pipeline de research: %s", started.isoformat())

    try:
        # 1. Datos
        records = data_fetcher.collect_universe()
        if not records:
            log.error("No se obtuvieron datos del universo. Abortando ciclo.")
            telegram_notifier.send_message(
                "Quant Bot: el ciclo de hoy no obtuvo datos del mercado (rate-limit?)."
            )
            return

        # 2. Modelos
        analyzed = quant_models.run_models(records)

        # 3. PDF
        report_path = pdf_generator.generate_pdf(analyzed)

        # 4. Telegram
        top = analyzed[0] if analyzed else None
        caption = "Reporte semanal Quant Equity Research"
        if top:
            caption += (
                f"\nTop pick: {top.get('ticker')} "
                f"(score {top.get('score')})"
            )
        sent_ok = telegram_notifier.send_report(report_path, caption=caption)
        if not sent_ok:
            log.error("El reporte se genero pero no se pudo enviar por Telegram.")

        elapsed = (datetime.now() - started).total_seconds()
        log.info("FIN del pipeline OK en %.1fs. Reporte: %s", elapsed, report_path)

    except Exception as exc:  # red de seguridad: el daemon nunca debe morir
        log.exception("ERROR FATAL no controlado en el pipeline: %s", exc)
        try:
            telegram_notifier.send_message(f"Quant Bot: error fatal en el ciclo: {exc}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Scheduler (daemon)
# ---------------------------------------------------------------------------
def run_daemon() -> None:
    """Programa el pipeline para los viernes a las 18:00 y queda en loop."""
    import schedule

    log = logging.getLogger("quant_bot")
    getattr(schedule.every(), RUN_DAY).at(RUN_TIME).do(run_pipeline)
    log.info("Daemon iniciado. Proxima ejecucion: %s a las %s.", RUN_DAY, RUN_TIME)
    log.info("Dejar este proceso corriendo. Ctrl+C para detener.")

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            log.info("Daemon detenido manualmente.")
            break
        except Exception as exc:
            log.exception("Error en el loop del scheduler: %s", exc)
            time.sleep(60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Superbot de Equity Research")
    parser.add_argument(
        "--once", action="store_true",
        help="Corre el pipeline una sola vez (modo prueba) y sale.",
    )
    args = parser.parse_args()

    setup_logging()
    if args.once:
        run_pipeline()
    else:
        run_daemon()


if __name__ == "__main__":
    main()
