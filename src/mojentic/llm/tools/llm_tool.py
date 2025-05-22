import json
from typing import Any, Dict, Optional

from mojentic.audit.audit_system import AuditSystem
from mojentic.llm.gateways.models import TextContent


class LLMTool:
    def __init__(self, audit_system: Optional[AuditSystem] = None):
        """
        Initialize an LLM tool with optional audit system.
        
        Parameters
        ----------
        audit_system : AuditSystem, optional
            The audit system to use for recording tool usage.
        """
        self.audit_system = audit_system
        
    def run(self, **kwargs):
        raise NotImplementedError

    def call_tool(self, **kwargs):
        # Record tool call in audit system if available
        if self.audit_system:
            # Execute the tool and capture the result
            result = self.run(**kwargs)
            
            # Record the tool call in the audit system
            self.audit_system.record_tool_call(
                tool_name=self.name,
                arguments=kwargs,
                result=result,
                source=type(self)
            )
        else:
            # Simply execute the tool if no audit system is available
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
        
    def set_audit_system(self, audit_system: Optional[AuditSystem]) -> None:
        """
        Set or update the audit system used by this tool.
        
        Parameters
        ----------
        audit_system : AuditSystem or None
            The audit system to use, or None to disable auditing.
        """
        self.audit_system = audit_system
