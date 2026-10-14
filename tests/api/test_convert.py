
"""API tests for currency conversion."""

import pytest


@pytest.mark.api
def test_convert_success(client):
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
    assert body["data"]["amount"] == "100.00"
    assert body["data"]["from_currency"] == "EUR"
    assert body["data"]["to_currency"] == "USD"
    assert body["data"]["exchange_rate"] == "1.17"
    assert body["data"]["converted_amount"] == "117.00"


@pytest.mark.api
def test_convert_normalizes_currency_codes(client):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "10",
            "from_currency": "eur",
            "to_currency": "usd",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["from_currency"] == "EUR"
    assert response.json()["data"]["to_currency"] == "USD"


@pytest.mark.api
def test_convert_rejects_missing_fields(client):
    response = client.post(
        "/api/v1/convert",
        json={"amount": "10", "from_currency": "EUR"},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.api
def test_convert_rejects_negative_amount(client):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "-1",
            "from_currency": "EUR",
            "to_currency": "USD",
        },
    )

    assert response.status_code == 422


@pytest.mark.api
def test_convert_rejects_invalid_currency_code(client):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "10",
            "from_currency": "EURO",
            "to_currency": "USD",
        },
    )

    assert response.status_code == 422


@pytest.mark.api
def test_convert_rejects_unexpected_fields(client):
    response = client.post(
        "/api/v1/convert",
        json={
            "amount": "10",
            "from_currency": "EUR",
            "to_currency": "USD",
            "unexpected": True,
        },
    )

    assert response.status_code == 422
