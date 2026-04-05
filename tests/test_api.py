import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def create_mock_query_chain():
    """Create a mock query that supports method chaining"""
    mock_query = MagicMock()
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
    mock_query.execute = AsyncMock(return_value=MagicMock(data=[], count=0))
    return mock_query


@pytest.fixture(scope="session", autouse=True)
def mock_all_dependencies():
    """Mock all external dependencies"""
    mock_client = MagicMock()
    mock_client.table = MagicMock(side_effect=lambda name: create_mock_query_chain())

    with patch('app.db.supabase._client', mock_client), \
         patch('app.services.mqtt_service.mqtt_service') as mock_mqtt, \
         patch('app.services.offline_detection.offline_detection_service') as mock_offline, \
         patch('app.services.ota_recovery.ota_recovery_service') as mock_ota_recovery:
        yield


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
