
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter
from dataclasses import dataclass

import httpx


@dataclass
class RequestResult:
    status_code: int
    latency_ms: float
    error: str | None = None


async def send_conversion(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
    amount: str,
    source: str,
    target: str,
) -> RequestResult:
    async with semaphore:
        started = time.perf_counter()

        try:
            response = await client.post(
                url,
                json={
                    "amount": amount,
                    "from_currency": source,
                    "to_currency": target,
                },
            )
            elapsed = (time.perf_counter() - started) * 1000

            return RequestResult(
                status_code=response.status_code,
                latency_ms=elapsed,
            )

        except httpx.HTTPError as exc:
            elapsed = (time.perf_counter() - started) * 1000
            return RequestResult(
                status_code=0,
                latency_ms=elapsed,
                error=type(exc).__name__,
            )


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]


async def run_load_test(
    *,
    base_url: str,
    total_requests: int,
    concurrency: int,
    api_key: str | None,
    timeout_seconds: float,
) -> dict:
    endpoint = f"{base_url.rstrip('/')}/api/v1/convert"
    semaphore = asyncio.Semaphore(concurrency)

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )
    timeout = httpx.Timeout(timeout_seconds)

    started = time.perf_counter()

    async with httpx.AsyncClient(
        headers=headers,
        limits=limits,
        timeout=timeout,
    ) as client:
        tasks = [
            send_conversion(
                client,
                semaphore,
                endpoint,
                amount="100.00",
                source="EUR",
                target="USD",
            )
            for _ in range(total_requests)
        ]
        results = await asyncio.gather(*tasks)

    elapsed_seconds = time.perf_counter() - started
    latencies = [result.latency_ms for result in results]
    status_counts = Counter(str(result.status_code) for result in results)
    errors = Counter(
        result.error for result in results if result.error is not None
    )

    successful = sum(
        200 <= result.status_code < 300 for result in results
    )
    rate_limited = sum(result.status_code == 429 for result in results)
    server_errors = sum(result.status_code >= 500 for result in results)

    report = {
        "endpoint": endpoint,
        "total_requests": total_requests,
        "concurrency": concurrency,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "requests_per_second": round(
            total_requests / elapsed_seconds if elapsed_seconds else 0,
            2,
        ),
        "successful_requests": successful,
        "rate_limited_requests": rate_limited,
        "server_errors": server_errors,
        "status_counts": dict(status_counts),
        "transport_errors": dict(errors),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 2) if latencies else 0,
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
            "max": round(max(latencies), 2) if latencies else 0,
        },
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load test the Currency Converter API."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional test API key. Avoid putting production secrets in shell history.",
    )
    args = parser.parse_args()

    if args.requests < 1:
        parser.error("--requests must be at least 1")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    report = asyncio.run(
        run_load_test(
            base_url=args.base_url,
            total_requests=args.requests,
            concurrency=args.concurrency,
            api_key=args.api_key,
            timeout_seconds=args.timeout,
        )
    )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
