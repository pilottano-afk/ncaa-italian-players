import pytest

from ncaa_api.providers.cbbd import CollegeBasketballDataClient, ProviderNotConfigured


def test_client_requires_api_key_without_sending_request() -> None:
    client = CollegeBasketballDataClient(api_key="")
    with pytest.raises(ProviderNotConfigured):
        client.get("games")


def test_client_rejects_historical_season_before_request() -> None:
    client = CollegeBasketballDataClient(api_key="test-key")
    with pytest.raises(ValueError, match="Only season=2027"):
        client.get("games", {"season": 2026})


def test_client_rejects_absolute_endpoint() -> None:
    client = CollegeBasketballDataClient(api_key="test-key")
    with pytest.raises(ValueError, match="relative API path"):
        client.get("https://example.com/games")
