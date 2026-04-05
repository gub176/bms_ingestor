from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from app.db.supabase import supabase
from app.core.exceptions import OtaUpgradeNotFoundException, InvalidTransitionException
from app.schemas.ota import OTAStatus, VALID_TRANSITIONS


class OtaService:
    """OTA management service"""

    async def create_upgrade(
        self,
        device_id: str,
        firmware_version: str,
        firmware_url: str
    ) -> Dict[str, Any]:
        """Create a new OTA upgrade task"""
        upgrade_data = {
            "device_id": device_id,
            "firmware_version": firmware_version,
            "firmware_url": firmware_url,
            "status": OTAStatus.PENDING.value,
            "progress": 0,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("ota_upgrades") \
            .insert(upgrade_data) \
            .execute()

        logger.info(f"OTA upgrade created for device {device_id}: {firmware_version}")
        return result.data[0] if result.data else upgrade_data

    async def get_upgrade_by_id(self, upgrade_id: str) -> Dict[str, Any]:
        """Get OTA upgrade by ID"""
        result = supabase.table("ota_upgrades") \
            .select("*") \
            .eq("id", upgrade_id) \
            .execute()

        if not result.data:
            raise OtaUpgradeNotFoundException(upgrade_id)

        return result.data[0]

    async def get_upgrades(
        self,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get OTA upgrade list with pagination"""
        query = supabase.table("ota_upgrades").select("*", count="exact")

        if device_id:
            query = query.eq("device_id", device_id)
        if status:
            query = query.eq("status", status)

        result = query.execute()
        upgrades = result.data if hasattr(result, 'data') else []
        total = result.count if hasattr(result, 'count') else len(upgrades)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_upgrades = upgrades[start_idx:end_idx]

        return {
            "upgrades": paginated_upgrades,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def update_progress(
        self,
        upgrade_id: str,
        status: str,
        progress: int,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update OTA upgrade progress"""
        upgrade = await self.get_upgrade_by_id(upgrade_id)

        # Validate state transition
        current_status = OTAStatus(upgrade["status"])
        new_status = OTAStatus(status)

        if new_status not in VALID_TRANSITIONS.get(current_status, []):
            raise InvalidTransitionException(current_status.value, new_status.value)

        update_data = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat()
        }

        if message:
            update_data["error_message"] = message

        if new_status in [OTAStatus.SUCCESS, OTAStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow().isoformat()
        elif not upgrade.get("started_at"):
            update_data["started_at"] = datetime.utcnow().isoformat()

        result = supabase.table("ota_upgrades") \
            .update(update_data) \
            .eq("id", upgrade_id) \
            .execute()

        logger.info(f"OTA upgrade {upgrade_id} progress updated: {status} ({progress}%)")
        return result.data[0] if result.data else update_data

    async def mark_upgrade_failed(
        self,
        upgrade_id: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Mark an OTA upgrade as failed"""
        update_data = {
            "status": OTAStatus.FAILED.value,
            "error_message": error_message,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("ota_upgrades") \
            .update(update_data) \
            .eq("id", upgrade_id) \
            .execute()

        logger.error(f"OTA upgrade {upgrade_id} failed: {error_message}")
        return result.data[0] if result.data else update_data

    async def retry_upgrade(self, upgrade_id: str) -> Dict[str, Any]:
        """Retry a failed or timed out upgrade"""
        upgrade = await self.get_upgrade_by_id(upgrade_id)

        if upgrade["status"] not in [OTAStatus.FAILED.value, OTAStatus.TIMEOUT.value]:
            raise ValueError(f"Cannot retry upgrade in {upgrade['status']} status")

        retry_count = upgrade.get("retry_count", 0)
        if retry_count >= upgrade.get("max_retries", 3):
            raise ValueError(f"Max retries exceeded for upgrade {upgrade_id}")

        update_data = {
            "status": OTAStatus.PENDING.value,
            "progress": 0,
            "retry_count": retry_count + 1,
            "error_message": None,
            "completed_at": None,
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("ota_upgrades") \
            .update(update_data) \
            .eq("id", upgrade_id) \
            .execute()

        logger.info(f"OTA upgrade {upgrade_id} retried (attempt {retry_count + 1})")
        return result.data[0] if result.data else update_data

    async def get_stuck_upgrades(self) -> List[Dict[str, Any]]:
        """Get upgrades that are stuck (no update in 10 minutes)"""
        threshold_time = datetime.utcnow() - timedelta(minutes=10)

        result = supabase.table("ota_upgrades") \
            .select("*") \
            .in_("status", [
                OTAStatus.PENDING.value,
                OTAStatus.DOWNLOADING.value,
                OTAStatus.INSTALLING.value
            ]) \
            .lt("updated_at", threshold_time.isoformat()) \
            .execute()

        return result.data if hasattr(result, 'data') else []


ota_service = OtaService()
