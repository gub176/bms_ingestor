import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.exceptions import DeviceNotFoundException, DeviceAlreadyBoundException


def create_mock_query_chain(execute_result=None):
    """Create a mock query that supports method chaining"""
    mock_query = MagicMock()
    if execute_result is None:
        execute_result = MagicMock(data=[], count=0)
    mock_query.select = MagicMock(return_value=mock_query)
    mock_query.eq = MagicMock(return_value=mock_query)
    mock_query.neq = MagicMock(return_value=mock_query)
    mock_query.gt = MagicMock(return_value=mock_query)
    mock_query.gte = MagicMock(return_value=mock_query)
    mock_query.lt = MagicMock(return_value=mock_query)
    mock_query.lte = MagicMock(return_value=mock_query)
    mock_query.in_ = MagicMock(return_value=mock_query)
    mock_query.order = MagicMock(return_value=mock_query)
    mock_query.range = MagicMock(return_value=mock_query)
    mock_query.insert = MagicMock(return_value=mock_query)
    mock_query.update = MagicMock(return_value=mock_query)
    mock_query.delete = MagicMock(return_value=mock_query)
    mock_query.execute = AsyncMock(return_value=execute_result)
    return mock_query


class TestDeviceService:
    """Test DeviceService"""

    @pytest.mark.asyncio
    async def test_get_devices_with_filters(self):
        """Test getting device list with filters"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[], count=0)
        ))

        with patch('app.services.device_service.supabase', mock_client):
            from app.services.device_service import device_service
            result = await device_service.get_devices(
                user_id="user123",
                status="online",
                page=1,
                page_size=20
            )

            assert "devices" in result
            assert "total" in result
            assert "page" in result
            assert "page_size" in result

    @pytest.mark.asyncio
    async def test_get_device_by_id_not_found(self):
        """Test getting non-existent device"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[])
        ))

        with patch('app.services.device_service.supabase', mock_client):
            from app.services.device_service import device_service
            with pytest.raises(DeviceNotFoundException):
                await device_service.get_device_by_id("nonexistent")

    @pytest.mark.asyncio
    async def test_bind_device_already_bound(self):
        """Test binding already bound device"""
        mock_client = MagicMock()
        # First call (get_device_by_serial) returns existing device
        # Second call (user_devices check) returns device with user_id
        mock_query = create_mock_query_chain(
            MagicMock(data=[{"id": "dev1", "user_id": "user123"}])
        )
        mock_client.table = MagicMock(return_value=mock_query)

        with patch('app.services.device_service.supabase', mock_client):
            from app.services.device_service import device_service
            with pytest.raises(DeviceAlreadyBoundException):
                await device_service.bind_device("DEV123", "user456")

    @pytest.mark.asyncio
    async def test_update_device_status(self):
        """Test updating device status"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[{"id": "dev1", "status": "offline"}])
        ))

        with patch('app.services.device_service.supabase', mock_client):
            from app.services.device_service import device_service
            result = await device_service.update_device_status("dev1", "offline")

            assert result["status"] == "offline"
