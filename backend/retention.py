import asyncio
import logging
import os
import time

import database

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 3600  # run every hour


async def run_retention_loop() -> None:
    days = int(os.environ.get("LOG_RETENTION_DAYS", "30"))
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            deleted = database.delete_old_logs(days)
            if deleted:
                logger.info("Retention: deleted %d log rows older than %d days", deleted, days)
        except Exception as e:
            logger.error("Retention error: %s", e)
        try:
            purged = database.purge_deleted_containers(time.time() - 7 * 86400)
            if purged:
                logger.info("Retention: purged %d soft-deleted container groups", purged)
        except Exception as e:
            logger.error("Retention purge error: %s", e)
