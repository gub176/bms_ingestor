from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from app.db.supabase import supabase
from app.core.exceptions import AlertNotFoundException


class AlertService:
    """Alert management service"""

    async def get_alerts(
        self,
        device_id: Optional[str] = None,
        severity: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get alert list with filtering and pagination"""
        # First get the total count with filters applied (no pagination)
        count_query = supabase.table("alerts").select("*", count="exact")

        if device_id:
            count_query = count_query.eq("device_id", device_id)
        if severity is not None:
            count_query = count_query.eq("severity", severity)
        if start_date:
            count_query = count_query.gte("start_time", start_date)
        if end_date:
            count_query = count_query.lte("start_time", end_date)

        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') and count_result.count is not None else 0

        # Then get the paginated data
        data_query = supabase.table("alerts").select("*")

        if device_id:
            data_query = data_query.eq("device_id", device_id)
        if severity is not None:
            data_query = data_query.eq("severity", severity)
        if start_date:
            data_query = data_query.gte("start_time", start_date)
        if end_date:
            data_query = data_query.lte("start_time", end_date)

        result = data_query.range(
            (page - 1) * page_size,
            page * page_size - 1
        ).execute()

        alerts = result.data if hasattr(result, 'data') else []

        # Filter by keyword in memory
        if keyword:
            keyword_lower = keyword.lower()
            alerts = [
                a for a in alerts
                if keyword_lower in a.get("alert_type", "").lower()
            ]

        return {
            "alerts": alerts,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_alert_by_id(self, alert_id: int) -> Dict[str, Any]:
        """Get alert by ID"""
        result = supabase.table("alerts") \
            .select("*") \
            .eq("id", alert_id) \
            .execute()

        if not result.data:
            raise AlertNotFoundException(alert_id)

        return result.data[0]

    async def close_alert(self, alert_id: int) -> Dict[str, Any]:
        """Close an alert by setting end_time"""
        alert = await self.get_alert_by_id(alert_id)

        result = supabase.table("alerts") \
            .update({"end_time": datetime.utcnow().isoformat()}) \
            .eq("id", alert_id) \
            .execute()

        return result.data[0] if result.data else alert

    async def bulk_close_alerts(
        self,
        alert_ids: List[int],
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bulk close alerts"""
        query = supabase.table("alerts") \
            .update({"end_time": datetime.utcnow().isoformat()}) \
            .in_("id", alert_ids)

        if device_id:
            query = query.eq("device_id", device_id)

        result = query.execute()

        return {"updated_count": len(alert_ids)}

    async def get_alert_stats(
        self,
        device_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get alert statistics"""
        # Get count for total
        count_query = supabase.table("alerts").select("id", count="exact")

        if device_id:
            count_query = count_query.eq("device_id", device_id)
        if start_date:
            count_query = count_query.gte("start_time", start_date)
        if end_date:
            count_query = count_query.lte("start_time", end_date)

        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') and count_result.count is not None else 0

        # Get data for grouping (with limit to avoid memory issues)
        data_query = supabase.table("alerts").select("severity, alert_type, device_id")

        if device_id:
            data_query = data_query.eq("device_id", device_id)
        if start_date:
            data_query = data_query.gte("start_time", start_date)
        if end_date:
            data_query = data_query.lte("start_time", end_date)

        result = data_query.limit(10000).execute()
        alerts = result.data if hasattr(result, 'data') else []

        stats = {
            "total": total,
            "by_severity": {},
            "by_device": {},
            "by_type": {}
        }

        for alert in alerts:
            # Count by severity
            severity = str(alert.get("severity", "unknown"))
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # Count by device
            dev_id = alert.get("device_id", "unknown")
            stats["by_device"][dev_id] = stats["by_device"].get(dev_id, 0) + 1

            # Count by type
            alert_type = alert.get("alert_type", "unknown")
            stats["by_type"][alert_type] = stats["by_type"].get(alert_type, 0) + 1

        return stats

    async def create_alert(
        self,
        device_id: str,
        level: str,
        alert_type: str,
        message: str
    ) -> Dict[str, Any]:
        """Create a new alert"""
        result = supabase.table("alerts") \
            .insert({
                "device_id": device_id,
                "level": level,
                "type": alert_type,
                "message": message,
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }) \
            .execute()

        logger.info(f"Alert created for device {device_id}: {alert_type} - {message}")
        return result.data[0] if result.data else {}


alert_service = AlertService()
