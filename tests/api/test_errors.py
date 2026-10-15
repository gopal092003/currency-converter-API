"""API tests for standardized error responses."""

import pytest
from app.api.dependencies import get_rates_service
from app.core.exceptions import ProviderError


class FailingRatesService:
    """Service stub that simulates an upstream provider failure."""

    async def get_latest_rates(self, *args, **kwargs):
        raise ProviderError(
            "The exchange-rate provider is unavailable.",
            retryable=True,
        )


@pytest.mark.api
def test_validation_error_response(client):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "not-a-number",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )

    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"]
    assert isinstance(body["error"]["details"]["errors"], list)


@pytest.mark.api
def test_missing_query_parameter_returns_validation_error(client):
    response = client.get(
        "/api/v1/rates/historical",
        params={"base": "EUR"},
    )

    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.api
def test_provider_error_uses_standard_error_response(app, client):
    app.dependency_overrides[get_rates_service] = lambda: FailingRatesService()

    try:
        response = client.get(
            "/api/v1/rates/latest",
            params={"base": "EUR"},
        )
    finally:
        app.dependency_overrides.pop(get_rates_service, None)

    assert response.status_code == 502

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PROVIDER_ERROR"
    assert body["error"]["message"]
    assert "details" in body["error"]


@pytest.mark.api
def test_unknown_route_returns_not_found(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
