from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from app.db.supabase import supabase
from app.core.exceptions import ThresholdNotFoundException


class ThresholdService:
    """Threshold management service"""

    async def get_thresholds(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get threshold configuration for a device"""
        result = supabase.table("alert_thresholds") \
            .select("*") \
            .eq("device_id", device_id) \
            .execute()

        if not result.data:
            raise ThresholdNotFoundException(device_id)

        return result.data[0]

    async def update_thresholds(
        self,
        device_id: str,
        over_voltage: Optional[float] = None,
        under_voltage: Optional[float] = None,
        over_current: Optional[float] = None,
        over_temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update threshold configuration for a device"""
        update_data = {
            "device_id": device_id,
            "updated_at": datetime.utcnow().isoformat()
        }

        if over_voltage is not None:
            update_data["over_voltage"] = over_voltage
        if under_voltage is not None:
            update_data["under_voltage"] = under_voltage
        if over_current is not None:
            update_data["over_current"] = over_current
        if over_temperature is not None:
            update_data["over_temperature"] = over_temperature

        # Check if thresholds exist
        existing = supabase.table("alert_thresholds") \
            .select("id") \
            .eq("device_id", device_id) \
            .execute()

        if existing.data:
            # Update existing
            result = supabase.table("alert_thresholds") \
                .update(update_data) \
                .eq("device_id", device_id) \
                .execute()
        else:
            # Insert new
            result = supabase.table("alert_thresholds") \
                .insert(update_data) \
                .execute()

        logger.info(f"Thresholds updated for device {device_id}")
        return result.data[0] if result.data else update_data

    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all threshold templates"""
        result = supabase.table("threshold_templates") \
            .select("*") \
            .order("is_default", desc=True) \
            .execute()

        return result.data if hasattr(result, 'data') else []

    async def create_template(
        self,
        name: str,
        description: Optional[str] = None,
        over_voltage: Optional[float] = None,
        under_voltage: Optional[float] = None,
        over_current: Optional[float] = None,
        over_temperature: Optional[float] = None,
        is_default: bool = False
    ) -> Dict[str, Any]:
        """Create a new threshold template"""
        # If this is default, unset other defaults
        if is_default:
            supabase.table("threshold_templates") \
                .update({"is_default": False}) \
                .execute()

        result = supabase.table("threshold_templates") \
            .insert({
                "name": name,
                "description": description,
                "over_voltage": over_voltage,
                "under_voltage": under_voltage,
                "over_current": over_current,
                "over_temperature": over_temperature,
                "is_default": is_default,
                "created_at": datetime.utcnow().isoformat()
            }) \
            .execute()

        logger.info(f"Threshold template created: {name}")
        return result.data[0] if result.data else {}

    async def apply_template_to_device(
        self,
        template_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Apply a threshold template to a device"""
        # Get template
        template_result = supabase.table("threshold_templates") \
            .select("*") \
            .eq("id", template_id) \
            .execute()

        if not template_result.data:
            raise ValueError(f"Template {template_id} not found")

        template = template_result.data[0]

        # Apply to device
        return await self.update_thresholds(
            device_id=device_id,
            over_voltage=template.get("over_voltage"),
            under_voltage=template.get("under_voltage"),
            over_current=template.get("over_current"),
            over_temperature=template.get("over_temperature")
        )


threshold_service = ThresholdService()
