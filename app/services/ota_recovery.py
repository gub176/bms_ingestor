from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from app.services.ota_service import ota_service
from app.schemas.ota import OTAStatus


class OtaRecoveryService:
    """OTA failure recovery service"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def check_and_recovery(self):
        """Check for stuck upgrades and attempt recovery"""
        logger.info("Running OTA recovery check...")

        # Get stuck upgrades
        stuck_upgrades = await ota_service.get_stuck_upgrades()

        for upgrade in stuck_upgrades:
            upgrade_id = upgrade["id"]
            retry_count = upgrade.get("retry_count", 0)
            max_retries = upgrade.get("max_retries", 3)

            if retry_count < max_retries:
                # Retry the upgrade
                try:
                    await ota_service.retry_upgrade(upgrade_id)
                    logger.info(f"OTA upgrade {upgrade_id} retried (attempt {retry_count + 1}/{max_retries})")
                except Exception as e:
                    logger.error(f"Failed to retry OTA upgrade {upgrade_id}: {e}")
            else:
                # Mark as failed
                await ota_service.mark_upgrade_failed(
                    upgrade_id,
                    f"Max retries ({max_retries}) exceeded"
                )
                logger.error(f"OTA upgrade {upgrade_id} marked as failed after {max_retries} retries")

        logger.info(f"OTA recovery check completed. Processed {len(stuck_upgrades)} stuck upgrades.")

    def start(self):
        """Start the OTA recovery scheduler"""
        # Run every 10 minutes
        self.scheduler.add_job(
            self.check_and_recovery,
            trigger=CronTrigger.from_crontab("*/10 * * * *"),
            id="ota_recovery",
            name="Check and recover stuck OTA upgrades",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("OTA recovery scheduler started (runs every 10 minutes)")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()


# Global recovery service instance
ota_recovery_service = OtaRecoveryService()
