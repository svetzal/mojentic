"""recovery-capabilities-v1: executable public capability contract."""

import json

import pytest
from pydantic import ValidationError

from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import Capabilities


@pytest.fixture(params=["ollama", "omlx", "openai", "anthropic"])
def endpoint_contract(request):
    return {
        "ollama": (
            OllamaGateway,
            {},
            "POST /api/chat",
            "https://docs.ollama.com/api/chat",
            "Chat documents generation, streaming and model keep_alive",
            True,
        ),
        "omlx": (
            OMLXGateway,
            {},
            "POST /v1/chat/completions",
            "https://github.com/jundot/omlx/blob/main/README.md#api-compatibility",
            "API Compatibility lists chat completions and model/admin endpoints",
            True,
        ),
        "openai": (
            OpenAIGateway,
            {"api_key": "contract-test"},
            "POST /v1/chat/completions",
            "https://developers.openai.com/api/reference/resources/chat",
            "Chat documents creation and stored completions; Responses and Batch are separate APIs",
            True,
        ),
        "anthropic": (
            AnthropicGateway,
            {"api_key": "contract-test"},
            "POST /v1/messages",
            "https://platform.claude.com/docs/en/api/messages/create",
            "Messages documents request creation and streaming",
            False,
        ),
    }[request.param]


@pytest.fixture
def capabilities(endpoint_contract):
    gateway, arguments, *_ = endpoint_contract
    return gateway(**arguments).recovery_capabilities()


def assert_evidence(capabilities, endpoint_contract, name, basis):
    _, _, endpoint, source, *_ = endpoint_contract
    assert capabilities.evidence[name].model_dump() == {
        "endpoint": endpoint,
        "source": source,
        "inspected_on": "2026-10-17",
        "basis": basis,
    }


class DescribeRecoveryCapabilitiesV1:
    def should_report_local_cancellation_with_endpoint_evidence(
        self, capabilities, endpoint_contract
    ):
        assert capabilities.local_cancellation == "unknown"
        assert_evidence(
            capabilities,
            endpoint_contract,
            "local_cancellation",
            endpoint_contract[4] + ", but is silent on local HTTP cancellation. "
            "RecoveryCall cancels local work; that implementation does not establish "
            "a documented endpoint guarantee.",
        )

    def should_report_remote_cancellation_with_endpoint_evidence(
        self, capabilities, endpoint_contract
    ):
        assert capabilities.remote_cancellation == "unsupported"
        assert_evidence(
            capabilities,
            endpoint_contract,
            "remote_cancellation",
            endpoint_contract[4] + "; no remote cancellation facility for an in-flight "
            "request is described on this endpoint. Closing HTTP is not remote cancellation.",
        )

    def should_report_request_status_with_endpoint_evidence(
        self, capabilities, endpoint_contract
    ):
        assert capabilities.request_status == "unsupported"
        assert_evidence(
            capabilities,
            endpoint_contract,
            "request_status",
            endpoint_contract[4]
            + "; no status lookup for an in-flight request is described. "
            "Stored outputs and model activity are not request execution status.",
        )

    def should_report_idempotency_with_endpoint_evidence(
        self, capabilities, endpoint_contract
    ):
        assert capabilities.idempotency == "unsupported"
        assert_evidence(
            capabilities,
            endpoint_contract,
            "idempotency",
            endpoint_contract[4]
            + "; no inference idempotency key or deduplication guarantee "
            "is described for this endpoint. Local correlation IDs do not deduplicate inference.",
        )

    def should_report_exact_attempt_termination_with_endpoint_evidence(
        self, capabilities, endpoint_contract
    ):
        assert capabilities.inference_termination == "unknown"
        assert_evidence(
            capabilities,
            endpoint_contract,
            "inference_termination",
            endpoint_contract[4]
            + "; no evidence establishes termination of this exact "
            "attempt. A disconnect, model unload or aggregate activity is insufficient.",
        )

    def should_preserve_legacy_access_and_serialized_values(
        self, capabilities, endpoint_contract
    ):
        legacy = {
            "ordinary_recovery": True,
            "structured_recovery": True,
            "streaming_recovery": endpoint_contract[5],
            "remote_cancellation": "unsupported",
            "request_status": "unsupported",
            "inference_termination": "unknown",
            "idempotency": "unsupported",
            "exact_wire_capture": True,
        }

        assert (
            capabilities.model_dump(exclude={"local_cancellation", "evidence"})
            == legacy
        )
        assert {name: getattr(capabilities, name) for name in legacy} == legacy
        restored = type(capabilities).model_validate(legacy)
        assert restored.model_dump(exclude={"local_cancellation", "evidence"}) == legacy
        assert restored.local_cancellation == "unknown"
        assert restored.evidence == {}

    def should_accept_old_anthropic_unsupported_structured_projection(self):
        legacy = {"structured_recovery": False, "streaming_recovery": False}

        restored = Capabilities.model_validate(legacy)

        assert not restored.structured_recovery
        assert not restored.streaming_recovery

    def should_round_trip_new_evidence_in_python_and_json(self, capabilities):
        assert (
            type(capabilities).model_validate(capabilities.model_dump()) == capabilities
        )
        assert (
            type(capabilities).model_validate_json(capabilities.model_dump_json())
            == capabilities
        )
        assert json.loads(capabilities.model_dump_json()) == capabilities.model_dump()

    @pytest.mark.parametrize(
        "field",
        [
            "local_cancellation",
            "remote_cancellation",
            "request_status",
            "idempotency",
            "inference_termination",
        ],
    )
    def should_reject_invalid_capability_values(self, capabilities, field):
        data = capabilities.model_dump() | {field: "confirmed"}

        with pytest.raises(ValidationError):
            type(capabilities).model_validate(data)

    def should_reject_claims_of_exact_attempt_termination(self, capabilities):
        data = capabilities.model_dump() | {"inference_termination": "supported"}

        with pytest.raises(ValidationError):
            type(capabilities).model_validate(data)

    def should_report_anthropic_local_cancellation_without_claiming_remote_support(
        self,
    ):
        capabilities = AnthropicGateway(api_key="contract-test").recovery_capabilities()

        assert capabilities.local_cancellation == "unknown"
        assert capabilities.remote_cancellation == "unsupported"
        assert capabilities.inference_termination == "unknown"
        evidence = capabilities.evidence["local_cancellation"]
        assert evidence.endpoint == "POST /v1/messages"
        assert (
            evidence.source == "https://platform.claude.com/docs/en/api/messages/create"
        )
        assert evidence.inspected_on == "2026-10-17"
        assert evidence.basis == (
            "Messages documents request creation and streaming, but is silent on local "
            "HTTP cancellation. RecoveryCall cancels local work; that implementation "
            "does not establish a documented endpoint guarantee."
        )
