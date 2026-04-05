"""Batch processing worker for efficient Supabase writes"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List
from loguru import logger
import httpx
from app.core.config import settings
from app.db.supabase import get_supabase


class MetricsCollector:
    """Async-safe metrics collector"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._stats: Dict[str, Any] = {
            "messages_received_total": 0,
            "messages_processed_total": 0,
            "messages_dropped_total": 0,
            "telemetry_received": 0,
            "status_received": 0,
            "alerts_generated": 0,
            "alerts_updated": 0,
            "offline_events": 0,
            "device_online_events": 0,
            "device_offline_events": 0,
            "batch_flushes": 0,
            "supabase_errors": 0,
            "json_errors": 0,
            "queue_size": 0,
            "batch_telemetry": 0,
            "batch_status": 0,
            "batch_alerts": 0,
            "batch_offline_events": 0,
            "last_message_time": None,
        }
        self._recent_errors: list[Dict[str, Any]] = []
        self._max_errors = 50  # Keep last 50 errors

    async def inc(self, key: str, value: int = 1) -> None:
        """Increment metric"""
        async with self._lock:
            if key in self._stats:
                self._stats[key] += value
            else:
                self._stats[key] = value

    async def set(self, key: str, value: Any) -> None:
        """Set metric value"""
        async with self._lock:
            self._stats[key] = value

    async def get_stats(self) -> Dict[str, Any]:
        """Get all stats"""
        async with self._lock:
            return self._stats.copy()

    async def update(self, updates: Dict[str, Any]) -> None:
        """Bulk update metrics"""
        async with self._lock:
            for key, value in updates.items():
                if key in self._stats:
                    self._stats[key] = value

    async def add_error(self, error_type: str, message: str) -> None:
        """Add a recent error"""
        async with self._lock:
            error_entry = {
                "type": error_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self._recent_errors.append(error_entry)
            # Keep only the last N errors
            if len(self._recent_errors) > self._max_errors:
                self._recent_errors = self._recent_errors[-self._max_errors:]

    async def get_recent_errors(self) -> list[Dict[str, Any]]:
        """Get recent errors"""
        async with self._lock:
            return self._recent_errors.copy()


class BatchWorker:
    """Batch processor for MQTT messages"""

    def __init__(
        self,
        queue: asyncio.Queue,
        metrics: MetricsCollector,
        alert_detector=None,  # Will be added in Task 2
    ):
        self.queue = queue
        self.metrics = metrics
        self.alert_detector = alert_detector
        self._running = False

        # Batch configuration
        self.batch_size = getattr(settings, 'batch_size', 50)
        self.batch_timeout = getattr(settings, 'batch_timeout', 6)

    async def run(self, client: httpx.AsyncClient) -> None:
        """Run batch worker loop"""
        self._running = True
        logger.info("Batch worker started")

        telemetry_batch: List[Dict] = []
        status_batch: List[Dict] = []
        alert_insert_batch: List[Dict] = []
        alert_update_list: List[Dict] = []
        offline_event_batch: List[Dict] = []
        device_updates: Dict[str, Dict[str, Any]] = {}

        last_flush = asyncio.get_event_loop().time()

        while self._running:
            item = None
            try:
                item = await asyncio.wait_for(
                    self.queue.get(), timeout=self.batch_timeout
                )
            except asyncio.TimeoutError:
                pass

            if item:
                await self.metrics.inc("messages_processed_total")
                # Process item based on op_type
                op_type = item.get('op_type') if isinstance(item, dict) else getattr(item, 'op_type', None)
                data = item.get('data') if isinstance(item, dict) else getattr(item, 'data', None)

                if op_type == 'telemetry':
                    telemetry_batch.append(data)
                    await self.metrics.inc("telemetry_received")
                elif op_type == 'status':
                    status_batch.append(data)
                    await self.metrics.inc("status_received")
                elif op_type == 'offline_event':
                    offline_event_batch.append(data)
                    await self.metrics.inc("offline_events")
                elif op_type == 'device_offline':
                    # Update device status to offline
                    dev_id = data.get('device_id')
                    if dev_id:
                        device_updates[dev_id] = {
                            'last_offline': data.get('timestamp').isoformat().replace('+00:00', 'Z') if data.get('timestamp') else datetime.utcnow().isoformat() + 'Z',
                            'status': 'offline'
                        }
                        await self.metrics.inc("device_offline_events")
                        logger.debug(f"Device offline: {dev_id}")
                elif op_type == 'device_online':
                    # Update device status to online
                    dev_id = data.get('device_id')
                    if dev_id:
                        device_updates[dev_id] = {
                            'last_online': data.get('timestamp').isoformat().replace('+00:00', 'Z') if data.get('timestamp') else datetime.utcnow().isoformat() + 'Z',
                            'status': 'online'
                        }
                        await self.metrics.inc("device_online_events")
                        logger.debug(f"Device online: {dev_id}")
                elif op_type == 'alert':
                    alert_insert_batch.append(data)
                    await self.metrics.inc("alerts_generated")
                elif op_type == 'alert_update':
                    alert_update_list.append(data)
                    await self.metrics.inc("alerts_updated")

            # Check flush conditions
            now = asyncio.get_event_loop().time()
            should_flush = (
                (now - last_flush) >= self.batch_timeout or
                len(telemetry_batch) >= self.batch_size or
                len(status_batch) >= self.batch_size or
                len(offline_event_batch) >= self.batch_size or
                len(alert_insert_batch) >= self.batch_size or
                len(alert_update_list) >= self.batch_size or
                len(device_updates) >= 10
            )

            if should_flush and any([telemetry_batch, status_batch, offline_event_batch, alert_insert_batch, alert_update_list, device_updates]):
                await self._flush(client, telemetry_batch, status_batch, offline_event_batch, alert_insert_batch, alert_update_list, device_updates)
                telemetry_batch.clear()
                status_batch.clear()
                offline_event_batch.clear()
                alert_insert_batch.clear()
                alert_update_list.clear()
                device_updates.clear()
                last_flush = now
                await self.metrics.inc("batch_flushes")

            await self.metrics.set("queue_size", self.queue.qsize())

            if item is None and not any([telemetry_batch, status_batch, offline_event_batch, alert_insert_batch, alert_update_list, device_updates]):
                await asyncio.sleep(0.1)

    async def _flush(
        self,
        client: httpx.AsyncClient,
        telemetry_batch: List[Dict],
        status_batch: List[Dict],
        offline_event_batch: List[Dict],
        alert_insert_batch: List[Dict] = None,
        alert_update_list: List[Dict] = None,
        device_updates: Dict[str, Dict[str, Any]] = None,
    ) -> None:
        """Flush batches to Supabase"""
        supabase = get_supabase()

        if alert_insert_batch is None:
            alert_insert_batch = []
        if alert_update_list is None:
            alert_update_list = []
        if device_updates is None:
            device_updates = {}

        try:
            if telemetry_batch:
                result = supabase.table("telemetry").insert(telemetry_batch).execute()
                logger.debug(f"Inserted {len(telemetry_batch)} telemetry records")
                await self.metrics.inc("batch_telemetry", len(telemetry_batch))

            if status_batch:
                result = supabase.table("status").insert(status_batch).execute()
                logger.debug(f"Inserted {len(status_batch)} status records")
                await self.metrics.inc("batch_status", len(status_batch))

            if offline_event_batch:
                result = supabase.table("offline_events").insert(offline_event_batch).execute()
                logger.debug(f"Inserted {len(offline_event_batch)} offline events")
                await self.metrics.inc("batch_offline_events", len(offline_event_batch))

            # Insert alerts
            if alert_insert_batch:
                result = supabase.table("alerts").insert(alert_insert_batch).execute()
                logger.debug(f"Inserted {len(alert_insert_batch)} alerts")
                await self.metrics.inc("batch_alerts", len(alert_insert_batch))

            # Update alerts (close recovered alerts)
            if alert_update_list:
                for alert_upd in alert_update_list:
                    result = supabase.table("alerts") \
                        .update({"end_time": alert_upd.get("end_time")}) \
                        .eq("device_id", alert_upd.get("device_id")) \
                        .eq("alert_type", alert_upd.get("alert_type")) \
                        .is_("end_time", None) \
                        .execute()
                    logger.debug(f"Closed alert for {alert_upd.get('device_id')} - {alert_upd.get('alert_type')}")

            # Update device status
            if device_updates:
                for dev_id, updates in device_updates.items():
                    result = supabase.table("devices") \
                        .update(updates) \
                        .eq("id", dev_id) \
                        .execute()
                    logger.debug(f"Updated device {dev_id}: {updates}")

        except Exception as e:
            logger.error(f"Batch flush error: {e}")
            await self.metrics.inc("supabase_errors")
            await self.metrics.add_error("supabase", str(e))

    async def process_item(
        self,
        op_type: str,
        data: Dict[str, Any],
        telemetry_batch: List[Dict],
        status_batch: List[Dict],
        alert_insert_batch: List[Dict],
        alert_update_list: List[Dict],
        offline_event_batch: List[Dict],
        device_updates: Dict[str, Dict[str, Any]],
    ) -> None:
        """Process a queue item"""
        if op_type == 'telemetry':
            telemetry_batch.append(data)
            await self.metrics.inc("telemetry_received")
        elif op_type == 'status':
            status_batch.append(data)
            await self.metrics.inc("status_received")
        elif op_type == 'offline_event':
            offline_event_batch.append(data)
            await self.metrics.inc("offline_events")

    def stop(self) -> None:
        """Stop batch worker"""
        self._running = False
