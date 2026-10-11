import json

import pytest
from pydantic import BaseModel, field_validator

from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import frame, scripted_http
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
from mojentic.llm.llm_broker import LLMBroker


class Result(BaseModel):
    answer: str

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value):
        raise TypeError("validator programming defect")


class DescribeStructuredBoundary:
    def should_propagate_validator_defects_through_the_public_broker(self, mocker):
        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = [1]
        with scripted_http([(200, {}, frame('{"answer":"ok"}'))]) as (host, requests):
            gateway = OllamaGateway(
                host=host, headers={"Authorization": "Bearer broker-proof"}
            )
            broker = LLMBroker(model="test", gateway=gateway, tokenizer=tokenizer)

            with pytest.raises(TypeError, match="validator programming defect"):
                broker.generate_object(
                    [LLMMessage(role=MessageRole.User, content="test")], Result
                )

            assert len(requests) == 1
            assert requests[0][0] == "/api/chat"
            assert requests[0][2]["authorization"] == "Bearer broker-proof"
            assert json.loads(requests[0][1]) == {
                "model": "test",
                "messages": [{"role": "user", "content": "test"}],
                "tools": [],
                "stream": False,
                "format": Result.model_json_schema(),
                "options": {"temperature": 1.0, "num_ctx": 32768, "num_predict": 16384},
            }

    def should_propagate_validator_defects_with_exact_authenticated_request(self):
        with scripted_http([(200, {}, frame('{"answer":"ok"}'))]) as (host, requests):
            gateway = OllamaGateway(
                host=host, headers={"Authorization": "Bearer lint-proof"}
            )

            with pytest.raises(TypeError, match="validator programming defect"):
                gateway.complete(model="test", messages=[], object_model=Result)

            assert len(requests) == 1
            path, body, headers = requests[0]
            assert path == "/api/chat"
            assert headers["authorization"] == "Bearer lint-proof"
            assert json.loads(body) == {
                "model": "test",
                "messages": [],
                "tools": [],
                "stream": False,
                "format": {
                    "properties": {"answer": {"title": "Answer", "type": "string"}},
                    "required": ["answer"],
                    "title": "Result",
                    "type": "object",
                },
                "options": {"temperature": 1.0, "num_ctx": 32768},
            }
            assert body == (
                b'{"model":"test","stream":false,"options":'
                b'{"num_ctx":32768,"temperature":1.0},"format":'
                b'{"properties":{"answer":{"title":"Answer","type":"string"}},'
                b'"required":["answer"],"title":"Result","type":"object"},'
                b'"messages":[],"tools":[]}'
            )
