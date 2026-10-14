
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

logger = logging.getLogger("app.alerts")


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AlertDefinition:
    name: str
    severity: AlertSeverity
    description: str


ALERT_DEFINITIONS: dict[str, AlertDefinition] = {
    "provider_failure": AlertDefinition(
        name="provider_failure",
        severity=AlertSeverity.ERROR,
        description="Exchange-rate provider request failed.",
    ),
    "rate_limit_storage_failure": AlertDefinition(
        name="rate_limit_storage_failure",
        severity=AlertSeverity.CRITICAL,
        description="Rate-limit storage is unavailable.",
    ),
    "database_unavailable": AlertDefinition(
        name="database_unavailable",
        severity=AlertSeverity.CRITICAL,
        description="The application database is unavailable.",
    ),
    "provider_latency_high": AlertDefinition(
        name="provider_latency_high",
        severity=AlertSeverity.WARNING,
        description="Exchange-rate provider latency is above its threshold.",
    ),
    "quota_exhausted": AlertDefinition(
        name="quota_exhausted",
        severity=AlertSeverity.WARNING,
        description="An API key has exhausted its monthly quota.",
    ),
    "rate_limit_exceeded": AlertDefinition(
        name="rate_limit_exceeded",
        severity=AlertSeverity.INFO,
        description="A request was rejected by rate limiting.",
    ),
}


class AlertSink:
    """Interface for future integrations with external alerting systems."""

    def emit(
        self,
        *,
        definition: AlertDefinition,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError


class LoggingAlertSink(AlertSink):
    """Emit structured alert records through Python logging."""

    def emit(
        self,
        *,
        definition: AlertDefinition,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        safe_attributes = sanitize_alert_attributes(attributes or {})

        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }[definition.severity]

        log_method(
            "operational_alert",
            extra={
                "alert_name": definition.name,
                "alert_severity": definition.severity.value,
                "alert_description": definition.description,
                "alert_attributes": safe_attributes,
            },
        )


def sanitize_alert_attributes(
    attributes: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove common secrets and high-risk values from alert attributes."""
    forbidden_fragments = (
        "authorization",
        "api_key",
        "apikey",
        "secret",
        "password",
        "token",
        "credential",
        "connection_string",
    )

    safe: dict[str, Any] = {}

    for key, value in attributes.items():
        normalized_key = key.lower().replace("-", "_")

        if any(fragment in normalized_key for fragment in forbidden_fragments):
            continue

        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        else:
            safe[key] = str(type(value).__name__)

    return safe


_default_sink: AlertSink = LoggingAlertSink()


def emit_alert(
    name: str,
    *,
    attributes: Mapping[str, Any] | None = None,
    sink: AlertSink | None = None,
) -> None:
    """Emit a registered alert. Unknown alert names are rejected."""
    definition = ALERT_DEFINITIONS.get(name)

    if definition is None:
        raise ValueError(f"Unknown alert definition: {name}")

    (sink or _default_sink).emit(
        definition=definition,
        attributes=attributes,
    )
