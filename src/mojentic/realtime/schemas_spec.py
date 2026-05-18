from mojentic.realtime.schemas import parse_server_event


class DescribeParseServerEvent:
    class DescribeKnownEvents:
        def should_validate_session_created(self):
            raw = {"type": "session.created", "session": {"id": "sess_123"}}

            parsed = parse_server_event(raw)

            assert parsed["type"] == "session.created"
            assert parsed["session"]["id"] == "sess_123"

        def should_preserve_unknown_fields(self):
            raw = {
                "type": "response.audio.delta",
                "response_id": "resp_1",
                "item_id": "item_1",
                "delta": "AAAA",
                "future_field": 42,
            }

            parsed = parse_server_event(raw)

            assert parsed["future_field"] == 42

        def should_normalize_output_audio_delta_alias(self):
            raw = {
                "type": "response.output_audio.delta",
                "response_id": "resp_1",
                "delta": "AAAA",
            }

            parsed = parse_server_event(raw)

            assert parsed["type"] == "response.output_audio.delta"
            assert parsed["delta"] == "AAAA"

    class DescribeUnknownEvents:
        def should_pass_through_unknown_types(self):
            raw = {"type": "session.something_new", "payload": True}

            parsed = parse_server_event(raw)

            assert parsed == {"type": "session.something_new", "payload": True}

        def should_return_unknown_marker_for_typeless_payload(self):
            parsed = parse_server_event({"no_type": True})

            assert parsed == {"type": "unknown"}

        def should_fall_back_to_raw_when_known_type_fails_validation(self):
            raw = {"type": "response.created"}  # missing 'response'

            parsed = parse_server_event(raw)

            assert parsed == raw
