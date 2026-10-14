# API Reference

## Base URL and conventions

Local development base URL: `http://127.0.0.1:8000`.

The mounted public API is V1 under `/api/v1`. Endpoints accept and return JSON
where applicable. Interactive OpenAPI documentation is available at `/docs`,
`/redoc`, and `/openapi.json` outside the production environment.

Currency codes are normalized to uppercase and must consist of three letters.
Conversion amounts are non-negative decimals with at most 30 significant
digits and 10 decimal places. Responses serialize monetary and rate values as
decimal strings.

## Endpoint summary

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/convert` | Convert an amount |
| `GET` | `/api/v1/rates/latest` | Retrieve latest rates |
| `GET` | `/api/v1/rates/historical` | Retrieve rates for a date |
| `GET` | `/api/v1/rates/time-series` | Retrieve rates for a date range |
| `GET` | `/api/v1/currencies` | List currencies present in latest rates |
| `GET` | `/health/live` | Report that the process responds |

The application does not currently mount API-key management, usage, readiness,
or metrics endpoints. Supporting modules and deployment manifests are not a
substitute for mounted and tested routes.

## Convert

`POST /api/v1/convert`

Request:

```json
{
  "amount": "100.00",
  "from_currency": "EUR",
  "to_currency": "USD"
}
```

The amount must be non-negative. Currency values are uppercased and validated
as three-letter codes. Unknown or unavailable target rates result in an
`UNSUPPORTED_CURRENCY` application error. Same-currency conversion returns a
rate of `1` without an external lookup.

Response shape:

```json
{
  "success": true,
  "data": {
    "amount": "100.00",
    "from_currency": "EUR",
    "to_currency": "USD",
    "exchange_rate": "1.08",
    "converted_amount": "108.00",
    "rate_date": "2026-10-14"
  }
}
```

The values are illustrative. `rate_date` is `null` when no provider date
applies, including same-currency conversions. Converted amounts are rounded
according to the target currency's configured minor-unit precision, using
half-even rounding. The currency precision registry includes selected common
currencies and defaults other currencies to two decimal places.

## Latest rates

`GET /api/v1/rates/latest`

| Query parameter | Required | Default | Description |
|---|---|---|---|
| `base` | No | `EUR` | Three-letter base currency |
| `symbols` | No | all returned | Comma-separated or repeated target currency codes |

Example:

```text
GET /api/v1/rates/latest?base=EUR&symbols=USD,INR
```

Response shape:

```json
{
  "success": true,
  "data": {
    "base": "EUR",
    "rate_date": "2026-10-14",
    "rates": {
      "INR": "90.0",
      "USD": "1.08"
    }
  }
}
```

The date and rates are provider data, not guaranteed to reflect today's
calendar date.

## Historical rates

`GET /api/v1/rates/historical`

| Query parameter | Required | Default | Description |
|---|---|---|---|
| `date` | Yes | — | Requested date in `YYYY-MM-DD` format; must not be in the future |
| `base` | No | `EUR` | Three-letter base currency |
| `symbols` | No | all returned | Comma-separated or repeated target currency codes |

The response uses the same `RateResponse` envelope as the latest-rates
endpoint. The service preserves the actual provider observation date and
rejects a provider result dated later than the requested date.

## Time-series rates

`GET /api/v1/rates/time-series`

| Query parameter | Required | Default | Description |
|---|---|---|---|
| `start_date` | Yes | — | Inclusive start date in `YYYY-MM-DD` format |
| `end_date` | Yes | — | Inclusive end date; cannot precede `start_date` or be in the future |
| `base` | No | `EUR` | Three-letter base currency |
| `symbols` | No | all returned | Comma-separated or repeated target currency codes |

Response shape:

```json
{
  "success": true,
  "data": {
    "base": "EUR",
    "start_date": "2026-10-01",
    "end_date": "2026-10-07",
    "rates": {
      "2026-10-01": {
        "USD": "1.08"
      }
    }
  }
}
```

Dates without provider observations may be absent from the `rates` mapping.

## Supported currencies

`GET /api/v1/currencies`

The endpoint derives its list from the latest EUR-based provider response and
includes EUR as the base currency. Its response has `success`, `currencies`,
and `count` fields. Each currency item contains a `code`, with `name` and
`symbol` unset and `minor_units` defaulting to `2` in the current response.
Availability may change with the provider.

## Liveness

`GET /health/live`

Returns `{"status":"ok"}` when the application process can respond. It does
not check the provider, database, or Redis.

## Error response

Application errors use this envelope:

```json
{
  "success": false,
  "error": {
    "code": "PROVIDER_TIMEOUT",
    "message": "The exchange-rate provider timed out.",
    "details": null
  }
}
```

Request validation failures return HTTP `422` with code `VALIDATION_ERROR` and
an `errors` array in `details`. Error details may differ by error type. The
mounted handlers do not currently add a request ID to error bodies.

See [Error Codes](error-codes.md) for the known application exception
mappings.
