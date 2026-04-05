"""Bitmap-based alert detector with deduplication"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any
from loguru import logger
from app.models.schemas import Alert
from app.db.supabase import get_supabase


class AlertDetector:
    """
    Alert detector with bitmap-based state tracking.

    Supports:
    - Signal 01003001 (warning) - 10 bits
    - Signal 01002001 (fault) - 12 bits
    """

    # Default signal map
    SIGNAL_MAP = {
        "01003001": {
            "type": "warning",
            "severity": 2,
            "bit_map": {
                "0": "cell_voltage_low_warning",
                "1": "cell_voltage_high_warning",
                "2": "cell_low_temperature_warning",
                "3": "cell_high_temperature_warning",
                "4": "total_voltage_high_warning",
                "5": "total_voltage_low_warning",
                "6": "cell_voltage_diff_warning",
                "7": "mos_high_temperature_warning",
                "8": "ambient_low_temperature_warning",
                "9": "ambient_high_temperature_warning",
            }
        },
        "01002001": {
            "type": "fault",
            "severity": 1,
            "bit_map": {
                "0": "short_circuit",
                "1": "undervoltage",
                "2": "overvoltage",
                "3": "discharge_overcurrent",
                "4": "charge_overcurrent",
                "5": "low_temperature",
                "6": "over_temperature",
                "7": "status_abnormal",
                "8": "mos_abnormal",
                "9": "total_voltage_overvoltage",
                "10": "total_voltage_undervoltage",
                "11": "cell_voltage_diff",
            }
        }
    }

    def __init__(self, signal_map: Dict[str, Any] = None):
        self.signal_map = signal_map or self.SIGNAL_MAP
        self.last_state: Dict[str, Dict[str, int]] = defaultdict(dict)
        self._active_alerts: Set[Tuple[str, str]] = set()
        self._lock = asyncio.Lock()
        logger.debug("AlertDetector initialized")

    async def load_active_alerts(self) -> int:
        """Load active alerts from database on startup"""
        try:
            supabase = get_supabase()
            result = supabase.table("alerts") \
                .select("device_id", "alert_type") \
                .is_("end_time", None) \
                .execute()

            async with self._lock:
                for record in result.data:
                    self._active_alerts.add((record["device_id"], record["alert_type"]))

            count = len(result.data)
            logger.info(f"Loaded {count} active alerts from database")
            return count
        except Exception as e:
            logger.error(f"Error loading active alerts: {e}")
            return 0

    async def is_active(self, device_id: str, alert_type: str) -> bool:
        """Check if alert is currently active"""
        async with self._lock:
            return (device_id, alert_type) in self._active_alerts

    async def mark_active(self, device_id: str, alert_type: str) -> None:
        """Mark alert as active"""
        async with self._lock:
            self._active_alerts.add((device_id, alert_type))

    async def mark_inactive(self, device_id: str, alert_type: str) -> None:
        """Mark alert as inactive"""
        async with self._lock:
            self._active_alerts.discard((device_id, alert_type))

    async def get_active_alerts_count(self) -> int:
        """Get count of active alerts"""
        async with self._lock:
            return len(self._active_alerts)

    async def process(
        self,
        device_id: str,
        timestamp: datetime,
        status_data: Dict[str, int],
    ) -> Tuple[List[Alert], List[Dict[str, str]]]:
        """
        Process status data and detect alert changes.

        Args:
            device_id: Device ID
            timestamp: Timestamp of status data
            status_data: Status signal data (e.g., {"01002001": 2})

        Returns:
            (alerts_to_insert, alerts_to_update)
        """
        alerts_insert: List[Alert] = []
        alerts_update: List[Dict[str, str]] = []

        for signal_id, current_val in status_data.items():
            if signal_id not in self.signal_map:
                continue

            # Get previous state
            async with self._lock:
                prev_val = self.last_state[device_id].get(signal_id, 0)

            if prev_val == current_val:
                continue

            # Find changed bits
            changed_bits = prev_val ^ current_val
            alert_def = self.signal_map[signal_id]

            for bit_pos_str, bit_name in alert_def.get("bit_map", {}).items():
                bit_pos = int(bit_pos_str)
                bit_mask = 1 << bit_pos

                if changed_bits & bit_mask:
                    bit_prev = (prev_val >> bit_pos) & 1
                    bit_curr = (current_val >> bit_pos) & 1

                    if bit_prev == 0 and bit_curr == 1:
                        # Alert triggered
                        if await self.is_active(device_id, bit_name):
                            logger.debug(f"Alert {bit_name} already active for {device_id}, skipping")
                            continue

                        alert = Alert(
                            device_id=device_id,
                            alert_type=bit_name,
                            severity=alert_def["severity"],
                            start_time=timestamp.isoformat() + "Z",
                            end_time=None,
                        )
                        alerts_insert.append(alert)
                        await self.mark_active(device_id, bit_name)
                        logger.debug(f"Alert triggered: {bit_name} for {device_id}")

                    elif bit_prev == 1 and bit_curr == 0:
                        # Alert recovered
                        alerts_update.append({
                            "device_id": device_id,
                            "alert_type": bit_name,
                            "end_time": timestamp.isoformat() + "Z",
                        })
                        await self.mark_inactive(device_id, bit_name)
                        logger.debug(f"Alert recovered: {bit_name} for {device_id}")

            # Update last state
            async with self._lock:
                self.last_state[device_id][signal_id] = current_val

        return alerts_insert, alerts_update


# Global instance
alert_detector = AlertDetector()
