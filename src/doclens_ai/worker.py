from __future__ import annotations

import asyncio
import logging
import signal
from datetime import timedelta

from doclens_ai.core.config import Settings
from doclens_ai.db.session import Database
from doclens_ai.services.ingestion import IngestionService
from doclens_ai.services.processing import ProcessingCoordinator, ProcessingPolicy
from doclens_ai.services.worker import IngestionWorker, WorkerSettings
from doclens_ai.storage.config import StorageSettings
from doclens_ai.storage.s3 import S3ObjectStorage


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level)
    # SDK/parser debug and warning records can contain object keys or document bytes.
    # This dedicated process exposes only our fixed operational event codes.
    for handler in logging.getLogger().handlers:
        handler.addFilter(lambda record: record.name in {__name__, "doclens_ai.services.worker"})


async def main() -> None:
    settings = Settings()
    worker_settings = WorkerSettings()
    _configure_logging(settings.log_level)
    database = Database(settings.database_url)
    storage = S3ObjectStorage(StorageSettings())
    worker = IngestionWorker(
        ProcessingCoordinator(
            database.session_factory,
            policy=ProcessingPolicy(
                lease_duration=timedelta(seconds=worker_settings.lease_seconds)
            ),
        ),
        IngestionService(database.session_factory, storage),
        settings=worker_settings,
    )
    previous_handlers = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.signal(signum, lambda *_: worker.request_stop())
    try:
        await worker.run()
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        await database.dispose()
        await asyncio.to_thread(storage._client.close)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        # Settings validation and connection exceptions may include credentials. No traceback.
        logging.getLogger(__name__).error("worker_startup_failed")
        raise SystemExit(1) from None
