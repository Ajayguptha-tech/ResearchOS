"""Standalone Background Reminder Worker for Production / Render.

Runs independently of the web server process to guarantee timely reminder
detection and email dispatch even when the web tier is scaling, recycling,
or separated from background jobs.

Usage:
    python -m app.worker
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Ensure backend root is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.reminder_agent import process_due_reminders, recover_stale_reminders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("researchos.worker")

CHECK_INTERVAL_SECONDS = 5.0


async def run_worker() -> None:
    logger.info(
        "[Worker] ResearchOS Reminder Worker starting (Environment: %s, Email Provider: %s, Interval: %gs)",
        settings.environment,
        settings.email_provider,
        CHECK_INTERVAL_SECONDS,
    )

    # Recover any reminders left in 'processing' by a previous crash/restart
    try:
        with SessionLocal() as db:
            recovered = recover_stale_reminders(db)
            if recovered:
                logger.info("[Worker] Recovered %d interrupted reminder(s) to 'pending'", recovered)
    except Exception as exc:
        logger.error("[Worker] Initial recovery error: %s", exc)

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is not None:
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                # Windows event loop doesn't support add_signal_handler
                pass

    logger.info("[Worker] Reminder processing loop running...")
    while not stop_event.is_set():
        try:
            with SessionLocal() as db:
                processed = process_due_reminders(db)
                if processed > 0:
                    logger.info("[Worker] Processed and dispatched %d due reminder(s)", processed)
        except Exception as exc:
            logger.error("[Worker] Error processing due reminders: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass

    logger.info("[Worker] Reminder Worker stopped gracefully.")


def main() -> None:
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        logger.info("[Worker] Shutdown requested. Exiting.")


if __name__ == "__main__":
    main()
