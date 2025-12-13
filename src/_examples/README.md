# Mojentic Python Examples

This directory contains example scripts demonstrating various features of the Mojentic Python library.

## Prerequisites

Before running these examples, ensure you have:

1. **Python installed** (version 3.11 or later)
2. **Ollama running locally** at `http://localhost:11434`
3. **At least one model pulled**, for example:
   ```bash
   ollama pull phi4:14b
   ollama pull qwen2.5:3b
   ```
4. **Dependencies installed**:
   ```bash
   pip install -e .
   ```

## Available Examples

### Level 1: Basic LLM Usage

#### `simple_llm.py`
Basic text generation with a local LLM model.
```bash
python src/_examples/simple_llm.py
```

#### `list_models.py`
List all available models from the Ollama gateway.
```bash
python src/_examples/list_models.py
```

#### `simple_structured.py`
Generate structured JSON output using Pydantic models.
```bash
python src/_examples/simple_structured.py
```

#### `simple_tool.py`
Use a single tool (DateResolver) with the LLM.
```bash
python src/_examples/simple_tool.py
```

### Level 2: Advanced LLM Features

#### `broker_examples.py`
Comprehensive demonstration of various broker features.
```bash
python src/_examples/broker_examples.py
```

#### `streaming.py`
Stream responses chunk-by-chunk with tool calling support.
```bash
python src/_examples/streaming.py
```

#### `chat_session.py`
Interactive chat session maintaining conversation history.
```bash
python src/_examples/chat_session.py
```

#### `chat_session_with_tool.py`
Chat session with access to tools.
```bash
python src/_examples/chat_session_with_tool.py
```

#### `image_analysis.py`
Analyze images using vision-capable models.
```bash
python src/_examples/image_analysis.py
```

#### `embeddings.py`
Generate vector embeddings for text.
```bash
python src/_examples/embeddings.py
```

### Level 3: Tool System Extensions

#### `file_tool.py`
Demonstrates file operations using the FileTool.
```bash
python src/_examples/file_tool.py
```

#### `coding_file_tool.py`
Advanced file operations for coding tasks.
```bash
python src/_examples/coding_file_tool.py
```

#### `broker_as_tool.py`
Wrap agents as tools for delegation patterns.
```bash
python src/_examples/broker_as_tool.py
```

#### `ephemeral_task_manager_example.py`
Task management using the TaskManager tool.
```bash
python src/_examples/ephemeral_task_manager_example.py
```

#### `tell_user_example.py`
Demonstrates the TellUser tool for agent-to-user communication.
```bash
python src/_examples/tell_user_example.py
```

#### `web_search.py` (if available)
Web search capabilities.

### Level 4: Tracing & Observability

#### `tracer_demo.py`
Demonstrates the event tracing system.
```bash
python src/_examples/tracer_demo.py
```

#### `tracer_qt_viewer.py`
Qt-based GUI viewer for tracer events (requires PySide6).
```bash
python src/_examples/tracer_qt_viewer.py
```

### Level 5: Agent System Basics

#### `async_llm_example.py`
Demonstrates asynchronous LLM agents.
```bash
python src/_examples/async_llm_example.py
```

#### `async_dispatcher_example.py`
Demonstrates the async event dispatcher and routing.
```bash
python src/_examples/async_dispatcher_example.py
```

### Level 6: Advanced Agent Patterns

#### `iterative_solver.py`
Multi-step problem solving agent.
```bash
python src/_examples/iterative_solver.py
```

#### `recursive_agent.py`
Self-recursive agent pattern.
```bash
python src/_examples/recursive_agent.py
```

#### `solver_chat_session.py`
Interactive chat with a solver agent.
```bash
python src/_examples/solver_chat_session.py
```

### Level 7: Multi-Agent & Specialized

#### `react.py`
Implementation of the ReAct (Reasoning + Acting) pattern.
```bash
python src/_examples/react.py
```

#### `working_memory.py`
Shared working memory between agents.
```bash
python src/_examples/working_memory.py
```

## Configuration

You can customize behavior using environment variables:

- `OLLAMA_HOST` - Ollama server URL (default: `http://localhost:11434`)
- `OPENAI_API_KEY` - API key for OpenAI gateway
