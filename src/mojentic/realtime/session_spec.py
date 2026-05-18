import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.runner import ToolRunContext
from mojentic.realtime.broker import RealtimeVoiceBroker
from mojentic.realtime.config import RealtimeVoiceConfig
from mojentic.realtime.events import (
    AssistantTextEvent,
    InterruptedEvent,
    SessionOpenedEvent,
    ToolBatchSubmittedEvent,
    ToolCallCompletedEvent,
)
from mojentic.realtime.gateway import RealtimeGatewaySession, RealtimeVoiceGateway
from mojentic.realtime.session import RealtimeSession, build_session_update


class _ScriptedGatewaySession(RealtimeGatewaySession):
    """A scripted in-memory gateway session for deterministic tests."""

    def __init__(self):
        self._session_id = "sess_test"
        self.sent: List[Dict[str, Any]] = []
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
        self._send_hook = None

    @property
    def session_id(self) -> str:
        return self._session_id

    async def send_event(self, event: Dict[str, Any]) -> None:
        self.sent.append(event)
        if self._send_hook is not None:
            await self._send_hook(event)

    def push(self, raw: Dict[str, Any]) -> None:
        self._queue.put_nowait(raw)

    def end(self) -> None:
        self._queue.put_nowait({"__eos__": True})

    async def events(self) -> AsyncIterator[Dict[str, Any]]:
        while True:
            item = await self._queue.get()
            if isinstance(item, dict) and item.get("__eos__"):
                return
            yield item

    async def close(self) -> None:
        self._closed = True
        self.end()

    def is_closed(self) -> bool:
        return self._closed


class _ScriptedGateway(RealtimeVoiceGateway):
    def __init__(self, session: _ScriptedGatewaySession):
        self._session = session

    async def open(self, model, config, correlation_id=None) -> RealtimeGatewaySession:
        return self._session


class _EchoTool(LLMTool):
    def __init__(self, name: str = "echo"):
        super().__init__()
        self._name = name

    def run(self, value: str = "") -> dict:
        return {"echo": value, "tool": self._name}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": self._name,
                "description": "Echo input",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": [],
                },
            },
        }


class _SlowAbortableTool(LLMTool):
    """Async tool that obeys the cancel_event in its ctx."""

    async def run(self, value: str = "x", delay_s: float = 0.5, ctx: Optional[ToolRunContext] = None) -> dict:
        # Bail early if the runner has already aborted this batch.
        if ctx is not None and ctx.cancelled:
            raise asyncio.CancelledError("ctx cancelled before start")
        try:
            await asyncio.sleep(delay_s)
        except asyncio.CancelledError:
            raise
        if ctx is not None and ctx.cancelled:
            raise asyncio.CancelledError("ctx cancelled during run")
        return {"value": value}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "slow",
                "description": "Sleeps then returns",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}, "delay_s": {"type": "number"}},
                    "required": [],
                },
            },
        }


class DescribeBuildSessionUpdate:
    def should_emit_realtime_ga_shape(self):
        config = RealtimeVoiceConfig(
            instructions="be brief",
            voice="alloy",
            modalities=["audio", "text"],
            max_response_output_tokens=128,
        )

        payload = build_session_update(config)

        assert payload["type"] == "session.update"
        session = payload["session"]
        assert session["type"] == "realtime"
        assert session["output_modalities"] == ["audio"]
        assert session["audio"]["output"]["voice"] == "alloy"
        assert session["max_output_tokens"] == 128
        assert session["instructions"] == "be brief"

    def should_include_function_tools(self):
        config = RealtimeVoiceConfig(tools=[_EchoTool("greet")])

        payload = build_session_update(config)

        assert len(payload["session"]["tools"]) == 1
        assert payload["session"]["tools"][0]["name"] == "greet"
        assert payload["session"]["tools"][0]["type"] == "function"


class DescribeRealtimeSessionTextRoundTrip:
    def should_emit_session_opened_immediately(self):
        async def run():
            gateway_session = _ScriptedGatewaySession()
            session = RealtimeSession(gateway_session, config=RealtimeVoiceConfig())
            gateway_session.end()
            collected = []
            async for ev in session.events():
                collected.append(ev)
            await session.close()
            return collected

        events = asyncio.run(run())

        assert isinstance(events[0], SessionOpenedEvent)
        assert events[0].session_id == "sess_test"

    def should_normalize_text_turn_into_kind_events(self):
        async def run():
            gateway_session = _ScriptedGatewaySession()
            session = RealtimeSession(gateway_session, config=RealtimeVoiceConfig())
            # Pre-load the entire scripted turn.
            gateway_session.push({"type": "response.created", "response": {"id": "resp_1"}})
            gateway_session.push({
                "type": "response.text.delta",
                "response_id": "resp_1",
                "delta": "Hello ",
            })
            gateway_session.push({
                "type": "response.text.delta",
                "response_id": "resp_1",
                "delta": "world.",
            })
            gateway_session.push({
                "type": "response.text.done",
                "response_id": "resp_1",
                "text": "Hello world.",
            })
            gateway_session.push({
                "type": "response.done",
                "response": {"id": "resp_1"},
            })
            gateway_session.end()
            kinds = []
            async for ev in session.events():
                kinds.append(ev.kind)
                if isinstance(ev, AssistantTextEvent):
                    pass
            await session.close()
            return kinds

        kinds = asyncio.run(run())

        assert kinds[0] == "session_opened"
        assert "assistant_turn_started" in kinds
        assert kinds.count("assistant_text_delta") == 2
        assert "assistant_text" in kinds
        assert "assistant_turn_completed" in kinds


class DescribeRealtimeSessionToolBatch:
    def should_dispatch_parallel_tools_and_submit_outputs(self):
        async def run():
            gateway_session = _ScriptedGatewaySession()
            session = RealtimeSession(
                gateway_session,
                config=RealtimeVoiceConfig(tools=[_EchoTool("alpha"), _EchoTool("beta")]),
            )
            # Script a turn that emits two tool calls before response.done.
            gateway_session.push({"type": "response.created", "response": {"id": "r1"}})
            gateway_session.push({
                "type": "response.output_item.added",
                "response_id": "r1",
                "item": {
                    "type": "function_call",
                    "call_id": "call_a",
                    "name": "alpha",
                    "id": "item_a",
                },
            })
            gateway_session.push({
                "type": "response.function_call_arguments.done",
                "response_id": "r1",
                "call_id": "call_a",
                "name": "alpha",
                "arguments": json.dumps({"value": "1"}),
            })
            gateway_session.push({
                "type": "response.output_item.added",
                "response_id": "r1",
                "item": {
                    "type": "function_call",
                    "call_id": "call_b",
                    "name": "beta",
                    "id": "item_b",
                },
            })
            gateway_session.push({
                "type": "response.function_call_arguments.done",
                "response_id": "r1",
                "call_id": "call_b",
                "name": "beta",
                "arguments": json.dumps({"value": "2"}),
            })
            gateway_session.push({"type": "response.done", "response": {"id": "r1"}})

            collected = []

            async def reader():
                async for ev in session.events():
                    collected.append(ev)
                    if isinstance(ev, ToolBatchSubmittedEvent):
                        gateway_session.end()
                        return

            reader_task = asyncio.create_task(reader())
            await asyncio.wait_for(reader_task, timeout=2.0)
            await session.close()
            return collected, gateway_session.sent

        events, sent = asyncio.run(run())

        completed_names = [e.name for e in events if isinstance(e, ToolCallCompletedEvent)]
        assert set(completed_names) == {"alpha", "beta"}

        # function_call_output events should be sent before response.create
        outputs = [s for s in sent if s.get("type") == "conversation.item.create"
                   and s.get("item", {}).get("type") == "function_call_output"]
        create_calls = [s for s in sent if s.get("type") == "response.create"]
        assert len(outputs) == 2
        assert len(create_calls) == 1
        # All outputs precede the response.create
        last_output_idx = max(sent.index(o) for o in outputs)
        assert last_output_idx < sent.index(create_calls[0])


class DescribeRealtimeSessionInterruption:
    def should_cancel_in_flight_tool_on_barge_in(self):
        async def run():
            gateway_session = _ScriptedGatewaySession()
            tool = _SlowAbortableTool()
            session = RealtimeSession(
                gateway_session,
                config=RealtimeVoiceConfig(tools=[tool], on_interrupt="drop"),
            )
            gateway_session.push({"type": "response.created", "response": {"id": "r1"}})
            gateway_session.push({
                "type": "response.output_item.added",
                "response_id": "r1",
                "item": {
                    "type": "function_call",
                    "call_id": "c1",
                    "name": "slow",
                    "id": "i1",
                },
            })
            gateway_session.push({
                "type": "response.function_call_arguments.done",
                "response_id": "r1",
                "call_id": "c1",
                "name": "slow",
                "arguments": json.dumps({"value": "x", "delay_s": 0.5}),
            })
            gateway_session.push({"type": "response.done", "response": {"id": "r1"}})

            interrupted_event = asyncio.Event()
            collected = []

            async def reader():
                async for ev in session.events():
                    collected.append(ev)
                    if isinstance(ev, InterruptedEvent):
                        interrupted_event.set()
                        return

            reader_task = asyncio.create_task(reader())

            # Give the tool batch a beat to start, then barge in.
            await asyncio.sleep(0.05)
            gateway_session.push({
                "type": "input_audio_buffer.speech_started",
                "audio_start_ms": 0,
            })
            await asyncio.wait_for(interrupted_event.wait(), timeout=2.0)
            gateway_session.end()
            await reader_task
            await session.close()
            return collected, gateway_session.sent

        events, sent = asyncio.run(run())

        # response.cancel should have been sent
        cancel_calls = [s for s in sent if s.get("type") == "response.cancel"]
        assert len(cancel_calls) == 1

        # 'drop' policy: no function_call_output should be submitted
        outputs = [s for s in sent if s.get("type") == "conversation.item.create"
                   and s.get("item", {}).get("type") == "function_call_output"]
        assert outputs == []

        # InterruptedEvent fired with barge_in reason
        interrupts = [e for e in events if isinstance(e, InterruptedEvent)]
        assert len(interrupts) == 1
        assert interrupts[0].reason == "barge_in"


class DescribeRealtimeVoiceBroker:
    def should_initialise_session_with_session_update(self):
        async def run():
            gateway_session = _ScriptedGatewaySession()
            gateway = _ScriptedGateway(gateway_session)
            broker = RealtimeVoiceBroker(
                "gpt-realtime",
                gateway,
                config=RealtimeVoiceConfig(instructions="hi", voice="verse"),
            )
            session = await broker.connect()
            gateway_session.end()
            await session.close()
            return gateway_session.sent

        sent = asyncio.run(run())

        assert sent[0]["type"] == "session.update"
        assert sent[0]["session"]["instructions"] == "hi"

    def should_merge_overrides_over_broker_config(self):
        async def run():
            gateway_session = _ScriptedGatewaySession()
            gateway = _ScriptedGateway(gateway_session)
            broker = RealtimeVoiceBroker(
                "gpt-realtime",
                gateway,
                config=RealtimeVoiceConfig(voice="verse", instructions="default"),
            )
            session = await broker.connect(overrides={"instructions": "override"})
            gateway_session.end()
            await session.close()
            return gateway_session.sent

        sent = asyncio.run(run())

        assert sent[0]["session"]["instructions"] == "override"
        # voice came from broker config, not overridden
        assert sent[0]["session"]["audio"]["output"]["voice"] == "verse"
