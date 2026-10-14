# Runbook: Exchange-Rate Freshness

## Scope

Use this runbook when consumers report old observation dates or when rate-age
monitoring indicates data is older than expected.

The repository has an in-memory cache helper and a freshness-policy helper,
but the mounted rates service currently requests rates directly from the
provider and does not attach the cache or freshness policy. Consequently, the
`RATE_CACHE_TTL_SECONDS` and `MAX_STALE_RATE_AGE_SECONDS` settings do not
currently control the public conversion or rate endpoints. The API returns
the observation date supplied by the provider.

## Triage

1. Record the endpoint, base and target currencies, and returned
   `rate_date`.
2. Compare that date with a low-volume request directly to the configured
   provider.
3. Determine whether the date difference is expected because of a weekend,
   market holiday, or provider publication schedule.
4. Check the active `EXCHANGE_API` and recent application/provider failures.
5. Check recent deployments, system clocks, and timezone handling if the
   returned date regressed unexpectedly.

There is no currently mounted application rate-refresh worker or cache
fallback to inspect. Do not flush Redis or report a Redis cache failure as the
cause of old data unless the deployment has separately connected that
integration.

## Response

- If the provider itself reports a recent business-day observation, explain
  that `rate_date` is an observation date rather than a fetch timestamp.
- If the provider reports a date older than expected, follow the
  [provider failure runbook](provider-outage.md) and contact the provider when
  appropriate.
- Do not manually edit rate records or substitute a hard-coded rate.
- Do not increase stale-age thresholds to suppress an alert; those settings
  are not currently applied to the public route behavior.

## Recovery and follow-up

Confirm the provider's returned date and rate through the public endpoint
after recovery. Record the incident and affected pairs. Before presenting a
cache/freshness policy as active, integrate it into the rates service, expose
the effective observation/fetch metadata to clients, and add tests for fresh,
stale, and expired data as well as provider outage behavior.
