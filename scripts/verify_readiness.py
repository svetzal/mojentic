"""Verify an installed candidate through public APIs and controlled HTTP.

Run outside the checkout, passing its absolute path solely to read contracts.
"""

import hashlib
import json
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from pydantic import BaseModel

import mojentic
from mojentic.llm import CompletionConfig, LLMBroker, LLMMessage
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.models import MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.model_context_window import effective_context_window
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy
from mojentic.llm.tools.llm_tool import LLMTool


@contextmanager
def endpoint(replies: list[tuple[int, bytes]]):
    """Serve finite fixture responses and capture exact request bodies."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.respond()

        def do_POST(self) -> None:
            self.respond()

        def respond(self) -> None:
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            requests.append((self.command, self.path, raw))
            status, body = replies[len(requests) - 1]
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=lambda: server.serve_forever(0.01))
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", requests
        finally:
            server.shutdown()
            thread.join()


class Answer(BaseModel):
    answer: str


class Count(LLMTool):
    def __init__(self, result: str) -> None:
        self.calls: list[int] = []
        self.result = result

    def run(self, value: int) -> str:
        self.calls.append(value)
        return self.result

    @property
    def descriptor(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "count",
                "description": "Count",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                },
            },
        }


def verify_metadata(root: Path) -> None:
    contract = json.loads(
        (root / "src/mojentic/llm/contracts/context_window_v1.json").read_text()
    )
    for case in contract["cases"]:
        with endpoint([(case["status"], case["response"].encode())]) as (
            host,
            requests,
        ):
            gateway = (
                OllamaGateway(host=host)
                if case["provider"] == "ollama"
                else OMLXGateway(host=host)
            )
            expected = case["expected"]
            try:
                result = gateway.get_model_context_window(case["model"])
            except (ValueError, httpx.HTTPStatusError) as error:
                assert "error" in expected
                if isinstance(error, httpx.HTTPStatusError):
                    assert error.response.status_code == expected["error"][1]
                else:
                    assert expected["error"] == "invalid_response"
            else:
                assert "error" not in expected
                assert (
                    result.model_dump(exclude_none=True) if result else None
                ) == expected["window"]
                if result:
                    assert effective_context_window(
                        result, CompletionConfig(num_ctx=1024)
                    ) == min(result.max_context_tokens, 1024)
            actual = requests[0]
            assert actual[:2] == (case["request"]["method"], case["request"]["path"])
            assert (json.loads(actual[2]) if actual[2] else None) == case["request"][
                "body"
            ]
    gateway = OpenAIGateway(api_key="local", base_url="http://127.0.0.1:1/v1")
    assert gateway.get_model_context_window("gpt-4o").field == "registry"
    assert gateway.get_model_context_window("unknown-model") is None
    print("metadata: all provider cases and exact requests passed")


def verify_reasoning(root: Path) -> None:
    contract = json.loads(
        (
            root
            / "src/mojentic/llm/gateways/fixtures/contracts/native_reasoning_v1.json"
        ).read_text()
    )
    for provider, factory in (("ollama", OllamaGateway), ("omlx", OMLXGateway)):
        field = "thinking" if provider == "ollama" else "reasoning_content"
        message = {
            "role": "assistant",
            "content": '{"answer":"answer"}',
            field: contract["reasoning"],
        }

        def reply(value: dict, provider: str = provider) -> bytes:
            envelope = (
                {"message": value, "done": True, "done_reason": "stop"}
                if provider == "ollama"
                else {"choices": [{"message": value, "finish_reason": "stop"}]}
            )
            return json.dumps(envelope).encode()

        for case in contract["controls"]:
            with endpoint([(200, reply(message))]) as (host, requests):
                response = factory(host=host).complete(
                    model="arbitrary-alias",
                    messages=[LLMMessage(content="question")],
                    object_model=Answer,
                    config=CompletionConfig(reasoning_effort=case["effort"]),
                )
                assert response.object == Answer(answer="answer")
                assert response.thinking == contract["reasoning"]
                body = json.loads(requests[0][2])
                assert {
                    key: body[key]
                    for key in ("think", "enable_thinking", "reasoning_effort")
                    if key in body
                } == case[provider]
                controls = body.get("options", body)
                assert (
                    not {"temperature", "max_tokens", "num_predict", "num_ctx"}
                    & controls.keys()
                )
        call = json.loads(json.dumps(contract["tool_call"]))
        if provider == "ollama":
            call["function"]["arguments"] = json.loads(call["function"]["arguments"])
        first = message | {"content": contract["visible"], "tool_calls": [call]}
        with endpoint([(200, reply(first)), (200, reply(message))]) as (host, requests):
            tool = Count(contract["tool_result"])
            result = LLMBroker(model="alias", gateway=factory(host=host)).generate(
                [LLMMessage(content="question")],
                tools=[tool],
                config=CompletionConfig(retain_reasoning=True),
            )
            assert result == '{"answer":"answer"}'
            assert tool.calls == [7]
            body = json.loads(requests[1][2])
            assistant = body["messages"][1]
            assert assistant[field] == contract["reasoning"]
            assert assistant["content"] == contract["visible"]
            function = assistant["tool_calls"][0]["function"]
            assert function["name"] == call["function"]["name"]
            arguments = function["arguments"]
            assert (arguments if provider == "ollama" else json.loads(arguments)) == {
                "value": 7
            }
            assert body["messages"][2]["content"] == json.dumps(contract["tool_result"])
            if provider == "omlx":
                assert body["chat_template_kwargs"] == {"preserve_thinking": True}
                assert body["messages"][2]["tool_call_id"] == call["id"]
    print(
        "reasoning: distinct controls, structured output, native tool continuation passed"
    )


def verify_recovery() -> None:
    success = json.dumps(
        {
            "id": "msg-test",
            "type": "message",
            "role": "assistant",
            "model": "claude-test",
            "content": [{"type": "text", "text": "answer"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 2, "output_tokens": 3},
        }
    ).encode()
    messages = [
        LLMMessage(content="hello"),
        LLMMessage(role=MessageRole.Assistant, content="prior"),
        LLMMessage(content="continue"),
    ]
    for policy in (None, RecoveryPolicy(max_attempts=2, base_delay=0)):
        replies = (
            [(200, success)] if policy is None else [(503, b"busy"), (200, success)]
        )
        with endpoint(replies) as (host, requests):
            gateway = AnthropicGateway(
                api_key="local", base_url=host, recovery_policy=policy
            )
            response = gateway.complete(
                model="claude-test",
                messages=messages,
                config=CompletionConfig(max_tokens=17, temperature=0),
            )
            assert response.content == "answer"
            expected = {
                "model": "claude-test",
                "system": None,
                "messages": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "prior"},
                    {"role": "user", "content": "continue"},
                ],
                "max_tokens": 17,
                "temperature": 0,
            }
            assert json.loads(requests[0][2]) == expected
            assert all(request == requests[0] for request in requests)
            if policy:
                assert response.recovery_report.history[0].http_status == 503
                assert response.recovery_report.identity.wire_attempt == 2
    with endpoint([(401, b"private")]) as (host, requests):
        gateway = AnthropicGateway(
            api_key="local",
            base_url=host,
            recovery_policy=RecoveryPolicy(max_attempts=2),
        )
        try:
            gateway.complete(model="claude-test", messages=messages)
        except RecoveryError as error:
            assert error.report.history[0].http_status == 401
            assert "private" not in str(error)
        else:
            raise AssertionError("Permanent HTTP error was not raised")
        assert len(requests) == 1
    print(
        "recovery/history: SDK success, admitted byte-identical retry and permanent failure passed"
    )


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    installed = Path(mojentic.__file__).resolve()
    assert not installed.is_relative_to(root)
    assert not Path.cwd().is_relative_to(root)
    print("installed:", installed)
    for path in [
        root / "src/mojentic/llm/contracts/context_window_v1.json",
        *sorted((root / "src/mojentic/llm/gateways/fixtures/contracts").glob("*.json")),
    ]:
        print("contract:", path.name, hashlib.sha256(path.read_bytes()).hexdigest())
    verify_metadata(root)
    verify_reasoning(root)
    verify_recovery()


if __name__ == "__main__":
    main()
