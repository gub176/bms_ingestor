import asyncio
import json
import aiomqtt
from typing import Optional, Dict, Any
from loguru import logger
from app.core.config import settings


class MQTTService:
    """MQTT connection and messaging service"""

    def __init__(self):
        self.client: Optional[aiomqtt.Client] = None
        self.connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = aiomqtt.Client(
                hostname=settings.emqx_host,
                port=settings.emqx_port,
                username=settings.emqx_username,
                password=settings.emqx_password,
            )
            await self.client.connect()
            self.connected = True
            self._reconnect_attempts = 0
            logger.info(f"Connected to MQTT broker at {settings.emqx_host}:{settings.emqx_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            await self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")

    async def reconnect(self):
        """Reconnect to MQTT broker with retry"""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(f"Max reconnect attempts ({self._max_reconnect_attempts}) exceeded")
            raise ConnectionError("Max reconnect attempts exceeded")

        self._reconnect_attempts += 1
        logger.info(f"Reconnecting to MQTT broker (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")

        try:
            await self.connect()
            logger.info("Reconnection successful")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            raise

    async def publish(self, topic: str, payload: Dict[str, Any]):
        """Publish a message to MQTT topic"""
        if not self.connected:
            await self.connect()

        try:
            await self.client.publish(topic, json.dumps(payload))
            logger.debug(f"Published to {topic}: {payload}")
        except aiomqtt.MqttError as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            # Try reconnect
            await self.reconnect()
            await self.client.publish(topic, json.dumps(payload))

    async def subscribe(self, topic: str):
        """Subscribe to an MQTT topic"""
        if not self.connected:
            await self.connect()

        await self.client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")

    async def send_ota_command(self, device_id: str, ota_url: str, version: str):
        """Send OTA command to device"""
        topic = f"devices/{device_id}/ota"
        payload = {
            "command": "upgrade",
            "url": ota_url,
            "version": version,
        }
        await self.publish(topic, payload)
        logger.info(f"OTA command sent to device {device_id}")

    async def send_remote_command(self, device_id: str, command: str, params: Optional[Dict] = None):
        """Send remote command to device"""
        topic = f"devices/{device_id}/commands"
        payload = {
            "command": command,
            "params": params or {}
        }
        await self.publish(topic, payload)
        logger.info(f"Remote command sent to device {device_id}: {command}")


# Global MQTT service instance
mqtt_service = MQTTService()
