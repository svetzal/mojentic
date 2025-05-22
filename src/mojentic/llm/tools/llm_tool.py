import json
from typing import Any, Dict, Optional

from mojentic.tracer.tracer_system import TracerSystem
from mojentic.llm.gateways.models import TextContent


class LLMTool:
    def __init__(self, tracer: Optional[TracerSystem] = None):
        """
        Initialize an LLM tool with optional tracer system.
        
        Parameters
        ----------
        tracer : TracerSystem, optional
            The tracer system to use for recording tool usage.
        """
        self.tracer_system = tracer
        
    def run(self, **kwargs):
        raise NotImplementedError

    def call_tool(self, **kwargs):
        # Record tool call in tracer system if available
        if self.tracer_system:
            # Execute the tool and capture the result
            result = self.run(**kwargs)
            
            # Record the tool call in the tracer system
            self.tracer_system.record_tool_call(
                tool_name=self.name,
                arguments=kwargs,
                result=result,
                source=type(self)
            )
        else:
            # Simply execute the tool if no tracer system is available
            result = self.run(**kwargs)
        
        # Format the result
        if isinstance(result, dict):
            result = json.dumps(result)
        return {
            "content": [
                TextContent(type="text", text=result).model_dump(),
            ]
        }

    @property
    def descriptor(self):
        raise NotImplementedError

    @property
    def name(self):
        return self.descriptor["function"]["name"]

    @property
    def description(self):
        return self.descriptor["function"]["description"]

    def matches(self, name: str):
        return name == self.name
        
    def set_tracer_system(self, tracer: Optional[TracerSystem]) -> None:
        """
        Set or update the tracer system used by this tool.
        
        Parameters
        ----------
        tracer : TracerSystem or None
            The tracer system to use, or None to disable tracing.
        """
        self.tracer_system = tracer
