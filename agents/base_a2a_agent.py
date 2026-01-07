"""
Base A2A Agent
Standard base class for all agents using A2A protocol

Part of Week 2: Agent Coordinator Refactor
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio

from services.a2a_protocol import (
    A2AMessage,
    MessageType,
    AgentCapability,
    AgentMetadata,
    AgentStatus,
    A2AError
)


class BaseA2AAgent(ABC):
    """
    Base class for all A2A-compatible agents
    
    Provides:
    - Standard message handling
    - Capability registration
    - Dependency declaration
    - Status management
    - Progress reporting
    """
    
    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.progress_callback: Optional[Callable] = None
        
        # Initialize metadata
        self.metadata = AgentMetadata(
            name=name,
            version=version,
            description=description,
            capabilities=self.get_capabilities(),
            dependencies=self.get_dependencies(),
            status=self.status
        )
    
    @abstractmethod
    async def handle_message(self, message: A2AMessage) -> A2AMessage:
        """
        Handle incoming A2A message
        
        This is the main entry point for agent communication.
        Subclasses must implement this to handle specific tasks.
        
        Args:
            message: Incoming A2A message
        
        Returns:
            Response A2A message
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Return list of capabilities this agent provides
        
        Returns:
            List of AgentCapability objects
        """
        pass
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """
        Return list of agents this agent depends on
        
        Returns:
            List of agent names
        """
        pass
    
    def validate_message(self, message: A2AMessage) -> bool:
        """
        Validate incoming message
        
        Args:
            message: Message to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Check message type
        if message.message_type != MessageType.REQUEST:
            return False
        
        # Check required fields
        if "task" not in message.payload:
            return False
        
        # Check if task is supported
        task = message.payload["task"]
        supported_tasks = [cap.name for cap in self.get_capabilities()]
        
        return task in supported_tasks
    
    def set_status(self, status: AgentStatus):
        """Update agent status"""
        self.status = status
        self.metadata.status = status
    
    def set_progress_callback(self, callback: Callable):
        """Set progress callback function"""
        self.progress_callback = callback
    
    async def report_progress(
        self,
        progress: float,
        stage: str,
        message: str = ""
    ):
        """
        Report progress to callback if set
        
        Args:
            progress: Progress value (0.0 to 1.0)
            stage: Current stage name
            message: Optional progress message
        """
        if self.progress_callback:
            await self.progress_callback({
                "agent": self.name,
                "progress": progress,
                "stage": stage,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def execute_task(
        self,
        task: str,
        parameters: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Any:
        """
        Execute a task (internal method)
        
        Args:
            task: Task name
            parameters: Task parameters
            correlation_id: Optional correlation ID
        
        Returns:
            Task result
        """
        # Set status to busy
        self.set_status(AgentStatus.BUSY)
        self.current_task = task
        
        try:
            # Report start
            await self.report_progress(0.0, task, "Starting task")
            
            # Execute task (subclass implements this)
            result = await self._execute_task_impl(task, parameters)
            
            # Report completion
            await self.report_progress(1.0, task, "Task completed")
            
            return result
        
        except Exception as e:
            # Report error
            self.set_status(AgentStatus.ERROR)
            raise A2AError(f"Task execution failed: {str(e)}", retryable=True)
        
        finally:
            # Reset status
            self.set_status(AgentStatus.IDLE)
            self.current_task = None
    
    @abstractmethod
    async def _execute_task_impl(
        self,
        task: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Internal task execution implementation
        
        Subclasses must implement this to perform actual work.
        
        Args:
            task: Task name
            parameters: Task parameters
        
        Returns:
            Task result
        """
        pass
    
    def get_metadata(self) -> AgentMetadata:
        """Get agent metadata"""
        return self.metadata
    
    def is_busy(self) -> bool:
        """Check if agent is busy"""
        return self.status == AgentStatus.BUSY
    
    def can_handle_task(self, task: str) -> bool:
        """
        Check if agent can handle a task
        
        Args:
            task: Task name
        
        Returns:
            True if agent can handle this task
        """
        supported_tasks = [cap.name for cap in self.get_capabilities()]
        return task in supported_tasks
    
    def get_task_schema(self, task: str) -> Optional[Dict[str, Any]]:
        """
        Get input/output schema for a task
        
        Args:
            task: Task name
        
        Returns:
            Schema dictionary or None if task not found
        """
        for capability in self.get_capabilities():
            if capability.name == task:
                return {
                    "input": capability.input_schema,
                    "output": capability.output_schema
                }
        return None
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', status='{self.status}')>"


class SimpleA2AAgent(BaseA2AAgent):
    """
    Simple A2A agent for quick implementations
    
    Allows defining capabilities and task handlers without subclassing
    """
    
    def __init__(
        self,
        name: str,
        capabilities: List[AgentCapability],
        dependencies: List[str] = None,
        task_handlers: Dict[str, Callable] = None
    ):
        self._capabilities = capabilities
        self._dependencies = dependencies or []
        self._task_handlers = task_handlers or {}
        
        super().__init__(name)
    
    def get_capabilities(self) -> List[AgentCapability]:
        return self._capabilities
    
    def get_dependencies(self) -> List[str]:
        return self._dependencies
    
    async def handle_message(self, message: A2AMessage) -> A2AMessage:
        """Handle incoming message"""
        
        if not self.validate_message(message):
            return message.create_error("Invalid message format")
        
        task = message.payload["task"]
        parameters = message.payload.get("parameters", {})
        
        try:
            result = await self.execute_task(
                task,
                parameters,
                message.correlation_id
            )
            return message.create_response(result)
        
        except Exception as e:
            return message.create_error(str(e))
    
    async def _execute_task_impl(
        self,
        task: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute task using registered handler"""
        
        if task not in self._task_handlers:
            raise ValueError(f"No handler registered for task: {task}")
        
        handler = self._task_handlers[task]
        
        # Call handler (sync or async)
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            return handler(**parameters)
    
    def register_task_handler(self, task: str, handler: Callable):
        """
        Register a task handler
        
        Args:
            task: Task name
            handler: Handler function (sync or async)
        """
        self._task_handlers[task] = handler


# Helper function to create simple agents

def create_simple_agent(
    name: str,
    capabilities: List[Dict[str, Any]],
    dependencies: List[str] = None,
    task_handlers: Dict[str, Callable] = None
) -> SimpleA2AAgent:
    """
    Helper to create a simple A2A agent
    
    Args:
        name: Agent name
        capabilities: List of capability dictionaries
        dependencies: List of dependency agent names
        task_handlers: Dictionary of task name -> handler function
    
    Returns:
        SimpleA2AAgent instance
    
    Example:
        agent = create_simple_agent(
            name="example_agent",
            capabilities=[
                {
                    "name": "process_data",
                    "description": "Process some data",
                    "input_schema": {"data": "string"},
                    "output_schema": {"result": "string"}
                }
            ],
            task_handlers={
                "process_data": lambda data: f"Processed: {data}"
            }
        )
    """
    
    # Convert capability dicts to AgentCapability objects
    cap_objects = [
        AgentCapability(**cap) if isinstance(cap, dict) else cap
        for cap in capabilities
    ]
    
    return SimpleA2AAgent(
        name=name,
        capabilities=cap_objects,
        dependencies=dependencies,
        task_handlers=task_handlers
    )