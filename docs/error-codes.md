# Error Codes

## Response contract

Application exceptions registered by the FastAPI app use this envelope:

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

Request validation failures use HTTP `422` and this shape:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data.",
    "details": {
      "errors": [
        {
          "location": ["body", "amount"],
          "message": "Input should be greater than or equal to 0",
          "type": "greater_than_equal"
        }
      ]
    }
  }
}
```

Validation message wording is supplied by Pydantic and may vary by invalid
field. Error responses do not currently include a request ID. The catalogue
below lists application exception classes; not every class is reachable from
the currently mounted endpoints.

## Application error catalogue

| Code | HTTP status | Meaning |
|---|---:|---|
| `INVALID_REQUEST` | 400 | Application-level request is invalid |
| `VALIDATION_ERROR` | 422 | Request fields or domain values failed validation |
| `UNSUPPORTED_CURRENCY` | 422 | Requested currency/rate is unavailable |
| `RATE_NOT_FOUND` | 404 | Requested rate or resource was not found |
| `AUTHENTICATION_ERROR` | 401 | Authentication is missing or invalid |
| `AUTHORIZATION_ERROR` | 403 | Caller is not authorized |
| `RATE_LIMIT_EXCEEDED` | 429 | Request rate limit was exceeded |
| `QUOTA_EXCEEDED` | 429 | Usage quota was exceeded |
| `PROVIDER_ERROR` | 502 | General provider failure |
| `PROVIDER_UNAVAILABLE` | 502 | Provider cannot be reached |
| `PROVIDER_INVALID_RESPONSE` | 502 | Provider response is invalid |
| `PROVIDER_TIMEOUT` | 504 | Provider request timed out |
| `INTERNAL_ERROR` | 500 | Unexpected application failure |

Some supporting middleware can produce additional errors, such as
`RATE_LIMIT_STORAGE_UNAVAILABLE`, but that middleware is not currently
mounted by the application.

## Client guidance

- Correct invalid input before retrying a `400` or `422`.
- Do not retry `401` or `403` without correcting credentials or permissions.
- Retry transient provider or service failures only with bounded backoff.
- When a mounted component returns `429` with `Retry-After`, wait at least
  that many seconds before retrying.
- Do not assume every `502` is transient; invalid provider payloads should not
  be retried immediately.

Error codes are intended to be stable identifiers. Keep their meaning and
HTTP mapping consistent when changing exception handling.
