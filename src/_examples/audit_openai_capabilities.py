"""
Audit script that probes OpenAI models for their actual capabilities
and compares against our hardcoded model registry.

Usage:
    OPENAI_API_KEY=sk-... python src/_examples/audit_openai_capabilities.py
    OPENAI_API_KEY=sk-... python src/_examples/audit_openai_capabilities.py --cheap

The --cheap flag skips expensive model families and infers capabilities
from their -mini variants instead.
"""

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from openai import OpenAI, BadRequestError, APIError, RateLimitError

from mojentic.llm.gateways.openai_model_registry import (
    OpenAIModelRegistry, ModelType
)

# Models that use different API endpoints (not chat-compatible)
SKIP_PREFIXES = [
    "tts-", "whisper-", "dall-e-", "text-moderation-",
    "davinci-", "babbage-", "canary-",
    "codex-", "computer-",
]
SKIP_CONTAINS = [
    "-realtime-", "-transcribe", "-tts",
]

# Expensive model families to skip in --cheap mode
EXPENSIVE_FAMILIES = [
    "o1-pro", "o3-pro", "o3-deep-research", "o4-mini-deep-research",
    "gpt-5-codex",
]

# 1x1 white PNG for vision testing
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "nGP4z8BQDwAEgAF/pooBPQAAAABJRU5ErkJggg=="
)

MINIMAL_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    }
}


def should_skip_model(model_id: str) -> bool:
    """Check if a model should be skipped (non-chat endpoint)."""
    model_lower = model_id.lower()
    for prefix in SKIP_PREFIXES:
        if model_lower.startswith(prefix):
            return True
    for pattern in SKIP_CONTAINS:
        if pattern in model_lower:
            return True
    return False


def is_chat_model_candidate(model_id: str) -> bool:
    """Check if a model is a candidate for chat API probing."""
    model_lower = model_id.lower()
    chat_patterns = [
        "gpt-3.5", "gpt-4", "gpt-5",
        "o1", "o3", "o4",
        "chatgpt",
    ]
    return any(p in model_lower for p in chat_patterns)


def is_embedding_model(model_id: str) -> bool:
    """Check if a model is an embedding model."""
    return "embedding" in model_id.lower()


def is_expensive(model_id: str) -> bool:
    """Check if a model is in an expensive family."""
    model_lower = model_id.lower()
    return any(family in model_lower for family in EXPENSIVE_FAMILIES)


def rate_limited_call(func, *args, **kwargs):
    """Call a function with rate limit handling and backoff."""
    max_retries = 3
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except RateLimitError:
            if attempt < max_retries - 1:
                print(f"    Rate limited, waiting {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise


def probe_basic_chat(client: OpenAI, model_id: str) -> dict:
    """Test basic chat completion and determine token parameter name."""
    result = {"works": False, "uses_max_tokens": None, "error": None}

    # Try with max_tokens first (standard chat models)
    try:
        response = rate_limited_call(
            client.chat.completions.create,
            model=model_id,
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=10,
        )
        result["works"] = True
        result["uses_max_tokens"] = True
        return result
    except BadRequestError as e:
        error_msg = str(e).lower()
        if "max_completion_tokens" in error_msg:
            # Reasoning model - retry with max_completion_tokens
            try:
                response = rate_limited_call(
                    client.chat.completions.create,
                    model=model_id,
                    messages=[{"role": "user", "content": "Say hi"}],
                    max_completion_tokens=10,
                )
                result["works"] = True
                result["uses_max_tokens"] = False
                return result
            except (BadRequestError, APIError) as e2:
                result["error"] = str(e2)
                return result
        else:
            result["error"] = str(e)
            return result
    except APIError as e:
        result["error"] = str(e)
        return result


def probe_tool_calling(client: OpenAI, model_id: str, uses_max_tokens: bool) -> dict:
    """Test if a model supports tool calling."""
    result = {"supports_tools": False, "error": None}

    token_kwargs = {}
    if uses_max_tokens:
        token_kwargs["max_tokens"] = 10
    else:
        token_kwargs["max_completion_tokens"] = 100

    try:
        response = rate_limited_call(
            client.chat.completions.create,
            model=model_id,
            messages=[{"role": "user", "content": "What is the weather in London?"}],
            tools=[MINIMAL_TOOL],
            **token_kwargs,
        )
        result["supports_tools"] = True
        return result
    except BadRequestError as e:
        error_msg = str(e).lower()
        if "tool" in error_msg or "function" in error_msg:
            result["supports_tools"] = False
        else:
            result["error"] = str(e)
            result["supports_tools"] = False
        return result
    except APIError as e:
        result["error"] = str(e)
        return result


def probe_streaming(client: OpenAI, model_id: str, uses_max_tokens: bool) -> dict:
    """Test if a model supports streaming."""
    result = {"supports_streaming": False, "error": None}

    token_kwargs = {}
    if uses_max_tokens:
        token_kwargs["max_tokens"] = 10
    else:
        token_kwargs["max_completion_tokens"] = 50

    try:
        stream = rate_limited_call(
            client.chat.completions.create,
            model=model_id,
            messages=[{"role": "user", "content": "Say hi"}],
            stream=True,
            **token_kwargs,
        )
        # Consume the stream to verify it works
        for chunk in stream:
            pass
        result["supports_streaming"] = True
        return result
    except BadRequestError as e:
        error_msg = str(e).lower()
        if "stream" in error_msg:
            result["supports_streaming"] = False
        else:
            result["error"] = str(e)
            result["supports_streaming"] = False
        return result
    except APIError as e:
        result["error"] = str(e)
        return result


def probe_vision(client: OpenAI, model_id: str, uses_max_tokens: bool) -> dict:
    """Test if a model supports vision (image input)."""
    result = {"supports_vision": False, "error": None}

    token_kwargs = {}
    if uses_max_tokens:
        token_kwargs["max_tokens"] = 10
    else:
        token_kwargs["max_completion_tokens"] = 50

    try:
        response = rate_limited_call(
            client.chat.completions.create,
            model=model_id,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in one word."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{TINY_PNG_B64}",
                            "detail": "low"
                        }
                    }
                ]
            }],
            **token_kwargs,
        )
        result["supports_vision"] = True
        return result
    except BadRequestError as e:
        error_msg = str(e).lower()
        if "image" in error_msg or "vision" in error_msg or "content" in error_msg:
            result["supports_vision"] = False
        else:
            result["error"] = str(e)
            result["supports_vision"] = False
        return result
    except APIError as e:
        result["error"] = str(e)
        return result


def probe_temperature(client: OpenAI, model_id: str, uses_max_tokens: bool) -> dict:
    """Test which temperature values a model supports."""
    result = {"supported_temperatures": None, "error": None}
    test_temps = [0.0, 0.5, 1.0]
    supported = []

    token_kwargs = {}
    if uses_max_tokens:
        token_kwargs["max_tokens"] = 5
    else:
        token_kwargs["max_completion_tokens"] = 20

    for temp in test_temps:
        try:
            response = rate_limited_call(
                client.chat.completions.create,
                model=model_id,
                messages=[{"role": "user", "content": "Say ok"}],
                temperature=temp,
                **token_kwargs,
            )
            supported.append(temp)
        except BadRequestError as e:
            error_msg = str(e).lower()
            if "temperature" in error_msg:
                pass  # This temperature not supported
            else:
                result["error"] = str(e)
                break
        except APIError as e:
            result["error"] = str(e)
            break
        time.sleep(0.3)

    if len(supported) == len(test_temps):
        result["supported_temperatures"] = None  # All supported
    elif len(supported) == 0:
        result["supported_temperatures"] = []  # None supported
    else:
        result["supported_temperatures"] = supported

    return result


def probe_embedding(client: OpenAI, model_id: str) -> dict:
    """Test if a model works as an embedding model."""
    result = {"is_embedding": False, "error": None}
    try:
        response = rate_limited_call(
            client.embeddings.create,
            model=model_id,
            input="test",
        )
        result["is_embedding"] = True
        return result
    except (BadRequestError, APIError) as e:
        result["error"] = str(e)
        return result


def probe_model(client: OpenAI, model_id: str, cheap_mode: bool = False) -> Optional[dict]:
    """Run all capability probes against a single model."""
    if should_skip_model(model_id):
        return None

    if cheap_mode and is_expensive(model_id):
        print(f"  Skipping {model_id} (expensive, --cheap mode)")
        return None

    # Handle embedding models separately
    if is_embedding_model(model_id):
        print(f"  Probing {model_id} (embedding)...")
        embed_result = probe_embedding(client, model_id)
        return {
            "model_type": "embedding" if embed_result["is_embedding"] else "unknown",
            "supports_tools": False,
            "supports_streaming": False,
            "supports_vision": False,
            "supported_temperatures": None,
            "uses_max_tokens": None,
            "errors": [embed_result["error"]] if embed_result["error"] else []
        }

    if not is_chat_model_candidate(model_id):
        return None

    print(f"  Probing {model_id}...")

    # Test 1: Basic chat
    basic = probe_basic_chat(client, model_id)
    if not basic["works"]:
        print(f"    Basic chat failed: {basic['error']}")
        return {
            "model_type": "unknown",
            "supports_tools": False,
            "supports_streaming": False,
            "supports_vision": False,
            "supported_temperatures": None,
            "uses_max_tokens": None,
            "errors": [basic["error"]]
        }

    uses_max_tokens = basic["uses_max_tokens"]
    model_type = "chat" if uses_max_tokens else "reasoning"
    time.sleep(0.5)

    # Test 2: Tool calling
    tools_result = probe_tool_calling(client, model_id, uses_max_tokens)
    time.sleep(0.5)

    # Test 3: Streaming
    stream_result = probe_streaming(client, model_id, uses_max_tokens)
    time.sleep(0.5)

    # Test 4: Vision
    vision_result = probe_vision(client, model_id, uses_max_tokens)
    time.sleep(0.5)

    # Test 5: Temperature
    temp_result = probe_temperature(client, model_id, uses_max_tokens)

    errors = [r["error"] for r in [tools_result, stream_result, vision_result, temp_result]
              if r.get("error")]

    return {
        "model_type": model_type,
        "supports_tools": tools_result["supports_tools"],
        "supports_streaming": stream_result["supports_streaming"],
        "supports_vision": vision_result["supports_vision"],
        "supported_temperatures": temp_result["supported_temperatures"],
        "uses_max_tokens": uses_max_tokens,
        "errors": errors if errors else []
    }


def compare_with_registry(probed_models: dict, registry: OpenAIModelRegistry) -> dict:
    """Compare probed results with current registry."""
    registered_models = set(registry.get_registered_models())
    probed_model_names = set(probed_models.keys())

    # Find new models (in API but not registry)
    new_models = sorted(probed_model_names - registered_models)

    # Find removed models (in registry but not in any API model)
    removed_models = sorted(registered_models - probed_model_names)

    # Find capability changes for models in both sets
    capability_changes = {}
    for model_name in sorted(probed_model_names & registered_models):
        probed = probed_models[model_name]
        registered_caps = registry.get_model_capabilities(model_name)

        changes = {}

        # Compare model type
        reg_type = registered_caps.model_type.value
        if probed["model_type"] != reg_type and probed["model_type"] != "unknown":
            changes["model_type"] = {"was": reg_type, "now": probed["model_type"]}

        # Compare tools support
        if probed["supports_tools"] != registered_caps.supports_tools:
            changes["supports_tools"] = {
                "was": registered_caps.supports_tools,
                "now": probed["supports_tools"]
            }

        # Compare streaming support
        if probed["supports_streaming"] != registered_caps.supports_streaming:
            changes["supports_streaming"] = {
                "was": registered_caps.supports_streaming,
                "now": probed["supports_streaming"]
            }

        # Compare vision support
        if probed["supports_vision"] != registered_caps.supports_vision:
            changes["supports_vision"] = {
                "was": registered_caps.supports_vision,
                "now": probed["supports_vision"]
            }

        # Compare temperature support
        reg_temps = registered_caps.supported_temperatures
        probed_temps = probed["supported_temperatures"]
        if reg_temps != probed_temps:
            changes["supported_temperatures"] = {
                "was": reg_temps,
                "now": probed_temps
            }

        if changes:
            capability_changes[model_name] = changes

    return {
        "new_models": new_models,
        "removed_models": removed_models,
        "capability_changes": capability_changes
    }


def main():
    cheap_mode = "--cheap" in sys.argv

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print("Fetching available OpenAI models...")
    all_models = sorted([m.id for m in client.models.list()])
    print(f"Found {len(all_models)} models total")

    # Separate into categories
    models_to_probe = []
    models_skipped = []

    for model_id in all_models:
        if should_skip_model(model_id):
            models_skipped.append(model_id)
        elif is_chat_model_candidate(model_id) or is_embedding_model(model_id):
            models_to_probe.append(model_id)
        else:
            models_skipped.append(model_id)

    print(f"\nWill probe {len(models_to_probe)} models, skipping {len(models_skipped)}")
    if cheap_mode:
        print("Running in --cheap mode (skipping expensive model families)")

    # Probe each model
    probed_results = {}
    for model_id in models_to_probe:
        result = probe_model(client, model_id, cheap_mode)
        if result is not None:
            probed_results[model_id] = result
        time.sleep(0.5)  # Rate limit between models

    # Compare with registry
    print("\nComparing with current registry...")
    registry = OpenAIModelRegistry()
    comparison = compare_with_registry(probed_results, registry)

    # Build report
    report = {
        "audit_date": datetime.now(timezone.utc).isoformat(),
        "cheap_mode": cheap_mode,
        "api_models_available": all_models,
        "models_skipped": models_skipped,
        "models_probed": probed_results,
        "comparison": comparison
    }

    # Write report
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "openai_model_audit_report.json"
    )
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nReport written to: {report_path}")

    # Print summary
    print("\n=== AUDIT SUMMARY ===")
    print(f"Models in API: {len(all_models)}")
    print(f"Models probed: {len(probed_results)}")
    print(f"Models skipped: {len(models_skipped)}")

    if comparison["new_models"]:
        print(f"\nNew models (not in registry): {len(comparison['new_models'])}")
        for m in comparison["new_models"]:
            caps = probed_results.get(m, {})
            print(f"  + {m} (type={caps.get('model_type', '?')}, "
                  f"tools={caps.get('supports_tools', '?')}, "
                  f"stream={caps.get('supports_streaming', '?')})")

    if comparison["removed_models"]:
        print(f"\nRemoved models (in registry, not in API): {len(comparison['removed_models'])}")
        for m in comparison["removed_models"]:
            print(f"  - {m}")

    if comparison["capability_changes"]:
        print(f"\nCapability changes: {len(comparison['capability_changes'])}")
        for model, changes in comparison["capability_changes"].items():
            print(f"  ~ {model}:")
            for field, diff in changes.items():
                print(f"      {field}: {diff['was']} -> {diff['now']}")

    if not comparison["new_models"] and not comparison["removed_models"] and not comparison["capability_changes"]:
        print("\nNo discrepancies found - registry is up to date!")


if __name__ == "__main__":
    main()
