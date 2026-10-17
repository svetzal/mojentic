import hashlib
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.request_fidelity_spec import assert_controls, reply
from mojentic.llm.model_context_window import (
    ModelContextWindow,
    effective_context_window,
)

CONTRACT_PATH = Path(__file__).parents[1] / "contracts/context_window_v1.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text())


@contextmanager
def metadata_server(replies, raw_requests=None):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if raw_requests is not None:
                raw_requests.append(body)
            requests.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "body": json.loads(body) if body else None,
                    "authorization": self.headers.get("Authorization"),
                }
            )
            status, data = replies[len(requests) - 1]
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(
            target=lambda: server.serve_forever(poll_interval=0.01)
        )
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", requests
        finally:
            server.shutdown()
            thread.join()


class DescribeContextWindow:
    def should_select_exact_model_through_authenticated_http(self):
        case = next(c for c in CONTRACT["cases"] if c["name"] == "exact-selection")
        with metadata_server([(case["status"], case["response"].encode())]) as (
            host,
            requests,
        ):
            gateway = OMLXGateway(host=host, api_key="test-key")

            result = gateway.get_model_context_window(case["model"])

        assert result.model_dump(exclude_none=True) == case["expected"]["window"]
        assert requests == [case["request"] | {"authorization": "Bearer test-key"}]


def gateway_for_case(case, host):
    key = "" if case.get("without_api_key") else "test-key"
    if case["provider"] == "ollama":
        return OllamaGateway(host=host, headers={"Authorization": "Bearer " + key})
    return OMLXGateway(host=host, api_key=key)


def contract_result(case):
    expected = case["expected"]
    if "error" not in expected:
        window = expected["window"]
        return ModelContextWindow(**window) if window is not None else None
    if expected["error"] == "invalid_response":
        raise ValueError("Invalid metadata")
    request = httpx.Request(
        case["request"]["method"], "http://contract" + case["request"]["path"]
    )
    response = httpx.Response(expected["error"][1], request=request)
    response.raise_for_status()


def verify_semantics(case, discover):
    expected = case["expected"]
    if "error" not in expected:
        result = discover(case["model"])
        assert (
            result.model_dump(exclude_none=True) if result is not None else None
        ) == expected["window"]
    elif expected["error"] == "invalid_response":
        with pytest.raises(ValueError):
            discover(case["model"])
    else:
        with pytest.raises(httpx.HTTPStatusError) as raised:
            discover(case["model"])
        assert raised.value.response.status_code == expected["error"][1]


class DescribeContextWindowContract:
    def should_pin_the_shared_executable_contract_identity(self):
        assert CONTRACT["version"] == "context-window-v1"
        assert hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest() == (
            "cfeee4702c0dd3b18e02fbd0c8bad82ae58ee1ca7eadcfd21683479ba24f3dc4"
        )

    @pytest.mark.parametrize(
        "case", CONTRACT["cases"], ids=lambda c: c["provider"] + "-" + c["name"]
    )
    def should_verify_provider_semantics_and_exact_http_request(self, case):
        with metadata_server([(case["status"], case["response"].encode())]) as (
            host,
            requests,
        ):
            gateway = gateway_for_case(case, host)

            verify_semantics(case, gateway.get_model_context_window)

        auth = None if case.get("without_api_key") else "Bearer test-key"
        assert requests == [case["request"] | {"authorization": auth}]

    @pytest.mark.parametrize(
        "case", CONTRACT["cases"], ids=lambda c: c["provider"] + "-" + c["name"]
    )
    def should_derive_gateway_double_from_verified_provider_case(self, case, mocker):
        gateway = mocker.Mock(spec=LLMGateway)
        gateway.get_model_context_window.side_effect = lambda model: contract_result(
            case
        )

        verify_semantics(case, gateway.get_model_context_window)

        gateway.get_model_context_window.assert_called_once_with(case["model"])

    @pytest.mark.parametrize(
        "case", CONTRACT["registry_cases"], ids=lambda c: c["model"]
    )
    def should_lookup_only_exact_registry_entries_without_http(self, case):
        with metadata_server([]) as (host, requests):
            gateway = OpenAIGateway(api_key="test-key", base_url=host + "/v1")

            result = gateway.get_model_context_window(case["model"])

        assert (
            result.model_dump(exclude_none=True) if result is not None else None
        ) == case["window"]
        assert requests == []

    @pytest.mark.parametrize("case", CONTRACT["effective_cases"])
    def should_apply_helper_precedence_and_clamping(self, case):
        window = (
            ModelContextWindow(**case["window"]) if case["window"] is not None else None
        )

        result = effective_context_window(
            window, CompletionConfig(num_ctx=case["num_ctx"])
        )

        assert result == case["expected"]

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    def should_distinguish_transport_failure(self, provider):
        with socket.socket() as endpoint:
            endpoint.bind(("127.0.0.1", 0))
            host = f"http://127.0.0.1:{endpoint.getsockname()[1]}"
            gateway = gateway_for_case({"provider": provider}, host)

            with pytest.raises(httpx.TransportError):
                gateway.get_model_context_window("exact-model")

    def should_return_not_advertised_for_unsupported_gateway(self):
        assert LLMGateway().get_model_context_window("unknown") is None
        assert (
            AnthropicGateway(api_key="test-key").get_model_context_window("unknown")
            is None
        )

    @pytest.mark.parametrize(
        "case", CONTRACT["cases"], ids=lambda c: c["provider"] + "-" + c["name"]
    )
    @pytest.mark.parametrize(
        "controls", [{}, {"num_ctx": 8192, "temperature": 0, "max_tokens": 17}]
    )
    def should_leave_same_model_completion_request_unchanged_after_discovery(
        self, case, controls
    ):
        provider = case["provider"]
        success = reply(provider, "complete")
        raw_requests = []
        replies = [
            (200, success),
            (case["status"], case["response"].encode()),
            (200, success),
        ]
        with metadata_server(replies, raw_requests) as (host, requests):
            gateway = gateway_for_case(case, host)
            args = {
                "model": case["model"],
                "messages": [LLMMessage(content="hello")],
                "config": CompletionConfig(**controls),
            }

            before = gateway.complete(**args)
            verify_semantics(case, gateway.get_model_context_window)
            after = gateway.complete(**args)

        assert before.content == after.content == "answer"
        assert raw_requests[0] == raw_requests[-1]
        assert requests[0] == requests[-1]
        assert requests[0]["body"]["model"] == case["model"]
        assert_controls(requests[0]["body"], provider, controls)
        assert len(requests) == 3
        auth = None if case.get("without_api_key") else "Bearer test-key"
        assert requests[1] == case["request"] | {"authorization": auth}

    @pytest.mark.parametrize("model", ["gpt-5.4", "o1-custom"])
    def should_preserve_registry_completion_semantics_after_discovery(self, model):
        success = reply("openai", "complete")
        raw_requests = []
        with metadata_server([(200, success), (200, success)], raw_requests) as (
            host,
            requests,
        ):
            gateway = OpenAIGateway(api_key="test-key", base_url=host + "/v1")
            args = {
                "model": model,
                "messages": [LLMMessage(content="hello")],
                "config": CompletionConfig(max_tokens=17),
            }
            capabilities = gateway.model_registry.get_model_capabilities(model)

            before = gateway.complete(**args)
            gateway.get_model_context_window(model)
            after = gateway.complete(**args)

        assert before.content == after.content == "answer"
        assert requests[0] == requests[1]
        assert requests[0]["body"]["model"] == model
        assert requests[0]["body"][capabilities.get_token_limit_param()] == 17
        assert len(requests) == 2
        assert [(request["method"], request["path"]) for request in requests] == [
            ("POST", "/v1/chat/completions"),
        ] * 2
        assert raw_requests[0] == raw_requests[1]
