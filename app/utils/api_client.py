import requests
from app.config.settings import EXCHANGE_API

def get_exchange_rate(from_currency, to_currency):
    response = requests.get(
        EXCHANGE_API,
        params={"base": from_currency, "symbols": to_currency}
    )

    data = response.json()

    if "rates" not in data or to_currency not in data["rates"]:
        raise ValueError("Invalid currency code")

    return data["rates"][to_currency]