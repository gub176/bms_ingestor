from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from app.db.supabase import supabase
from app.services.alert_service import alert_service


class AlertJudgmentService:
    """Alert judgment service - determines if telemetry values trigger alerts"""

    async def get_device_thresholds(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get threshold configuration for a device"""
        result = supabase.table("device_thresholds") \
            .select("*") \
            .eq("device_id", device_id) \
            .execute()

        return result.data[0] if result.data else None

    async def check_telemetry_and_alert(
        self,
        device_id: str,
        telemetry_data: Dict[str, Any]
    ) -> list:
        """Check telemetry data against thresholds and create alerts if needed"""
        alerts_created = []

        # Get device thresholds
        thresholds = await self.get_device_thresholds(device_id)

        if not thresholds:
            logger.debug(f"No thresholds configured for device {device_id}")
            return alerts_created

        # Check each telemetry value against thresholds
        alert_checks = [
            ("voltage", thresholds.get("over_voltage"), thresholds.get("under_voltage"), "电压"),
            ("current", thresholds.get("over_current"), None, "电流"),
            ("temperature", thresholds.get("over_temperature"), None, "温度"),
        ]

        for field, over_threshold, under_threshold, field_name in alert_checks:
            value = telemetry_data.get(field)
            if value is None:
                continue

            # Check over threshold
            if over_threshold is not None and float(value) > float(over_threshold):
                alert = await alert_service.create_alert(
                    device_id=device_id,
                    level="critical",
                    alert_type=f"over_{field}",
                    message=f"设备{field_name}过高：{value}V (阈值：{over_threshold}V)"
                )
                alerts_created.append(alert)
                logger.warning(f"Over {field} alert for device {device_id}: {value} > {over_threshold}")

            # Check under threshold
            if under_threshold is not None and float(value) < float(under_threshold):
                alert = await alert_service.create_alert(
                    device_id=device_id,
                    level="critical",
                    alert_type=f"under_{field}",
                    message=f"设备{field_name}过低：{value}V (阈值：{under_threshold}V)"
                )
                alerts_created.append(alert)
                logger.warning(f"Under {field} alert for device {device_id}: {value} < {under_threshold}")

        return alerts_created


alert_judgment_service = AlertJudgmentService()
