from flask import Blueprint, request, jsonify
from app.services.converter_service import convert_currency

currency_bp = Blueprint("currency", __name__)

@currency_bp.route("/convert", methods=["GET"])
def convert():
    try:
        amount = float(request.args.get("amount", 1))
        from_currency = request.args.get("from", "USD").upper()
        to_currency = request.args.get("to", "EUR").upper()

        result = convert_currency(amount, from_currency, to_currency)

        return jsonify(result)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500