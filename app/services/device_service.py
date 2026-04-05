from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from app.db.supabase import supabase
from app.core.exceptions import DeviceNotFoundException, DeviceAlreadyBoundException


class DeviceService:
    """Device management service"""

    async def get_devices(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get device list with pagination and filtering"""
        query = supabase.table("devices")

        # Apply filters
        if user_id:
            query = query.eq("user_id", user_id)
        if status:
            query = query.eq("status", status)

        # Get total count
        count_result = query.select("*", count="exact").execute()
        total = count_result.count

        # Apply pagination and sorting
        result = query.select("*").order(sort_by, desc=(sort_order.lower() == "desc")).range(
            (page - 1) * page_size,
            page * page_size - 1
        ).execute()

        devices = result.data if hasattr(result, 'data') else []

        return {
            "devices": devices,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_device_by_id(self, device_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get device details by ID"""
        query = supabase.table("devices").select("*").eq("id", device_id)

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()

        if not result.data:
            raise DeviceNotFoundException(device_id)

        device = result.data[0]

        # Get latest telemetry
        telemetry_result = supabase.table("telemetry") \
            .select("*") \
            .eq("device_id", device_id) \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()

        telemetry = telemetry_result.data[0] if telemetry_result.data else None

        # Get alert stats
        alert_result = supabase.table("alerts") \
            .select("level, is_read") \
            .eq("device_id", device_id) \
            .execute()

        alert_stats = {"total": 0, "unread": 0, "by_level": {}}
        if alert_result.data:
            alert_stats["total"] = len(alert_result.data)
            alert_stats["unread"] = sum(1 for a in alert_result.data if not a.get("is_read"))
            for alert in alert_result.data:
                level = alert.get("level", "unknown")
                if level not in alert_stats["by_level"]:
                    alert_stats["by_level"][level] = 0
                alert_stats["by_level"][level] += 1

        return {
            "device": device,
            "telemetry": telemetry,
            "alert_stats": alert_stats
        }

    async def get_device_by_serial(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """Get device by serial number"""
        result = supabase.table("devices") \
            .select("*") \
            .eq("serial_number", serial_number) \
            .execute()

        return result.data[0] if result.data else None

    async def bind_device(self, serial_number: str, user_id: str) -> Dict[str, Any]:
        """Bind a device to a user"""
        # Check if device exists
        device = await self.get_device_by_serial(serial_number)

        if not device:
            # Create new device
            result = supabase.table("devices") \
                .insert({
                    "serial_number": serial_number,
                    "user_id": user_id,
                    "status": "inactive"
                }) \
                .execute()
            device = result.data[0]
        elif device.get("user_id"):
            raise DeviceAlreadyBoundException(device["id"])
        else:
            # Update existing device
            result = supabase.table("devices") \
                .update({"user_id": user_id, "status": "inactive"}) \
                .eq("id", device["id"]) \
                .execute()
            device = result.data[0]

        return device

    async def update_device_status(self, device_id: str, status: str) -> Dict[str, Any]:
        """Update device status"""
        result = supabase.table("devices") \
            .update({"status": status, "updated_at": datetime.utcnow().isoformat()}) \
            .eq("id", device_id) \
            .execute()

        if not result.data:
            raise DeviceNotFoundException(device_id)

        return result.data[0]

    async def mark_device_offline(self, device_id: str) -> Dict[str, Any]:
        """Mark device as offline and record offline event"""
        # Update device status
        await self.update_device_status(device_id, "offline")

        # Record offline event
        supabase.table("offline_events") \
            .insert({
                "device_id": device_id,
                "offline_at": datetime.utcnow().isoformat()
            }) \
            .execute()

        logger.info(f"Device {device_id} marked as offline")

        return {"device_id": device_id, "status": "offline"}


device_service = DeviceService()
