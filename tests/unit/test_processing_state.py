from datetime import timedelta

import pytest

from doclens_ai.services.processing import (
    ProcessingPolicy,
    default_processing_configuration_fingerprint,
)


def test_default_processing_configuration_fingerprint_is_stable() -> None:
    assert default_processing_configuration_fingerprint() == (
        "b4fbdf76ff96f38c4007380693a83fd82920645cd355f0f8abd80ee14d1ec9c3"
    )


def test_retry_backoff_is_exponential_and_bounded() -> None:
    policy = ProcessingPolicy(
        retry_base_delay=timedelta(seconds=10),
        retry_max_delay=timedelta(seconds=25),
    )

    assert policy.retry_delay(1) == timedelta(seconds=10)
    assert policy.retry_delay(2) == timedelta(seconds=20)
    assert policy.retry_delay(3) == timedelta(seconds=25)
    assert policy.retry_delay(100) == timedelta(seconds=25)


@pytest.mark.parametrize(
    "policy",
    [
        ProcessingPolicy(lease_duration=timedelta(seconds=1)),
        ProcessingPolicy(retry_base_delay=timedelta(seconds=1)),
    ],
)
def test_valid_processing_policy_is_accepted(policy: ProcessingPolicy) -> None:
    assert policy.lease_duration > timedelta(0)


def test_invalid_processing_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="lease duration"):
        ProcessingPolicy(lease_duration=timedelta(0))
    with pytest.raises(ValueError, match="retry max"):
        ProcessingPolicy(
            retry_base_delay=timedelta(seconds=2),
            retry_max_delay=timedelta(seconds=1),
        )
    with pytest.raises(ValueError, match="attempt count"):
        ProcessingPolicy().retry_delay(0)
