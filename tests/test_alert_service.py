import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.exceptions import AlertNotFoundException


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


class TestAlertService:
    """Test AlertService"""

    @pytest.mark.asyncio
    async def test_get_alerts_with_filters(self):
        """Test getting alert list with filters"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[], count=0)
        ))

        with patch('app.services.alert_service.supabase', mock_client):
            from app.services.alert_service import alert_service
            result = await alert_service.get_alerts(
                device_id="dev1",
                level="critical",
                is_read=False,
                page=1,
                page_size=20
            )

            assert "alerts" in result
            assert "total" in result
            assert "page" in result

    @pytest.mark.asyncio
    async def test_mark_alert_as_read_not_found(self):
        """Test marking non-existent alert as read"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[])
        ))

        with patch('app.services.alert_service.supabase', mock_client):
            from app.services.alert_service import alert_service
            with pytest.raises(AlertNotFoundException):
                await alert_service.mark_alert_as_read("nonexistent")

    @pytest.mark.asyncio
    async def test_get_alert_stats(self):
        """Test getting alert statistics"""
        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=create_mock_query_chain(
            MagicMock(data=[
                {"level": "critical", "is_read": False, "device_id": "dev1", "type": "over_voltage"},
                {"level": "warning", "is_read": True, "device_id": "dev1", "type": "under_voltage"},
            ])
        ))

        with patch('app.services.alert_service.supabase', mock_client):
            from app.services.alert_service import alert_service
            result = await alert_service.get_alert_stats()

            assert result["total"] == 2
            assert result["unread"] == 1
            assert "by_level" in result
            assert "by_device" in result
