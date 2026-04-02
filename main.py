# converter.py
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

EXCHANGE_API = "https://api.frankfurter.app/latest"

@app.route("/convert", methods=["GET"])
def convert_currency():
    try:
        # Get parameters from request
        amount = float(request.args.get("amount", 1))
        from_currency = request.args.get("from", "USD").upper()
        to_currency = request.args.get("to", "EUR").upper()

        # Fetch exchange rate
        response = requests.get(EXCHANGE_API, params={"base": from_currency, "symbols": to_currency})
        data = response.json()

        if "rates" not in data or to_currency not in data["rates"]:
            return jsonify({"error": "Invalid currency code"}), 400

        rate = data["rates"][to_currency]
        converted_amount = amount * rate

        return jsonify({
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
            "rate": rate,
            "converted": round(converted_amount, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
