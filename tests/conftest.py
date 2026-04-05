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


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    mock_client = MagicMock()
    mock_client.table = MagicMock(side_effect=lambda name: create_mock_query_chain())

    with patch('app.db.supabase._client', mock_client):
        yield mock_client


@pytest.fixture
def mock_mqtt():
    """Mock MQTT service"""
    with patch('app.services.mqtt_service.mqtt_service') as mock:
        yield mock
