from app.utils.api_client import get_exchange_rate

def convert_currency(amount, from_currency, to_currency):
    rate = get_exchange_rate(from_currency, to_currency)

    converted_amount = amount * rate

    return {
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "rate": rate,
        "converted": round(converted_amount, 2)
    }