
from __future__ import annotations

import pytest

import asyncio

from app.modules.rate_limiting.service import RateLimitService
from app.modules.rate_limiting.storage import InMemoryRateLimitStorage

from app.modules.rate_limiting.policies import (
    CONVERSION_POLICY,
    DEFAULT_IP_POLICY,
    DEFAULT_API_KEY_POLICY,
    READ_POLICY,
    RateLimitPolicy,
    RateLimitScope,
    select_endpoint_policy,
    RateLimitPolicy,
    RateLimitScope,
)
from app.modules.rate_limiting.service import RateLimitService
from app.modules.rate_limiting.storage import InMemoryRateLimitStorage


@pytest.mark.asyncio
async def test_first_request_is_allowed():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)

    decision = await service.check(
        policy=RateLimitPolicy(
            name="test",
            limit=3,
            window_seconds=60,
        ),
        identity="client-a",
    )

    assert decision.allowed is True
    assert decision.limit == 3
    assert decision.remaining == 2
    assert decision.retry_after_seconds == 0


@pytest.mark.asyncio
async def test_request_at_limit_is_allowed():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy("test", limit=2, window_seconds=60)

    first = await service.check(policy=policy, identity="client-a")
    second = await service.check(policy=policy, identity="client-a")

    assert first.allowed is True
    assert second.allowed is True
    assert second.remaining == 0


@pytest.mark.asyncio
async def test_request_above_limit_is_rejected():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy("test", limit=1, window_seconds=60)

    await service.check(policy=policy, identity="client-a")
    rejected = await service.check(
        policy=policy,
        identity="client-a",
    )

    assert rejected.allowed is False
    assert rejected.remaining == 0
    assert rejected.retry_after_seconds >= 1


@pytest.mark.asyncio
async def test_rejected_requests_remain_rejected_in_same_window():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy("test", limit=1, window_seconds=60)

    decisions = [
        await service.check(policy=policy, identity="client-a")
        for _ in range(4)
    ]

    assert [decision.allowed for decision in decisions] == [
        True,
        False,
        False,
        False,
    ]


@pytest.mark.asyncio
async def test_different_identities_have_independent_counters():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy("test", limit=1, window_seconds=60)

    first_a = await service.check(policy=policy, identity="client-a")
    second_a = await service.check(policy=policy, identity="client-a")
    first_b = await service.check(policy=policy, identity="client-b")

    assert first_a.allowed is True
    assert second_a.allowed is False
    assert first_b.allowed is True


@pytest.mark.asyncio
async def test_different_policies_have_independent_counters():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)

    strict = RateLimitPolicy("strict", limit=1, window_seconds=60)
    relaxed = RateLimitPolicy("relaxed", limit=10, window_seconds=60)

    await service.check(policy=strict, identity="client-a")
    rejected = await service.check(
        policy=strict,
        identity="client-a",
    )
    allowed = await service.check(
        policy=relaxed,
        identity="client-a",
    )

    assert rejected.allowed is False
    assert allowed.allowed is True


@pytest.mark.asyncio
async def test_empty_identity_is_rejected():
    service = RateLimitService(InMemoryRateLimitStorage())
    policy = RateLimitPolicy("test", limit=1, window_seconds=60)

    with pytest.raises(ValueError, match="identity"):
        await service.check(policy=policy, identity="")


def test_invalid_policies_are_rejected():
    with pytest.raises(ValueError):
        RateLimitPolicy("invalid", limit=0, window_seconds=60)

    with pytest.raises(ValueError):
        RateLimitPolicy("invalid", limit=10, window_seconds=0)

    with pytest.raises(ValueError):
        RateLimitPolicy("", limit=10, window_seconds=60)


def test_endpoint_policy_selection():
    assert select_endpoint_policy("/api/v1/convert").name == (
        CONVERSION_POLICY.name
    )
    assert select_endpoint_policy("/api/v1/convert/").name == (
        CONVERSION_POLICY.name
    )
    assert select_endpoint_policy("/api/v1/convert/preview").name == (
        CONVERSION_POLICY.name
    )
    assert select_endpoint_policy("/api/v1/rates/latest").name == (
        READ_POLICY.name
    )
    assert select_endpoint_policy("/api/v1/currencies").name == (
        READ_POLICY.name
    )


def test_unknown_endpoint_uses_default_policy():
    selected = select_endpoint_policy("/api/v1/unknown")

    assert selected == DEFAULT_API_KEY_POLICY


def test_default_policies_have_expected_scopes():
    assert DEFAULT_IP_POLICY.scope == RateLimitScope.IP
    assert DEFAULT_API_KEY_POLICY.scope == RateLimitScope.API_KEY
    assert CONVERSION_POLICY.scope == RateLimitScope.API_KEY


@pytest.mark.asyncio
async def test_ip_limit_is_checked_before_endpoint_limit():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)

    ip_policy = RateLimitPolicy(
        "ip-test",
        limit=1,
        window_seconds=60,
        scope=RateLimitScope.IP,
    )
    endpoint_policy = RateLimitPolicy(
        "endpoint-test",
        limit=100,
        window_seconds=60,
        scope=RateLimitScope.API_KEY,
    )

    first, first_ip = await service.check_request(
        ip_identity="ip-a",
        endpoint_identity="key-a",
        endpoint_policy=endpoint_policy,
        ip_policy=ip_policy,
    )
    second, second_ip = await service.check_request(
        ip_identity="ip-a",
        endpoint_identity="key-b",
        endpoint_policy=endpoint_policy,
        ip_policy=ip_policy,
    )

@pytest.mark.asyncio
async def test_exact_limit_boundary():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy(
        name="boundary",
        limit=5,
        window_seconds=60,
        scope=RateLimitScope.API_KEY,
    )

    decisions = [
        await service.check(policy=policy, identity="client-a")
        for _ in range(5)
    ]

    assert all(item.allowed for item in decisions)
    assert decisions[-1].remaining == 0


@pytest.mark.asyncio
async def test_first_request_after_limit_is_rejected():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy(
        name="boundary",
        limit=5,
        window_seconds=60,
    )

    for _ in range(5):
        await service.check(policy=policy, identity="client-a")

    rejected = await service.check(
        policy=policy,
        identity="client-a",
    )

    assert rejected.allowed is False
    assert rejected.remaining == 0
    assert rejected.retry_after_seconds >= 1


@pytest.mark.asyncio
async def test_counter_resets_after_window_expiry(monkeypatch):
    # Control monotonic time to test expiry without sleeping.
    clock = {"now": 100.0}
    monkeypatch.setattr(
        "app.modules.rate_limiting.storage.time.monotonic",
        lambda: clock["now"],
    )

    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy(
        name="expiry",
        limit=1,
        window_seconds=10,
    )

    first = await service.check(policy=policy, identity="client-a")
    rejected = await service.check(policy=policy, identity="client-a")

    assert first.allowed is True
    assert rejected.allowed is False

    clock["now"] = 110.0

    after_expiry = await service.check(
        policy=policy,
        identity="client-a",
    )

    assert after_expiry.allowed is True
    assert after_expiry.remaining == 0


@pytest.mark.asyncio
async def test_concurrent_requests_never_exceed_limit():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    limit = 20

    policy = RateLimitPolicy(
        name="concurrency",
        limit=limit,
        window_seconds=60,
    )

    decisions = await asyncio.gather(
        *(
            service.check(policy=policy, identity="same-client")
            for _ in range(100)
        )
    )

    accepted = sum(item.allowed for item in decisions)
    rejected = sum(not item.allowed for item in decisions)

    assert accepted == limit
    assert rejected == 100 - limit
    assert sum(item.remaining == 0 for item in decisions) >= 1


@pytest.mark.asyncio
async def test_concurrent_clients_have_independent_capacity():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy(
        name="concurrent-clients",
        limit=3,
        window_seconds=60,
    )

    async def send_batch(identity: str):
        return await asyncio.gather(
            *(
                service.check(policy=policy, identity=identity)
                for _ in range(10)
            )
        )

    results_a, results_b = await asyncio.gather(
        send_batch("client-a"),
        send_batch("client-b"),
    )

    assert sum(item.allowed for item in results_a) == 3
    assert sum(item.allowed for item in results_b) == 3


@pytest.mark.asyncio
async def test_concurrent_policy_counters_do_not_interfere():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)

    strict_policy = RateLimitPolicy(
        name="strict",
        limit=2,
        window_seconds=60,
    )
    relaxed_policy = RateLimitPolicy(
        name="relaxed",
        limit=8,
        window_seconds=60,
    )

    strict_results, relaxed_results = await asyncio.gather(
        *[
            asyncio.gather(
                *(
                    service.check(
                        policy=strict_policy,
                        identity="same-client",
                    )
                    for _ in range(10)
                )
            ),
            asyncio.gather(
                *(
                    service.check(
                        policy=relaxed_policy,
                        identity="same-client",
                    )
                    for _ in range(10)
                )
            ),
        ]
    )

    assert sum(item.allowed for item in strict_results) == 2
    assert sum(item.allowed for item in relaxed_results) == 8


@pytest.mark.asyncio
async def test_remaining_capacity_never_becomes_negative():
    storage = InMemoryRateLimitStorage()
    service = RateLimitService(storage)
    policy = RateLimitPolicy(
        name="remaining",
        limit=2,
        window_seconds=60,
    )

    results = await asyncio.gather(
        *(
            service.check(policy=policy, identity="client-a")
            for _ in range(20)
        )
    )

    assert all(item.remaining >= 0 for item in results)
    assert all(item.remaining <= policy.limit for item in results)


@pytest.mark.asyncio
async def test_separate_storage_instances_do_not_share_counters():
    # Documents the in-memory backend limitation: each process/storage
    # instance maintains independent counters.
    storage_a = InMemoryRateLimitStorage()
    storage_b = InMemoryRateLimitStorage()
    policy = RateLimitPolicy(
        name="instance-isolation",
        limit=1,
        window_seconds=60,
    )

    first_a = await RateLimitService(storage_a).check(
        policy=policy,
        identity="client-a",
    )
    first_b = await RateLimitService(storage_b).check(
        policy=policy,
        identity="client-a",
    )

    assert first_a.allowed is True
    assert first_b.allowed is True
    assert first.allowed is True
    assert first_ip is not None
    assert second.allowed is False
    assert second.policy_name == "ip-test"
    assert second_ip is None
