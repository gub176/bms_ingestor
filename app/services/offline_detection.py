from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from loguru import logger
from app.db.supabase import supabase
from app.services.device_service import device_service


class OfflineDetectionService:
    """Device offline detection service"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def detect_offline_devices(self):
        """Detect devices that haven't reported in 15 minutes"""
        logger.info("Running offline device detection...")

        # Get threshold time (15 minutes ago)
        threshold_time = datetime.utcnow() - timedelta(minutes=15)

        # Get all online devices
        result = supabase.table("devices") \
            .select("id, serial_number, last_seen, status") \
            .eq("status", "online") \
            .execute()

        online_devices = result.data if hasattr(result, 'data') else []
        offline_count = 0

        for device in online_devices:
            last_seen_str = device.get("last_seen")
            if not last_seen_str:
                continue

            # Parse last_seen timestamp
            try:
                if isinstance(last_seen_str, str):
                    last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00').replace('+00:00', ''))
                else:
                    last_seen = last_seen_str
            except (ValueError, TypeError):
                logger.warning(f"Invalid last_seen timestamp for device {device['id']}")
                continue

            # Check if device is offline
            if last_seen < threshold_time:
                await device_service.mark_device_offline(device["id"])
                offline_count += 1
                logger.info(f"Device {device['id']} marked as offline (last seen: {last_seen})")

        logger.info(f"Offline detection completed. {offline_count} devices marked as offline.")

    def start(self):
        """Start the offline detection scheduler"""
        # Run every 5 minutes
        self.scheduler.add_job(
            self.detect_offline_devices,
            trigger=CronTrigger.from_crontab("*/5 * * * *"),
            id="offline_detection",
            name="Detect offline devices",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Offline detection scheduler started (runs every 5 minutes)")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()


# Global scheduler instance
offline_detection_service = OfflineDetectionService()
