"""Policy arithmetic and safe model invariants independent of transport."""

import pytest
from pydantic import ValidationError

from mojentic.llm.recovery import Failure, Identity, RecoveryPolicy, parse_retry_after


class DescribeRecoveryPolicy:
    @pytest.mark.parametrize(
        "attempt,expected", [(1, 0.5), (2, 1), (3, 1.5), (100000, 1.5)]
    )
    def should_bound_exponential_jitter_without_overflow(self, attempt, expected):
        policy = RecoveryPolicy(
            base_delay=1, delay_ceiling=3, jitter=lambda ceiling: ceiling / 2
        )
        failure = Failure(
            operation="ordinary",
            category="http",
            reason="transient",
            identity=Identity(
                logical_request_id="logical", attempt_id="attempt", wire_attempt=attempt
            ),
        )

        assert policy.delay(failure) == expected

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_attempts": 0},
            {"max_attempts": -1},
            {"max_attempts": True},
            {"max_attempts": 1.5},
            {"base_delay": -1},
            {"delay_ceiling": float("inf")},
            {"budget": -1},
            {"deadline": float("nan")},
        ],
    )
    def should_reject_invalid_recovery_policy(self, kwargs):
        with pytest.raises(ValidationError):
            RecoveryPolicy(**kwargs)

    @pytest.mark.parametrize(
        "value,state,delay",
        [
            (None, "absent", None),
            ("-1", "invalid", None),
            ("1.5", "invalid", None),
            ("secret", "invalid", None),
            ("0", "seconds", 0),
            ("12", "seconds", 12),
            ("Thursday, 01-Jan-70 00:16:42 GMT", "date", 2),
            ("Thu Jan  1 00:16:42 1970", "date", 2),
            ("Thu, 01 Jan 1970 00:16:39 GMT", "date", 0),
            ("9" * 5000, "invalid", None),
        ],
    )
    def should_parse_retry_after_without_serializing_untrusted_text(
        self, value, state, delay
    ):
        parsed = parse_retry_after(value, 1000)

        assert parsed.state == state
        assert parsed.delay == delay
        assert "secret" not in parsed.model_dump_json()

    def should_keep_callback_secrets_out_of_policy_serialization_and_repr(self):
        async def admission(context):
            return "reject"

        policy = RecoveryPolicy(admission=admission)

        assert "admission" not in policy.model_dump()
        assert "admission" not in repr(policy)
        with pytest.raises(ValidationError):
            policy.max_attempts = 2
