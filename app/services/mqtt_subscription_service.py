"""MQTT subscription service for direct device data ingestion"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import aiomqtt
from aiomqtt import Client as MqttClient, TLSParameters
from loguru import logger
from app.core.config import settings


# Telemetry array prefix mapping (from bms_mqtt_ingestor)
TELEMETRY_ARRAY_PREFIX_MAP = {
    "011170": "cell_voltages",      # mV
    "011290": "cell_socs",           # 0.1%
    "011190": "cell_temperatures",   # 0.1°C
}

# Known telemetry scalar fields (single values, not arrays)
KNOWN_SCALAR_FIELDS = {
    "01001001",  # Total voltage
    "01001002",  # Total current
    "01001003",  # SOC
    "01001004",  # SOE
    "01001005",  # Cycle count
    "01001006",  # MOS temperature
    "01001007",  # Ambient temperature
    "01001008",  # Cell max voltage
    "01001009",  # Cell min voltage
    "01001010",  # Cell max temp
    "01001011",  # Cell min temp
    "01101001",  # Power
    "01101002",  # Frequency
}

# All known prefixes (arrays + scalars)
ALL_KNOWN_PREFIXES = set(TELEMETRY_ARRAY_PREFIX_MAP.keys()) | KNOWN_SCALAR_FIELDS

# Status signal field mapping
STATUS_FIELD_MAP = {
    "TS001": "operation_status",
    "TS002": "charge_discharge_status",
    "TS003": "grid_connection_status",
    "TS004": "main_contactor_status",
    "TS005": "emergency_stop_status",
    "TS006": "battery_balancing_status",
}

# Heartbeat interval for login response (seconds)
HEARTBEAT_INTERVAL = 60


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string"""
    try:
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        ts = datetime.fromisoformat(timestamp_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except Exception:
        logger.warning(f"Invalid timestamp: {timestamp_str}, using current UTC")
        return datetime.now(timezone.utc)


def parse_telemetry_array(telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse dynamic array fields from telemetry data

    Stores known fields as columns and unknown fields in data JSONB.
    """
    array_values = {field: {} for field in TELEMETRY_ARRAY_PREFIX_MAP.values()}
    matched_keys = set()
    result = {}
    raw_data = {}  # Store unknown signal IDs for JSONB column

    for key, value in telemetry_data.items():
        if not isinstance(key, str) or not isinstance(value, (int, float)):
            continue

        # Check if this is a known field
        is_known = False
        for prefix, field in TELEMETRY_ARRAY_PREFIX_MAP.items():
            if key.startswith(prefix):
                is_known = True
                matched_keys.add(key)
                try:
                    idx_str = key[-2:]
                    idx = int(idx_str)
                    array_values[field][idx] = value
                except (ValueError, IndexError):
                    logger.debug(f"Invalid index in key: {key}")
                break

        # Also allow known scalar fields
        if not is_known and key in KNOWN_SCALAR_FIELDS:
            is_known = True
            # Map scalar field to a simple name (use key as field name for now)
            result[key] = value

        # Store unknown fields in raw_data for JSONB column
        if not is_known:
            raw_data[key] = value

    # Convert dict to list for array fields
    for field, values_dict in array_values.items():
        if values_dict:
            max_idx = max(values_dict.keys())
            arr = [0] * max_idx
            for idx, val in values_dict.items():
                arr[idx - 1] = val
            result[field] = arr

    # Store raw data if any unknown fields exist
    if raw_data:
        result["data"] = raw_data

    return result


class MqttSubscriptionService:
    """
    MQTT subscription service.

    Subscribes to device topics and enqueues messages for batch processing.
    """

    def __init__(self, queue: asyncio.Queue, metrics_collector, alert_detector):
        self.queue = queue
        self.metrics = metrics_collector
        self.alert_detector = alert_detector
        self._running = False
        self._mqtt_client: Optional[MqttClient] = None

    async def run(self) -> None:
        """Run MQTT subscription loop"""
        self._running = True
        reconnect_interval = 5

        while self._running:
            try:
                # Configure TLS if enabled
                tls_params = TLSParameters() if getattr(settings, 'mqtt_tls_enable', True) else None

                # Generate unique client ID
                client_id = f"fastapi_backend_{uuid.uuid4().hex[:8]}"

                async with MqttClient(
                    hostname=getattr(settings, 'emqx_host', 'localhost'),
                    port=getattr(settings, 'emqx_port', 1883),
                    username=getattr(settings, 'emqx_username', None),
                    password=getattr(settings, 'emqx_password', None),
                    tls_params=tls_params,
                    identifier=client_id,
                    keepalive=30,
                ) as client:
                    self._mqtt_client = client
                    logger.info(f"Connected to MQTT broker")

                    # Subscribe to topics
                    topics = ["ess/bms/+/up", "ess/bms/+/will"]
                    for topic in topics:
                        await client.subscribe(topic, qos=1)
                        logger.info(f"Subscribed to {topic}")

                    # Process messages
                    async for message in client.messages:
                        await self._handle_message(
                            str(message.topic),
                            message.payload,
                        )

                    self._mqtt_client = None

            except aiomqtt.MqttError as e:
                logger.error(f"MQTT connection lost: {e}. Reconnecting...")
                await asyncio.sleep(reconnect_interval)
            except asyncio.CancelledError:
                logger.info("MQTT subscription cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected MQTT error: {e}")
                await asyncio.sleep(reconnect_interval)

    async def _handle_message(self, topic: str, payload: bytes) -> None:
        """Handle incoming MQTT message"""
        await self.metrics.inc("messages_received_total")
        await self.metrics.set("last_message_time", asyncio.get_event_loop().time())

        # Parse payload
        try:
            data = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.error("Invalid JSON payload")
            await self.metrics.inc("json_errors")
            return

        dev_id = data.get("devId")
        timestamp_str = data.get("timestamp")

        if not dev_id or not timestamp_str:
            logger.warning("Missing devId or timestamp")
            return

        timestamp = parse_timestamp(timestamp_str)
        received_at = datetime.now(timezone.utc)

        # Handle will message (offline event)
        if topic.endswith("/will"):
            await self._handle_will(dev_id, timestamp, received_at, data)
            return

        msg_type = data.get("msgType")
        if msg_type is None:
            logger.warning("Missing msgType")
            return

        # Route by msgType
        if msg_type == 100:
            await self._handle_login(dev_id, timestamp)
        elif msg_type == 200:
            await self._handle_heartbeat(dev_id, timestamp)
        elif msg_type == 300:
            await self._handle_telemetry(dev_id, timestamp, received_at, data)
        elif msg_type == 310:
            await self._handle_status(dev_id, timestamp, received_at, data)

    async def _handle_will(self, dev_id: str, timestamp: datetime, received_at: datetime, data: Dict) -> None:
        """Handle device offline (will message)"""
        reason = data.get("reason", "unknown")
        try:
            await self.queue.put({
                "op_type": "offline_event",
                "data": {
                    "device_id": dev_id,
                    "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
                    "reason": reason,
                    "created_at": received_at.isoformat().replace('+00:00', 'Z'),
                }
            })
            # Also queue device_offline to update device status
            await self.queue.put({
                "op_type": "device_offline",
                "data": {
                    "device_id": dev_id,
                    "timestamp": timestamp,
                }
            })
            logger.info(f"Device offline: {dev_id}, reason={reason}")
        except asyncio.QueueFull:
            logger.error(f"Queue full, dropping offline event for {dev_id}")
            await self.metrics.inc("messages_dropped_total")

    async def _handle_login(self, dev_id: str, timestamp: datetime) -> None:
        """Handle device login"""
        try:
            await self.queue.put({
                "op_type": "device_online",
                "data": {"device_id": dev_id, "timestamp": timestamp}
            })
        except asyncio.QueueFull:
            await self.metrics.inc("messages_dropped_total")

        # Publish login response to device
        await self._publish_login_response(dev_id, timestamp)

    async def _handle_heartbeat(self, dev_id: str, timestamp: datetime) -> None:
        """Handle device heartbeat"""
        try:
            await self.queue.put({
                "op_type": "device_online",
                "data": {"device_id": dev_id, "timestamp": timestamp}
            })
        except asyncio.QueueFull:
            await self.metrics.inc("messages_dropped_total")

    async def _handle_telemetry(
        self,
        dev_id: str,
        timestamp: datetime,
        received_at: datetime,
        data: Dict,
    ) -> None:
        """Handle telemetry data"""
        telemetry_data = data.get("data", {})
        if not telemetry_data:
            return

        # Parse array fields
        parsed = parse_telemetry_array(telemetry_data.copy())

        record = {
            "device_id": dev_id,
            "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
            "received_at": received_at.isoformat().replace('+00:00', 'Z'),
            **parsed
        }

        try:
            await self.queue.put({"op_type": "telemetry", "data": record})
        except asyncio.QueueFull:
            await self.metrics.inc("messages_dropped_total")

    async def _handle_status(
        self,
        dev_id: str,
        timestamp: datetime,
        received_at: datetime,
        data: Dict,
    ) -> None:
        """Handle status data and detect alerts"""
        status_data = data.get("data", {})
        if not status_data:
            return

        # Map status fields
        record = {
            "device_id": dev_id,
            "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
            "received_at": received_at.isoformat().replace('+00:00', 'Z'),
        }

        for signal_id, db_field in STATUS_FIELD_MAP.items():
            if signal_id in status_data:
                record[db_field] = status_data[signal_id]

        try:
            await self.queue.put({"op_type": "status", "data": record})
        except asyncio.QueueFull:
            await self.metrics.inc("messages_dropped_total")

        # Detect alerts
        if self.alert_detector:
            alerts_insert, alerts_update = await self.alert_detector.process(
                dev_id, timestamp, status_data
            )

            for alert in alerts_insert:
                try:
                    await self.queue.put({
                        "op_type": "alert",
                        "data": alert.to_dict()
                    })
                    await self.metrics.inc("alerts_generated")
                except asyncio.QueueFull:
                    await self.metrics.inc("messages_dropped_total")

            # Queue alert updates (recoveries)
            for alert_upd in alerts_update:
                try:
                    await self.queue.put({
                        "op_type": "alert_update",
                        "data": alert_upd
                    })
                except asyncio.QueueFull:
                    await self.metrics.inc("messages_dropped_total")

    def stop(self) -> None:
        """Stop subscription service"""
        self._running = False

    async def _publish_login_response(self, dev_id: str, req_timestamp: datetime) -> None:
        """
        Publish login response to device

        Args:
            dev_id: Device ID
            req_timestamp: Request timestamp
        """
        if self._mqtt_client is None:
            logger.warning("MQTT client not connected, cannot publish login response")
            return

        current_time = datetime.now(timezone.utc)
        payload = {
            "msgType": 101,
            "devId": dev_id,
            "timestamp": current_time.isoformat().replace('+00:00', 'Z'),
            "data": {
                "result": 1,
                "heartbeat_interval": HEARTBEAT_INTERVAL
            }
        }

        topic = f"ess/bms/{dev_id}/down"
        try:
            await self._mqtt_client.publish(topic, json.dumps(payload), qos=1)
            logger.debug(f"Login response published to {topic}")
        except Exception as e:
            logger.error(f"Error publishing login response: {e}")
