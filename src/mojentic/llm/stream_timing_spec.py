"""Deterministic timing semantics supplement the production HTTP specifications."""

import pytest

from mojentic.llm.stream_timing import StreamClock


class DescribeStreamClock:
    @pytest.mark.parametrize(
        "frame,kind",
        [
            ({"message": {"content": "answer"}}, "content"),
            ({"message": {"thinking": "thought", "content": "answer"}}, "thinking"),
            (
                {
                    "choices": [
                        {"delta": {"tool_calls": [{"function": {"arguments": "{"}}]}}
                    ]
                },
                "tool_call",
            ),
        ],
    )
    def should_measure_exact_first_token_and_duration_with_injected_monotonic_clock(
        self, frame, kind
    ):
        ticks = iter([10.0, 10.025, 10.175])
        clock = StreamClock(clock=lambda: next(ticks))

        clock.dispatch()
        clock.observe({"model": "keepalive", "message": {"content": "ignored"}})
        clock.observe({"choices": [{"delta": {}}]})
        clock.dispatch()
        clock.observe(frame)
        clock.observe({"message": {"content": "later"}})
        evidence = clock.evidence()

        assert evidence["first_token_kind"] == kind
        assert evidence["time_to_first_token_ms"] == pytest.approx(25)
        assert evidence["request_duration_ms"] == pytest.approx(175)

    def should_report_empty_completion_without_inventing_a_first_token(self):
        ticks = iter([2.0, 2.25])
        clock = StreamClock(clock=lambda: next(ticks))

        clock.dispatch()
        clock.observe({"done": True})

        assert clock.evidence() == {"request_duration_ms": 250}

    def should_not_read_the_clock_before_dispatch(self):
        ticks = iter([])
        clock = StreamClock(clock=lambda: next(ticks))

        assert clock.evidence() == {}
