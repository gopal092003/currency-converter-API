# Security

This document distinguishes security controls present in the codebase from
controls enforced by the currently mounted API. A helper module or setting
alone does not secure a route.

## Current runtime status

- The public conversion, rates, currencies, and liveness routes currently do
  not require API-key authentication.
- API-key management routes and rate-limit middleware exist in the repository
  but are not mounted by `app/main.py` or the API router.
- `API_KEY_AUTH_ENABLED`, `RATE_LIMIT_ENABLED`, and `USAGE_QUOTA_ENABLED` do
  not currently activate enforcement on public routes.
- The app enables CORS only when `CORS_ALLOWED_ORIGINS` is non-empty. It does
  not allow credentials, and its configured allow-header list does not include
  `X-API-Key`.
- TLS termination, secret storage, network restrictions, and production
  access control are deployment responsibilities.
- The project is licensed under the MIT License; this is unrelated to runtime
  security.

Do not treat the repository's optional authentication and rate-limiting
modules as production protections until they are wired into the application
and exercised by end-to-end tests.

## API-key design in supporting modules

The API-key service is designed to store a lookup prefix and keyed digest
rather than the raw key. Key material uses a cryptographically secure random
source; the full key is returned when created or rotated. The
`API_KEY_PEPPER` setting is required when `API_KEY_AUTH_ENABLED=true` and must
be supplied as a high-entropy secret outside source control.

The management router relies on a validated API key in request state. Because
the current application does not install the authentication layer or include
that router, those endpoints are not presently available through the API.
Before exposing them, wire trusted caller authentication, owner scoping,
transactional rotation/revocation, and tests into the application.

## Deployment guidance

Before deploying to a public environment:

1. Terminate client traffic over HTTPS at a trusted edge or in the application
   deployment.
2. Store credentials in a secret manager or protected deployment variables;
   never commit `.env` files or production credentials.
3. Set `APP_ENV=production` and keep `DEBUG=false`. Interactive docs and
   OpenAPI are disabled in that environment.
4. Configure CORS with explicit trusted origins only when browser clients
   need it. CORS is not authentication.
5. Restrict network access to database, Redis, and monitoring services.
6. Run dependency and container security checks and review their findings.
7. Confirm that actual routes enforce intended authentication, authorization,
   rate limits, and quota policy before describing those controls as active.

## Logging and data handling

Never log raw API keys, authorization headers, passwords, peppers, database
connection strings, or secret configuration. Avoid logging request bodies
unless they are explicitly reviewed and redacted. Use bounded-cardinality
metric labels; do not label metrics with raw credentials, request IDs, or
arbitrary client input.

## Incident response

For suspected credential exposure:

1. Revoke or rotate the affected credential using the control plane that
   currently owns it.
2. Do not copy the secret into tickets, chat, or incident notes.
3. Review access logs and usage records for suspicious activity.
4. Rotate dependent credentials if they may also have been exposed.
5. Record the impact, mitigation, and follow-up controls.

Once API-key enforcement is connected to the app, add and maintain tests for
malformed keys, expiry, revocation, rotation, ownership isolation, secret
redaction, and authentication bypass attempts.
