import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.exceptions import OtaUpgradeNotFoundException, InvalidTransitionException


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


class TestOtaService:
    """Test OtaService"""

    @pytest.mark.asyncio
    async def test_create_upgrade(self):
        """Test creating OTA upgrade"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[{"id": "upgrade1", "status": "pending"}])
        ))

        with patch('app.services.ota_service.supabase', mock_client):
            from app.services.ota_service import ota_service
            result = await ota_service.create_upgrade(
                device_id="dev1",
                firmware_version="1.0.0",
                firmware_url="http://example.com/firmware.bin"
            )

            assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_upgrade_by_id_not_found(self):
        """Test getting non-existent upgrade"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[])
        ))

        with patch('app.services.ota_service.supabase', mock_client):
            from app.services.ota_service import ota_service
            with pytest.raises(OtaUpgradeNotFoundException):
                await ota_service.get_upgrade_by_id("nonexistent")

    @pytest.mark.asyncio
    async def test_update_progress_invalid_transition(self):
        """Test invalid state transition"""
        # Mock existing upgrade in SUCCESS state
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[{"id": "upg1", "status": "success"}])
        ))

        with patch('app.services.ota_service.supabase', mock_client):
            from app.services.ota_service import ota_service
            with pytest.raises(InvalidTransitionException):
                await ota_service.update_progress(
                    upgrade_id="upg1",
                    status="downloading",
                    progress=50
                )

    @pytest.mark.asyncio
    async def test_get_stuck_upgrades(self):
        """Test getting stuck upgrades"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[])
        ))

        with patch('app.services.ota_service.supabase', mock_client):
            from app.services.ota_service import ota_service
            result = await ota_service.get_stuck_upgrades()
            assert isinstance(result, list)
