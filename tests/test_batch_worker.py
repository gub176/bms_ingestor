"""Tests for batch worker and metrics collector"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.batch_worker import BatchWorker, MetricsCollector


@pytest.mark.asyncio
async def test_metrics_collector_inc():
    """Test metrics collector increment"""
    collector = MetricsCollector()
    await collector.inc("test_counter")
    stats = await collector.get_stats()
    assert stats["test_counter"] == 1


@pytest.mark.asyncio
async def test_metrics_collector_set():
    """Test metrics collector set"""
    collector = MetricsCollector()
    await collector.set("test_value", 42)
    stats = await collector.get_stats()
    assert stats["test_value"] == 42


@pytest.mark.asyncio
async def test_metrics_collector_update():
    """Test metrics collector bulk update"""
    collector = MetricsCollector()
    # Update existing keys
    await collector.update({"messages_received_total": 10, "messages_processed_total": 20})
    stats = await collector.get_stats()
    assert stats["messages_received_total"] == 10
    assert stats["messages_processed_total"] == 20


@pytest.mark.asyncio
async def test_batch_worker_process_item_telemetry():
    """Test batch worker processes telemetry items"""
    queue = asyncio.Queue()
    collector = MetricsCollector()
    alert_detector = AsyncMock()

    worker = BatchWorker(queue, collector, alert_detector)

    # Create test telemetry data
    telemetry = {
        "device_id": "TEST_DEVICE",
        "timestamp": "2026-04-01T12:00:00Z",
        "voltage": 48.5,
        "current": 10.2,
    }

    telemetry_batch = []
    status_batch = []
    alert_insert_batch = []
    alert_update_list = []
    offline_event_batch = []
    device_updates = {}

    await worker.process_item(
        op_type='telemetry',
        data=telemetry,
        telemetry_batch=telemetry_batch,
        status_batch=status_batch,
        alert_insert_batch=alert_insert_batch,
        alert_update_list=alert_update_list,
        offline_event_batch=offline_event_batch,
        device_updates=device_updates
    )

    # Verify telemetry was queued
    assert len(telemetry_batch) == 1
    stats = await collector.get_stats()
    assert stats["telemetry_received"] == 1


@pytest.mark.asyncio
async def test_batch_worker_process_item_status():
    """Test batch worker processes status items"""
    queue = asyncio.Queue()
    collector = MetricsCollector()
    alert_detector = AsyncMock()

    worker = BatchWorker(queue, collector, alert_detector)

    status = {
        "device_id": "TEST_DEVICE",
        "timestamp": "2026-04-01T12:00:00Z",
        "operation_status": 1,
    }

    status_batch = []

    await worker.process_item(
        op_type='status',
        data=status,
        telemetry_batch=[],
        status_batch=status_batch,
        alert_insert_batch=[],
        alert_update_list=[],
        offline_event_batch=[],
        device_updates={}
    )

    assert len(status_batch) == 1
    stats = await collector.get_stats()
    assert stats["status_received"] == 1


@pytest.mark.asyncio
async def test_batch_worker_process_item_offline():
    """Test batch worker processes offline events"""
    queue = asyncio.Queue()
    collector = MetricsCollector()
    alert_detector = AsyncMock()

    worker = BatchWorker(queue, collector, alert_detector)

    offline = {
        "device_id": "TEST_DEVICE",
        "timestamp": "2026-04-01T12:00:00Z",
        "reason": "connection_lost",
    }

    offline_batch = []

    await worker.process_item(
        op_type='offline_event',
        data=offline,
        telemetry_batch=[],
        status_batch=[],
        alert_insert_batch=[],
        alert_update_list=[],
        offline_event_batch=offline_batch,
        device_updates={}
    )

    assert len(offline_batch) == 1
    stats = await collector.get_stats()
    assert stats["offline_events"] == 1
