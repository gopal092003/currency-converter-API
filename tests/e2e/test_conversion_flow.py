
from __future__ import annotations

from fastapi.testclient import TestClient


def test_end_to_end_eur_to_usd_conversion(client: TestClient):
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
    data = body["data"]

    assert data["from_currency"] == "EUR"
    assert data["to_currency"] == "USD"
    assert float(data["amount"]) == 100.0
    assert float(data["exchange_rate"]) > 0
    assert float(data["converted_amount"]) >= 0


def test_end_to_end_same_currency_conversion(client: TestClient):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "123.45",
            "from_currency": "USD",
            "to_currency": "USD",
        },
    )

    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert body["success"] is True
    assert data["from_currency"] == "USD"
    assert data["to_currency"] == "USD"
    assert float(data["exchange_rate"]) == 1.0
    assert float(data["converted_amount"]) == 123.45


def test_end_to_end_zero_amount(client: TestClient):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "0",
            "from_currency": "EUR",
            "to_currency": "INR",
        },
    )

    assert response.status_code == 200
    assert float(response.json()["data"]["converted_amount"]) == 0.0


def test_end_to_end_rejects_negative_amount(client: TestClient):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "-1",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )

    assert response.status_code in {400, 422}


def test_end_to_end_rejects_malformed_currency_code(
    client: TestClient,
):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "25",
            "from_currency": "EURO",
            "to_currency": "USD",
        },
    )

    assert response.status_code in {400, 422}


def test_end_to_end_latest_rates_can_feed_conversion(
    client: TestClient,
):
    rates_response = client.get(
        "/api/v1/rates/latest",
        params={"base": "EUR", "symbols": "USD"},
    )
    assert rates_response.status_code == 200

    rates = rates_response.json()["data"]["rates"]
    expected_rate = float(rates["USD"])

    conversion_response = client.post(
        "/api/v1/convert",
        json={
            "amount": "10",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )

    assert conversion_response.status_code == 200
    converted = conversion_response.json()["data"]

    assert abs(float(converted["exchange_rate"]) - expected_rate) < 1e-8
