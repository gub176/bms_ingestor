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
            .select("device_id, last_online, last_offline, status") \
            .eq("status", "online") \
            .execute()

        online_devices = result.data if hasattr(result, 'data') else []
        offline_count = 0

        for device in online_devices:
            last_online_str = device.get("last_online")
            if not last_online_str:
                continue

            # Parse last_online timestamp
            try:
                if isinstance(last_online_str, str):
                    last_online = datetime.fromisoformat(last_online_str.replace('Z', '+00:00').replace('+00:00', ''))
                else:
                    last_online = last_online_str
            except (ValueError, TypeError):
                logger.warning(f"Invalid last_online timestamp for device {device['device_id']}")
                continue

            # Check if device is offline
            if last_online < threshold_time:
                await device_service.mark_device_offline(device["device_id"])
                offline_count += 1
                logger.info(f"Device {device['device_id']} marked as offline (last seen: {last_online})")

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
