
from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_contract(client: TestClient):
    response = client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_convert_v1_route_contract(client: TestClient):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "100.00",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert "data" in body
    data = body["data"]

    assert data["from_currency"] == "EUR"
    assert data["to_currency"] == "USD"
    assert "amount" in data
    assert "exchange_rate" in data
    assert "converted_amount" in data


def test_latest_rates_v1_route_contract(client: TestClient):
    response = client.get(
        "/api/v1/rates/latest",
        params={"base": "EUR", "symbols": "USD,INR"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert "data" in body
    assert body["data"]["base"] == "EUR"
    assert "rates" in body["data"]
    assert "rate_date" in body["data"]


def test_historical_rates_v1_route_contract(client: TestClient):
    response = client.get(
        "/api/v1/rates/historical",
        params={
            "base": "EUR",
            "date": "2026-10-01",
            "symbols": "USD",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["data"]["base"] == "EUR"
    assert "rates" in body["data"]


def test_supported_currencies_v1_route_contract(client: TestClient):
    response = client.get("/api/v1/currencies")

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert isinstance(body["currencies"], list)
    assert body["count"] == len(body["currencies"])


def test_invalid_conversion_keeps_validation_contract(
    client: TestClient,
):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "-10",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )

    assert response.status_code in {400, 422}


def test_unsupported_currency_is_not_reported_as_success(
    client: TestClient,
):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "10",
            "from_currency": "EUR",
            "to_currency": "ZZZ",
        },
    )

    assert response.status_code >= 400
    assert response.json().get("success") is not True


def test_v1_paths_do_not_require_an_extra_prefix(client: TestClient):
    # Guard against accidentally mounting /api/v1 twice.
    assert client.get("/api/v1/rates/latest").status_code != 404
    assert client.get("/api/v1/v1/rates/latest").status_code == 404
