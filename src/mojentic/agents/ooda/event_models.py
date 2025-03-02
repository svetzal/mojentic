"""Event models for the OODA loop implementation.

This module contains Pydantic models representing various events in the OODA
(Observe, Orient, Decide, Act) loop system. These events are used to track
the system's decision-making process and maintain an audit trail.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Enumeration of possible event types in the system."""
    TASK_GRAPH_INITIALIZED = "TaskGraphWasInitialized"
    TASK_GRAPH_UPDATED = "TaskGraphWasUpdated"
    SYSTEM_TERMINATED = "SystemWasTerminated"
    STEP_STARTED = "StepWasStarted"
    STEP_COMPLETED = "StepWasCompleted"
    STEP_FAILED = "StepDidFail"


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SystemStatus(str, Enum):
    """Enumeration of possible system statuses."""
    SUCCESS = "success"
    FAILURE = "failure"


class Task(BaseModel):
    """Represents a task in the system."""
    id: UUID
    description: str
    status: TaskStatus = TaskStatus.PENDING
    details: Optional[Dict[str, Any]] = None


class BaseEvent(BaseModel):
    """Base event model with common fields."""
    correlation_id: UUID = Field(..., description="Unique identifier linking related events")
    event_type: EventType = Field(..., description="Type of the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the event occurred")
    reason: Optional[str] = Field(None, description="Optional explanation for the event")


class TaskGraphInitializedEvent(BaseEvent):
    """Event emitted when the task graph is initialized."""
    event_type: EventType = EventType.TASK_GRAPH_INITIALIZED
    initial_tasks: List[Task] = Field(..., description="Initial set of tasks")


class TaskGraphUpdatedEvent(BaseEvent):
    """Event emitted when the task graph is updated with new tasks."""
    event_type: EventType = EventType.TASK_GRAPH_UPDATED
    added_tasks: List[Task] = Field(..., description="New tasks added to the graph")


class SystemTerminatedEvent(BaseEvent):
    """Event emitted when the system terminates."""
    event_type: EventType = EventType.SYSTEM_TERMINATED
    status: SystemStatus = Field(..., description="Final status of the system")
    summary: str = Field(..., description="Summary of the termination reason")


class StepStartedEvent(BaseEvent):
    """Event emitted when a step execution begins."""
    event_type: EventType = EventType.STEP_STARTED
    task_id: UUID = Field(..., description="ID of the task being started")
    task_details: Task = Field(..., description="Details of the task being started")


class StepCompletedEvent(BaseEvent):
    """Event emitted when a step is successfully completed."""
    event_type: EventType = EventType.STEP_COMPLETED
    task_id: UUID = Field(..., description="ID of the completed task")
    outcome: SystemStatus = Field(SystemStatus.SUCCESS, description="Outcome of the step")
    result: Dict[str, Any] = Field(..., description="Result data from the step")


class StepFailedEvent(BaseEvent):
    """Event emitted when a step execution fails."""
    event_type: EventType = EventType.STEP_FAILED
    task_id: UUID = Field(..., description="ID of the failed task")
    cause: str = Field(..., description="Reason for the failure")