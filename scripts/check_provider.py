"""Manually verify exchange-rate provider connectivity and response format."""

import argparse
import asyncio
import logging
import sys
from datetime import date
from decimal import Decimal

import httpx
from app.core.config import settings
from app.modules.providers.exceptions import ProviderError
from app.modules.providers.factory import create_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check exchange-rate provider connectivity."
    )
    parser.add_argument(
        "--base",
        default="EUR",
        help="Base currency code (default: EUR).",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["USD", "INR"],
        help="Target currency codes (default: USD INR).",
    )
    return parser.parse_args()


async def check_provider(base: str, symbols: list[str]) -> bool:
    base = base.strip().upper()
    symbols = sorted({symbol.strip().upper() for symbol in symbols})

    print(f"Provider: {settings.exchange_provider}")
    print(f"Base currency: {base}")
    print(f"Requested symbols: {', '.join(symbols)}")
    print("Checking connectivity...")

    timeout = httpx.Timeout(settings.exchange_timeout_seconds)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            provider = create_provider(client=client)
            payload = await provider.get_latest_rates(
                base=base,
                symbols=symbols,
            )

        if not isinstance(payload, dict):
            raise ValueError("Response must be a JSON object.")

        returned_base = payload.get("base")
        returned_date = payload.get("date")
        rates = payload.get("rates")

        if returned_base != base:
            raise ValueError(f"Expected base {base}, received {returned_base!r}.")

        if not isinstance(returned_date, str):
            raise ValueError("Missing or invalid response date.")

        parsed_date = date.fromisoformat(returned_date)
        if parsed_date > date.today():
            raise ValueError("Provider returned a future rate date.")

        if not isinstance(rates, dict):
            raise ValueError("Response 'rates' must be an object.")

        missing = set(symbols) - set(rates)
        if missing:
            raise ValueError(f"Missing requested rates: {', '.join(sorted(missing))}")

        for code in symbols:
            rate = Decimal(str(rates[code]))
            if not rate.is_finite() or rate <= 0:
                raise ValueError(f"Invalid rate returned for {code}.")

        print("Result: SUCCESS")
        print(f"Effective rate date: {returned_date}")
        print(f"Returned base: {returned_base}")
        print("Validated rates:")

        for code in symbols:
            print(f"  {base}/{code}: {rates[code]}")

        return True

    except (ProviderError, httpx.HTTPError, ValueError) as exc:
        print(f"Result: FAILED — {type(exc).__name__}: {exc}")
        return False
    except Exception:
        logging.exception("Unexpected provider diagnostic failure.")
        print("Result: FAILED — unexpected error.")
        return False


def main() -> int:
    args = parse_args()

    try:
        success = asyncio.run(check_provider(args.base, args.symbols))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
