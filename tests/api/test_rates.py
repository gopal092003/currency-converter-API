
"""API tests for exchange-rate endpoints."""

import pytest


@pytest.mark.api
def test_get_latest_rates(client):
    response = client.get(
        "/api/v1/rates/latest",
        params=[
            ("base", "EUR"),
            ("symbols", "USD"),
            ("symbols", "INR"),
        ],
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["base"] == "EUR"
    assert body["data"]["rates"]["USD"] == "1.17"
    assert body["data"]["rates"]["INR"] == "103.50"


@pytest.mark.api
def test_get_latest_rates_with_default_base(client):
    response = client.get(
        "/api/v1/rates/latest",
        params={"symbols": "USD"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["base"] == "EUR"


@pytest.mark.api
def test_get_historical_rates(client):
    response = client.get(
        "/api/v1/rates/historical",
        params={
            "date": "2026-10-01",
            "base": "EUR",
            "symbols": "INR",
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["base"] == "EUR"
    assert body["data"]["rate_date"] == "2026-10-01"
    assert body["data"]["rates"]["INR"] == "103.50"


@pytest.mark.api
def test_get_time_series(client):
    response = client.get(
        "/api/v1/rates/time-series",
        params={
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
            "base": "EUR",
            "symbols": "USD",
        },
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    assert body["success"] is True
    assert data["base"] == "EUR"
    assert data["start_date"] == "2026-10-01"
    assert data["end_date"] == "2026-10-03"
    assert data["rates"]["2026-10-01"]["USD"] == "1.17"


@pytest.mark.api
def test_historical_rates_reject_invalid_date(client):
    response = client.get(
        "/api/v1/rates/historical",
        params={"date": "not-a-date", "base": "EUR"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.api
def test_time_series_rejects_invalid_date_format(client):
    response = client.get(
        "/api/v1/rates/time-series",
        params={
            "start_date": "2026/10/01",
            "end_date": "2026-10-03",
        },
    )

    assert response.status_code == 422


@pytest.mark.api
def test_time_series_rejects_start_after_end(client):
    response = client.get(
        "/api/v1/rates/time-series",
        params={
            "start_date": "2026-10-10",
            "end_date": "2026-10-01",
        },
    )

    assert response.status_code == 422
