# Runbook: Exchange-Rate Provider Failure

## Scope

Use this runbook when Frankfurter requests time out, fail, become unusually
slow, or return invalid data.

The currently mounted conversion and rates services call the provider
directly. They do not use the repository's cache helper or persisted rate
models as a fallback. A provider failure therefore causes affected requests
to fail rather than serve cached values. The app's liveness endpoint does not
check provider availability.

## Triage

1. Confirm which operations and currency pairs are affected.
2. Inspect application logs for provider operation, status, and exception
   details; correlate using available request metadata.
3. Check provider reachability, DNS, TLS, and network egress from the
   application environment.
4. Verify `EXCHANGE_API`, `EXCHANGE_TIMEOUT_SECONDS`, and
   `EXCHANGE_MAX_RETRIES` in the deployed configuration.
5. Review recent deployments and provider status information.
6. Avoid high-volume manual probes, which can increase upstream load.

## Mitigation

- The provider client defaults to a five-second request timeout and two
  retries after the initial request.
- Retries apply to timeout, connection, HTTP 429, and HTTP 5xx failures.
  Backoff is bounded exponential delay without jitter.
- Do not increase retry counts during an incident without considering
  amplification across concurrent API requests.
- No automatic provider failover or cached-rate fallback is currently
  configured. Do not present an old rate as current or substitute a hard-coded
  rate.
- If operationally necessary, reduce or temporarily restrict incoming
  traffic using the deployment's existing traffic controls. Do not claim that
  the app's optional rate-limit middleware is active until it is mounted.

## Recovery

1. Confirm the provider is responding with a low-volume request.
2. Verify that a representative API request succeeds and returns the expected
   base, observation date, and rate.
3. Monitor request failure rates and latency through the deployment's
   available logs and monitoring.
4. Close the incident after provider-dependent requests remain healthy.

## Escalation and follow-up

Escalate persistent DNS, TLS, network, or provider response failures to the
responsible infrastructure or provider contact. Record the impact, time
window, root cause, and recovery steps. Consider adding tested cache fallback,
request coalescing, jittered retries, and provider-health monitoring before
relying on the API for availability-sensitive use cases.
