"""
A2A (Agent-to-Agent) Protocol Implementation
Standardized communication protocol for multi-agent coordination

Part of Week 2: Agent Coordinator Refactor
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class MessageType(str, Enum):
    """Types of A2A messages"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    PROGRESS = "progress"


class Priority(str, Enum):
    """Message priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentStatus(str, Enum):
    """Agent status"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class A2AMessage(BaseModel):
    """
    Standard A2A message format
    
    Provides consistent structure for all agent-to-agent communication
    """
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = Field(description="Sending agent name")
    receiver: str = Field(description="Receiving agent name")
    message_type: MessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # Links related messages in a workflow
    priority: Priority = Priority.MEDIUM
    
    def create_response(self, result: Any, metadata: Dict[str, Any] = None) -> "A2AMessage":
        """
        Create response message
        
        Args:
            result: Result data to return
            metadata: Optional additional metadata
        
        Returns:
            Response A2A message
        """
        return A2AMessage(
            sender=self.receiver,
            receiver=self.sender,
            message_type=MessageType.RESPONSE,
            payload={"result": result},
            metadata=metadata or {},
            correlation_id=self.correlation_id or self.message_id,
            priority=self.priority
        )
    
    def create_error(self, error: str, error_type: str = "AgentError") -> "A2AMessage":
        """
        Create error message
        
        Args:
            error: Error description
            error_type: Type of error
        
        Returns:
            Error A2A message
        """
        return A2AMessage(
            sender=self.receiver,
            receiver=self.sender,
            message_type=MessageType.ERROR,
            payload={
                "error": error,
                "error_type": error_type
            },
            correlation_id=self.correlation_id or self.message_id,
            priority=Priority.HIGH  # Errors are high priority
        )
    
    def create_progress(self, progress: float, stage: str, message: str = "") -> "A2AMessage":
        """
        Create progress notification message
        
        Args:
            progress: Progress value (0.0 to 1.0)
            stage: Current stage name
            message: Optional progress message
        
        Returns:
            Progress A2A message
        """
        return A2AMessage(
            sender=self.receiver,
            receiver=self.sender,
            message_type=MessageType.PROGRESS,
            payload={
                "progress": progress,
                "stage": stage,
                "message": message
            },
            correlation_id=self.correlation_id or self.message_id,
            priority=Priority.LOW  # Progress updates are low priority
        )


class AgentCapability(BaseModel):
    """Agent capability description"""
    name: str = Field(description="Capability name")
    description: str = Field(description="What this capability does")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Expected input format")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Output format")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")


class AgentMetadata(BaseModel):
    """Agent metadata and capabilities"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[AgentCapability] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list, description="Required agent names")
    status: AgentStatus = AgentStatus.IDLE
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)


class WorkflowTask(BaseModel):
    """Task in a workflow"""
    name: str = Field(description="Unique task name")
    agent: str = Field(description="Agent to execute this task")
    task: str = Field(description="Task/capability to invoke")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list, description="Task names this depends on")
    priority: Priority = Priority.MEDIUM
    timeout: Optional[int] = Field(None, description="Timeout in seconds")


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    tasks: List[WorkflowTask]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def validate_dependencies(self) -> bool:
        """
        Validate that all task dependencies exist
        
        Returns:
            True if valid, False otherwise
        """
        task_names = {task.name for task in self.tasks}
        
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_names:
                    return False
        
        return True
    
    def get_execution_order(self) -> List[List[str]]:
        """
        Get execution order with parallel stages
        
        Returns:
            List of stages, each stage contains task names that can run in parallel
        """
        completed = set()
        stages = []
        tasks_by_name = {task.name: task for task in self.tasks}
        
        while len(completed) < len(self.tasks):
            # Find tasks ready to execute
            ready = [
                task.name for task in self.tasks
                if task.name not in completed
                and all(dep in completed for dep in task.dependencies)
            ]
            
            if not ready:
                raise ValueError("Circular dependency detected in workflow")
            
            stages.append(ready)
            completed.update(ready)
        
        return stages


class A2AError(Exception):
    """Base exception for A2A protocol errors"""
    
    def __init__(self, message: str, error_type: str = "A2AError", retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class AgentNotFoundError(A2AError):
    """Agent not found in registry"""
    
    def __init__(self, agent_name: str):
        super().__init__(
            f"Agent '{agent_name}' not found in registry",
            error_type="AgentNotFoundError",
            retryable=False
        )


class AgentBusyError(A2AError):
    """Agent is busy and cannot accept new tasks"""
    
    def __init__(self, agent_name: str):
        super().__init__(
            f"Agent '{agent_name}' is busy",
            error_type="AgentBusyError",
            retryable=True
        )


class TaskTimeoutError(A2AError):
    """Task execution timeout"""
    
    def __init__(self, task_name: str, timeout: int):
        super().__init__(
            f"Task '{task_name}' timed out after {timeout} seconds",
            error_type="TaskTimeoutError",
            retryable=True
        )


class DependencyError(A2AError):
    """Dependency resolution error"""
    
    def __init__(self, message: str):
        super().__init__(
            message,
            error_type="DependencyError",
            retryable=False
        )


# Helper functions

def create_request_message(
    sender: str,
    receiver: str,
    task: str,
    parameters: Dict[str, Any],
    correlation_id: Optional[str] = None,
    priority: Priority = Priority.MEDIUM
) -> A2AMessage:
    """
    Helper to create a request message
    
    Args:
        sender: Sending agent name
        receiver: Receiving agent name
        task: Task to perform
        parameters: Task parameters
        correlation_id: Optional correlation ID
        priority: Message priority
    
    Returns:
        A2A request message
    """
    return A2AMessage(
        sender=sender,
        receiver=receiver,
        message_type=MessageType.REQUEST,
        payload={
            "task": task,
            "parameters": parameters
        },
        correlation_id=correlation_id,
        priority=priority
    )


def create_notification_message(
    sender: str,
    receiver: str,
    event: str,
    data: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> A2AMessage:
    """
    Helper to create a notification message
    
    Args:
        sender: Sending agent name
        receiver: Receiving agent name
        event: Event name
        data: Event data
        correlation_id: Optional correlation ID
    
    Returns:
        A2A notification message
    """
    return A2AMessage(
        sender=sender,
        receiver=receiver,
        message_type=MessageType.NOTIFICATION,
        payload={
            "event": event,
            "data": data
        },
        correlation_id=correlation_id,
        priority=Priority.LOW
    )