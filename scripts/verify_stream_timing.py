"""Fresh-wheel public API verification against py-stream-first-token-v1.

Run with a fresh uv environment containing the built wheel, outside this checkout.
The fixture directory is read as contract input; no source modules are imported.
"""

import asyncio
import hashlib
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import mojentic
from mojentic.llm import ChatSession, CompletionConfig, LLMBroker, LLMMessage
from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.stream_events import StreamError, StreamErrorReason
from mojentic.llm.recovery import RecoveryPolicy
from mojentic.llm.recovery_stream import StreamMetrics


async def recovery(
    gateway: OllamaGateway | OpenAIGateway | OMLXGateway,
) -> StreamMetrics:
    events = [
        event
        async for event in gateway.complete_stream_with_recovery(
            model="gpt-4o", messages=[LLMMessage(content="hello")]
        )
    ]
    assert events[-1].kind == "completed"
    return events[-1].metrics


def main() -> None:
    if sys.argv[1] == "--source-id":
        root = Path(__file__).resolve().parents[1]
        files = sorted(
            path
            for path in (root / "src").rglob("*")
            if path.suffix in {".py", ".json", ".sse"}
        ) + [root / "pyproject.toml", root / "uv.lock", Path(__file__).resolve()]
        manifest = "".join(
            f"{path.relative_to(root)} {hashlib.sha256(path.read_bytes()).hexdigest()}\n"
            for path in files
        )
        print(hashlib.sha256(manifest.encode()).hexdigest())
        return
    contract_path = Path(sys.argv[1]).resolve()
    contract = json.loads(contract_path.read_text())
    checkout = contract_path.parents[6]
    assert not Path(mojentic.__file__).resolve().is_relative_to(checkout / "src")
    print("installed:", mojentic.__file__)
    print(
        "contract:",
        contract["id"],
        hashlib.sha256(contract_path.read_bytes()).hexdigest(),
    )
    case = next(case for case in contract["cases"] if case["name"] == "empty-success")
    state = {"body": b""}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Length", str(len(state["body"])))
            self.end_headers()
            time.sleep(0.025)
            self.wfile.write(state["body"])

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"http://127.0.0.1:{server.server_port}"
    factories = {
        "ollama": lambda: OllamaGateway(host=host),
        "omlx": lambda: OMLXGateway(host=host),
        "openai": lambda: OpenAIGateway(api_key="loopback", base_url=host + "/v1"),
    }
    try:
        for provider, factory in factories.items():
            protocol = "ollama" if provider == "ollama" else "openai"
            state["body"] = case[protocol].encode()
            gateway = factory()
            events = list(
                gateway.complete_stream_events(
                    "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                )
            )
            assert events[-1].metadata.first_token_kind is None
            assert events[-1].metadata.time_to_first_token_ms is None
            assert events[-1].metadata.request_duration_ms >= 15
            # Reuse request-fidelity-v1's supported success envelopes. OpenAI
            # recovery does not accept oMLX-specific keepalive frames.
            fidelity = json.loads(
                (contract_path.parent / "request_fidelity_v1.json").read_text()
            )
            frame = fidelity["responses"][f"{protocol}-events"]
            if provider == "ollama":
                frames = [json.loads(line) for line in frame.splitlines()]
                for item in frames:
                    item["message"]["role"] = "assistant"
                frame = "".join(json.dumps(item) + "\n" for item in frames)
            state["body"] = frame.encode()
            broker = LLMBroker(model="gpt-4o", gateway=gateway)
            assert "".join(ChatSession(broker).send_stream("hello")) == "answer"
            assert broker.last_stream_metrics.first_token_kind == "content"
            assert broker.last_stream_metrics.time_to_first_token_ms >= 15
            gateway.recovery_policy = RecoveryPolicy()
            metrics = asyncio.run(recovery(gateway))
            assert metrics.first_token_kind == "content"
            assert 15 <= metrics.time_to_first_token_ms <= metrics.request_duration_ms
            print(provider, "events/session/recovery: passed")
            if provider != "ollama":
                state["body"] = b'data: {"choices":1}\n\n'
                events = list(
                    gateway.complete_stream_events(
                        "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                    )
                )
                assert len(events) == 1
                assert isinstance(events[0], StreamError)
                assert events[0].reason == StreamErrorReason.INVALID_STREAM_EVENT
                assert events[0].metadata.request_duration_ms >= 15
                assert events[0].metadata.time_to_first_token_ms is None
            if provider == "ollama":
                state["body"] = (
                    b'{"model":"test","message":{"role":"assistant","content":"answer"},'
                    b'"done":false,"eval_duration":123}\n'
                )
                expected = {"eval_duration": 123}
            else:
                state["body"] = (
                    b'data: {"choices":[{"index":0,"delta":{"content":"answer"}}],'
                    b'"usage":{"prompt_tokens":2,"completion_tokens":3,"total_tokens":5}}\n\n'
                )
                expected = {
                    "usage": {
                        "prompt_tokens": 2,
                        "completion_tokens": 3,
                        "total_tokens": 5,
                    }
                }
            for route in ("legacy", "broker", "session"):
                gateway = factory()
                gateway.recovery_policy = RecoveryPolicy()
                broker = LLMBroker(model="gpt-4o", gateway=gateway)
                session = ChatSession(broker)
                routes = {
                    "legacy": (
                        gateway,
                        lambda: gateway.complete_stream(
                            model="gpt-4o", messages=[LLMMessage(content="hello")]
                        ),
                    ),
                    "broker": (
                        broker,
                        lambda: broker.generate_stream([LLMMessage(content="hello")]),
                    ),
                    "session": (session, lambda: session.send_stream("hello")),
                }
                owner, create_stream = routes[route]
                stream = create_stream()
                stream.close()
                assert getattr(owner, "last_stream_metrics", None) is None
                stream = create_stream()
                chunk = next(stream)
                assert (chunk.content if route == "legacy" else chunk) == "answer"
                stream.close()
                metrics = owner.last_stream_metrics
                assert metrics.first_token_kind == "content"
                assert (
                    15 <= metrics.time_to_first_token_ms <= metrics.request_duration_ms
                )
                assert metrics.metadata == expected
            print(provider, "malformed events/public recovery close: passed")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
