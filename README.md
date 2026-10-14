# Currency Converter API

A FastAPI service that retrieves reference exchange rates from Frankfurter and
provides currency conversion, latest-rate, historical-rate, time-series, and
supported-currency endpoints.

| | |
|---|---|
| Package version | `2.0.0` |
| Python | 3.11 or later |
| API version currently mounted | V1 (`/api/v1`) |
| Default provider | Frankfurter |

This repository also contains database, API-key, rate-limiting, cache, and
observability modules. Not all of those modules are connected to the public
application yet. See [Architecture](docs/architecture.md) for the implemented
runtime boundary and [Security](docs/security.md) for current limitations.

## Features

- Convert non-negative decimal amounts using the latest provider rate.
- Retrieve latest rates, historical rates, and inclusive date-range series.
- List currencies returned by the provider's latest rates.
- Validate and normalize currency codes and provider responses.
- Apply target-currency rounding using decimal arithmetic and half-even rounding.
- Bound upstream HTTP requests with a configurable timeout and transient retries.
- Return normalized application and request-validation error envelopes.
- Expose a liveness endpoint at `/health/live`.

Rates are reference data, not an executable quote. The application does not
guarantee bank, card-network, or payment-provider prices.

## Requirements

- Python 3.11 or newer
- pip
- Git

Docker is needed only when using the supplied container setup. The API's
currently mounted request path does not require Redis or a database.

## Run locally

```powershell
git clone https://github.com/gopal092003/currency-converter-API.git
Set-Location currency-converter-API
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

For Linux or macOS, activate the environment with
`source .venv/bin/activate` and copy the configuration with
`cp .env.example .env`.

The local API is available at `http://127.0.0.1:8000`. In non-production
environments, FastAPI's interactive docs and OpenAPI schema are available at
`/docs`, `/redoc`, and `/openapi.json`. These are disabled when
`APP_ENV=production`.

Check liveness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
```

The response is `{"status":"ok"}`. There is currently no mounted readiness
endpoint.

## API quick start

Convert an amount:

```powershell
$body = @{
  amount = "100.00"
  from_currency = "EUR"
  to_currency = "USD"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/convert `
  -ContentType "application/json" `
  -Body $body
```

Retrieve latest rates:

```powershell
Invoke-RestMethod `
  "http://127.0.0.1:8000/api/v1/rates/latest?base=EUR&symbols=USD,INR"
```

The complete endpoint and response contract is in [API Reference](docs/api.md).

## Configuration

Settings are loaded from environment variables and `.env` (UTF-8, case
insensitive); explicitly supplied environment variables take precedence over
the `.env` file. Defaults and validation are defined in `app/core/config.py`.

| Variable | Default | Purpose |
|---|---:|---|
| `APP_NAME` | `Currency Converter API` | OpenAPI application title |
| `APP_ENV` | `development` | One of `development`, `testing`, `staging`, `production` |
| `APP_VERSION` | `2.0.0` | OpenAPI application version |
| `DEBUG` | `false` | FastAPI debug mode; rejected in production |
| `HOST` | `127.0.0.1` | Configured bind address |
| `PORT` | `8000` | Configured port |
| `LOG_LEVEL` | `INFO` | Configured logging level |
| `API_V1_PREFIX` | `/api/v1` | V1 router prefix |
| `API_V2_PREFIX` | `/api/v2` | Reserved prefix; no V2 router is mounted |
| `EXCHANGE_PROVIDER` | `frankfurter` | Provider selection setting |
| `EXCHANGE_API` | `https://api.frankfurter.app/latest` | Frankfurter endpoint used to derive provider URL |
| `EXCHANGE_TIMEOUT_SECONDS` | `5` | Positive upstream HTTP timeout, maximum 120 seconds |
| `EXCHANGE_MAX_RETRIES` | `2` | Retries after the initial provider request, range 0–10 |
| `RATE_CACHE_TTL_SECONDS` | `3600` | TTL used by the in-memory cache helper |
| `MAX_STALE_RATE_AGE_SECONDS` | `86400` | Threshold used by freshness-policy helper |
| `REDIS_URL` | unset | Optional Redis connection setting; not used by the mounted API |
| `DATABASE_URL` | unset | Optional database connection setting; not used by the mounted API |
| `API_KEY_AUTH_ENABLED` | `false` | Authentication setting; public routes do not currently enforce it |
| `API_KEY_PEPPER` | unset | Required when API-key authentication is enabled; secret value |
| `RATE_LIMIT_ENABLED` | `false` | Rate-limit setting; middleware is not currently mounted |
| `RATE_LIMIT_REQUESTS` | `60` | Configured request count for rate limiting |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Configured rate-limit window |
| `USAGE_QUOTA_ENABLED` | `false` | Usage-quota setting; not currently enforced by public routes |
| `MONTHLY_REQUEST_QUOTA` | `10000` | Configured default monthly quota |
| `METRICS_ENABLED` | `true` | Metrics setting; no metrics route is currently mounted |
| `METRICS_PATH` | `/metrics` | Configured metrics path |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Configured request-ID header name |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated explicit browser origins |
| `HTTP_MAX_CONNECTIONS` | `100` | Shared HTTP client's maximum connections |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | `20` | Shared HTTP client's maximum keep-alive connections |
| `TESTING` | `false` | Testing setting |

The optional API-key, usage, rate-limit, cache, database, and metrics settings
describe supporting modules; setting them does not activate routes or
middleware that the application has not mounted. For local use, leave the
example values unchanged unless a specific integration is being developed.
Never commit real secrets. See [Security](docs/security.md) before enabling
authentication in a deployment.

## API overview

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/convert` | Convert an amount |
| `GET` | `/api/v1/rates/latest` | Latest rates |
| `GET` | `/api/v1/rates/historical` | Rates for a requested date |
| `GET` | `/api/v1/rates/time-series` | Rates over an inclusive date range |
| `GET` | `/api/v1/currencies` | Currency codes from the latest EUR-based rates |
| `GET` | `/health/live` | Process liveness |

`/health/ready`, `/metrics`, API-key management, and usage endpoints are not
currently mounted. See [Error Codes](docs/error-codes.md) for error response
details.

## Development and tests

Install the optional project dependencies needed by CI:

```powershell
python -m pip install -e ".[dev,database,redis,observability]"
```

Run tests:

```powershell
python -m pytest
```

Run the same lint and formatting checks as CI:

```powershell
ruff check app tests scripts
ruff format --check app tests scripts
```

The GitHub Actions workflows run lint/format checks, tests with coverage on
Python 3.11 and 3.12, and dependency, static-analysis, secret, and container
security checks. The test job expects PostgreSQL and Redis services and
applies Alembic migrations before running the suite.

## Docker

Build and run the API image:

```powershell
docker build -t currency-converter-api:local .
docker run --rm -p 8000:8000 currency-converter-api:local
```

The image runs as a non-root user and includes a liveness health check. The
Compose file additionally starts PostgreSQL, Redis, and Prometheus, but the
currently mounted public API does not use the database, Redis, or expose
`/metrics`; treat those services as infrastructure scaffolding until those
integrations are connected and verified.

## Documentation

- [API reference](docs/api.md)
- [Architecture and runtime boundaries](docs/architecture.md)
- [Error codes](docs/error-codes.md)
- [Security status and deployment considerations](docs/security.md)
- [Provider outage runbook](docs/runbooks/provider-outage.md)
- [Stale-rates runbook](docs/runbooks/stale-rates.md)

## Contribution

Changes should include tests for behavior changes and corresponding
documentation updates for public API changes. Run the test, lint, and format
commands above before opening a pull request. Do not include secrets, local
environment files, or generated artifacts in a change.

## License

This project is licensed under the MIT License.

## Acknowledgement

Exchange-rate data is provided by [Frankfurter](https://frankfurter.dev/).
