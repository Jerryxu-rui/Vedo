"""
A2A Agent Coordinator
Comprehensive coordinator for Agent-to-Agent communication and workflow execution

Features:
- Thread-safe agent registry with health monitoring
- Capability-based message routing with load balancing
- DAG workflow execution with parallel task support
- Error handling with retry policies
- Progress tracking and performance monitoring

Part of Week 2: Agent Coordinator Refactor
"""

from typing import Dict, List, Optional, Any, Callable, Set, TYPE_CHECKING
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import threading
import time
from enum import Enum

from services.a2a_protocol import (
    A2AMessage,
    MessageType,
    Priority,
    AgentMetadata,
    AgentStatus,
    WorkflowDefinition,
    WorkflowTask,
    A2AError,
    AgentNotFoundError,
    AgentBusyError,
    TaskTimeoutError,
    DependencyError
)
from agents.base_a2a_agent import BaseA2AAgent

# Avoid circular import
if TYPE_CHECKING:
    from services.progress_broadcaster import ProgressBroadcaster


class WorkflowState(str, Enum):
    """Workflow execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"


class AgentRegistration:
    """Agent registration with health monitoring"""
    
    def __init__(self, agent: BaseA2AAgent, heartbeat_interval: int = 30):
        self.agent = agent
        self.registered_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.heartbeat_interval = heartbeat_interval
        self.message_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.lock = threading.Lock()
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        with self.lock:
            self.last_heartbeat = datetime.utcnow()
    
    def is_healthy(self, timeout: int = 60) -> bool:
        """Check if agent is healthy based on heartbeat"""
        with self.lock:
            elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
            return elapsed < timeout
    
    def record_message(self, execution_time: float, success: bool = True):
        """Record message execution metrics"""
        with self.lock:
            self.message_count += 1
            self.total_execution_time += execution_time
            if not success:
                self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        with self.lock:
            avg_time = (self.total_execution_time / self.message_count 
                       if self.message_count > 0 else 0)
            error_rate = (self.error_count / self.message_count 
                         if self.message_count > 0 else 0)
            
            return {
                "message_count": self.message_count,
                "error_count": self.error_count,
                "error_rate": error_rate,
                "avg_execution_time": avg_time,
                "total_execution_time": self.total_execution_time,
                "last_heartbeat": self.last_heartbeat.isoformat(),
                "is_healthy": self.is_healthy()
            }


class MessageQueue:
    """Priority-based message queue with dead letter support"""
    
    def __init__(self, max_retries: int = 3):
        self.queues = {
            Priority.HIGH: deque(),
            Priority.MEDIUM: deque(),
            Priority.LOW: deque()
        }
        self.dead_letter_queue = deque()
        self.max_retries = max_retries
        self.retry_counts: Dict[str, int] = {}
        self.lock = threading.Lock()
    
    def enqueue(self, message: A2AMessage):
        """Add message to appropriate priority queue"""
        with self.lock:
            self.queues[message.priority].append(message)
    
    def dequeue(self) -> Optional[A2AMessage]:
        """Dequeue highest priority message"""
        with self.lock:
            # Try high priority first
            for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                if self.queues[priority]:
                    return self.queues[priority].popleft()
            return None
    
    def retry_message(self, message: A2AMessage) -> bool:
        """
        Retry failed message
        
        Returns:
            True if message was requeued, False if moved to dead letter queue
        """
        with self.lock:
            message_id = message.message_id
            retry_count = self.retry_counts.get(message_id, 0) + 1
            self.retry_counts[message_id] = retry_count
            
            if retry_count <= self.max_retries:
                # Requeue with exponential backoff
                self.queues[message.priority].append(message)
                return True
            else:
                # Move to dead letter queue
                self.dead_letter_queue.append(message)
                return False
    
    def get_dead_letters(self) -> List[A2AMessage]:
        """Get all messages in dead letter queue"""
        with self.lock:
            return list(self.dead_letter_queue)
    
    def size(self) -> int:
        """Get total queue size"""
        with self.lock:
            return sum(len(q) for q in self.queues.values())


class WorkflowExecution:
    """Workflow execution state and tracking"""
    
    def __init__(self, workflow: WorkflowDefinition):
        self.workflow = workflow
        self.state = WorkflowState.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
        self.task_states: Dict[str, WorkflowState] = {
            task.name: WorkflowState.PENDING for task in workflow.tasks
        }
        self.progress: float = 0.0
        self.lock = threading.Lock()
    
    def start(self):
        """Mark workflow as started"""
        with self.lock:
            self.state = WorkflowState.RUNNING
            self.started_at = datetime.utcnow()
    
    def complete_task(self, task_name: str, result: Any):
        """Mark task as completed"""
        with self.lock:
            self.task_states[task_name] = WorkflowState.COMPLETED
            self.results[task_name] = result
            self._update_progress()
    
    def fail_task(self, task_name: str, error: str):
        """Mark task as failed"""
        with self.lock:
            self.task_states[task_name] = WorkflowState.FAILED
            self.errors[task_name] = error
            self._update_progress()
    
    def complete(self):
        """Mark workflow as completed"""
        with self.lock:
            self.state = WorkflowState.COMPLETED
            self.completed_at = datetime.utcnow()
            self.progress = 1.0
    
    def fail(self, error: str):
        """Mark workflow as failed"""
        with self.lock:
            self.state = WorkflowState.FAILED
            self.completed_at = datetime.utcnow()
            self.errors["workflow"] = error
    
    def cancel(self):
        """Cancel workflow execution"""
        with self.lock:
            self.state = WorkflowState.CANCELLED
            self.completed_at = datetime.utcnow()
    
    def _update_progress(self):
        """Update overall progress"""
        completed = sum(1 for state in self.task_states.values() 
                       if state == WorkflowState.COMPLETED)
        total = len(self.task_states)
        self.progress = completed / total if total > 0 else 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get workflow execution status"""
        with self.lock:
            duration = None
            if self.started_at:
                end_time = self.completed_at or datetime.utcnow()
                duration = (end_time - self.started_at).total_seconds()
            
            return {
                "workflow_id": self.workflow.workflow_id,
                "state": self.state,
                "progress": self.progress,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration": duration,
                "task_states": dict(self.task_states),
                "completed_tasks": len([s for s in self.task_states.values() 
                                       if s == WorkflowState.COMPLETED]),
                "failed_tasks": len([s for s in self.task_states.values() 
                                    if s == WorkflowState.FAILED]),
                "errors": dict(self.errors)
            }


class A2AAgentCoordinator:
    """
    Comprehensive A2A Agent Coordinator
    
    Manages agent registry, message routing, and workflow execution
    with support for parallel tasks, error recovery, and performance monitoring
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        load_balancing: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED,
        heartbeat_check_interval: int = 30,
        progress_broadcaster: Optional["ProgressBroadcaster"] = None
    ):
        # Agent registry
        self.agents: Dict[str, AgentRegistration] = {}
        self.capability_map: Dict[str, List[str]] = defaultdict(list)
        self.registry_lock = threading.Lock()
        
        # Message routing
        self.message_queue = MessageQueue()
        self.load_balancing = load_balancing
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        
        # Workflow execution
        self.workflows: Dict[str, WorkflowExecution] = {}
        self.workflow_lock = threading.Lock()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        # Monitoring
        self.heartbeat_check_interval = heartbeat_check_interval
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Performance metrics
        self.total_messages = 0
        self.total_workflows = 0
        self.metrics_lock = threading.Lock()
        
        # Progress broadcaster for WebSocket updates
        self.progress_broadcaster = progress_broadcaster
    
    # ==================== Agent Registry ====================
    
    def register_agent(self, agent: BaseA2AAgent):
        """
        Register an agent with the coordinator
        
        Args:
            agent: Agent to register
        """
        with self.registry_lock:
            if agent.name in self.agents:
                raise ValueError(f"Agent '{agent.name}' already registered")
            
            # Create registration
            registration = AgentRegistration(agent)
            self.agents[agent.name] = registration
            
            # Update capability map
            for capability in agent.get_capabilities():
                self.capability_map[capability.name].append(agent.name)
            
            print(f"[A2ACoordinator] Registered agent: {agent.name}")
    
    async def unregister_agent(self, agent_name: str):
        """Alias for deregister_agent for async compatibility"""
        self.deregister_agent(agent_name)
    
    def deregister_agent(self, agent_name: str):
        """Deregister an agent"""
        with self.registry_lock:
            if agent_name not in self.agents:
                return
            
            registration = self.agents[agent_name]
            agent = registration.agent
            
            # Remove from capability map
            for capability in agent.get_capabilities():
                if agent_name in self.capability_map[capability.name]:
                    self.capability_map[capability.name].remove(agent_name)
            
            # Remove registration
            del self.agents[agent_name]
            
            print(f"[A2ACoordinator] Deregistered agent: {agent_name}")
    
    def find_agents_with_capability(self, capability: str) -> List[str]:
        """
        Find all agents that provide a capability
        
        Args:
            capability: Capability name
        
        Returns:
            List of agent names
        """
        with self.registry_lock:
            return list(self.capability_map.get(capability, []))
    
    def discover_agents_by_capability(self, capability: str) -> List[str]:
        """Alias for find_agents_with_capability"""
        return self.find_agents_with_capability(capability)
    
    async def update_agent_heartbeat(self, agent_name: str):
        """Update agent heartbeat timestamp"""
        with self.registry_lock:
            if agent_name in self.agents:
                self.agents[agent_name].update_heartbeat()
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get agent status and metrics"""
        with self.registry_lock:
            if agent_name not in self.agents:
                raise AgentNotFoundError(agent_name)
            
            registration = self.agents[agent_name]
            return {
                "name": agent_name,
                "status": registration.agent.status,
                "registered_at": registration.registered_at.isoformat(),
                "metrics": registration.get_metrics()
            }
    
    # ==================== Message Routing ====================
    
    async def send_message(
        self,
        message: A2AMessage,
        timeout: Optional[int] = None
    ) -> A2AMessage:
        """
        Send A2A message to agent and wait for response
        
        Args:
            message: A2A message to send
            timeout: Optional timeout in seconds
        
        Returns:
            Response message
        """
        receiver = message.receiver
        
        with self.registry_lock:
            if receiver not in self.agents:
                raise AgentNotFoundError(receiver)
            
            registration = self.agents[receiver]
            agent = registration.agent
        
        # Send to agent with timeout
        start_time = time.time()
        try:
            if timeout:
                response = await asyncio.wait_for(
                    agent.handle_message(message),
                    timeout=timeout
                )
            else:
                response = await agent.handle_message(message)
            
            # Record metrics
            execution_time = time.time() - start_time
            registration.record_message(execution_time, success=True)
            
            with self.metrics_lock:
                self.total_messages += 1
            
            return response
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            registration.record_message(execution_time, success=False)
            task = message.payload.get("task", "unknown")
            raise TaskTimeoutError(task, timeout)
        
        except Exception as e:
            execution_time = time.time() - start_time
            registration.record_message(execution_time, success=False)
            raise
    
    async def send_task_message(
        self,
        receiver: str,
        task: str,
        parameters: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        timeout: Optional[int] = None
    ) -> A2AMessage:
        """
        Send message to agent and wait for response
        
        Args:
            receiver: Target agent name
            task: Task to perform
            parameters: Task parameters
            correlation_id: Optional correlation ID
            priority: Message priority
            timeout: Optional timeout in seconds
        
        Returns:
            Response message
        """
        with self.registry_lock:
            if receiver not in self.agents:
                raise AgentNotFoundError(receiver)
            
            registration = self.agents[receiver]
            agent = registration.agent
        
        # Create request message
        from services.a2a_protocol import create_request_message
        message = create_request_message(
            sender="coordinator",
            receiver=receiver,
            task=task,
            parameters=parameters,
            correlation_id=correlation_id,
            priority=priority
        )
        
        # Send to agent with timeout
        start_time = time.time()
        try:
            if timeout:
                response = await asyncio.wait_for(
                    agent.handle_message(message),
                    timeout=timeout
                )
            else:
                response = await agent.handle_message(message)
            
            # Record metrics
            execution_time = time.time() - start_time
            registration.record_message(execution_time, success=True)
            
            with self.metrics_lock:
                self.total_messages += 1
            
            return response
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            registration.record_message(execution_time, success=False)
            raise TaskTimeoutError(task, timeout)
        
        except Exception as e:
            execution_time = time.time() - start_time
            registration.record_message(execution_time, success=False)
            raise
    
    def select_agent_for_task(
        self,
        task: str,
        strategy: Optional[LoadBalancingStrategy] = None
    ) -> Optional[str]:
        """Alias for select_agent_for_capability"""
        return self.select_agent_for_capability(task, strategy)
    
    def select_agent_for_capability(
        self,
        capability: str,
        strategy: Optional[LoadBalancingStrategy] = None
    ) -> Optional[str]:
        """
        Select best agent for a capability using load balancing
        
        Args:
            capability: Capability name
        
        Returns:
            Selected agent name or None
        """
        agents = self.find_agents_with_capability(capability)
        if not agents:
            return None
        
        if len(agents) == 1:
            return agents[0]
        
        # Use provided strategy or default
        strategy = strategy or self.load_balancing
        
        # Apply load balancing strategy
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            counter = self.round_robin_counters[capability]
            selected = agents[counter % len(agents)]
            self.round_robin_counters[capability] = counter + 1
            return selected
        
        elif strategy == LoadBalancingStrategy.LEAST_LOADED:
            # Select agent with lowest message count
            with self.registry_lock:
                agent_loads = [
                    (name, self.agents[name].message_count)
                    for name in agents
                    if name in self.agents
                ]
                if agent_loads:
                    return min(agent_loads, key=lambda x: x[1])[0]
        
        # Default: return first agent
        return agents[0]
    
    # ==================== Workflow Execution ====================
    
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute workflow with dependency resolution and parallel tasks
        
        Args:
            workflow: Workflow definition
            progress_callback: Optional progress callback
        
        Returns:
            Dictionary of task results
        """
        # Validate workflow
        if not workflow.validate_dependencies():
            raise DependencyError("Invalid workflow dependencies")
        
        # Create execution tracking
        execution = WorkflowExecution(workflow)
        with self.workflow_lock:
            self.workflows[workflow.workflow_id] = execution
            self.total_workflows += 1
        
        execution.start()
        
        try:
            # Get execution order (stages for parallel execution)
            stages = workflow.get_execution_order()
            
            # Execute each stage
            for stage_idx, stage_tasks in enumerate(stages):
                # Report progress
                if progress_callback:
                    await progress_callback({
                        "workflow_id": workflow.workflow_id,
                        "stage": stage_idx + 1,
                        "total_stages": len(stages),
                        "tasks": stage_tasks,
                        "progress": execution.progress
                    })
                
                # Execute tasks in parallel within stage
                task_futures = []
                for task_name in stage_tasks:
                    task = next(t for t in workflow.tasks if t.name == task_name)
                    future = self._execute_task(task, execution, workflow.workflow_id)
                    task_futures.append(future)
                
                # Wait for all tasks in stage to complete
                results = await asyncio.gather(*task_futures, return_exceptions=True)
                
                # Check for errors
                for task_name, result in zip(stage_tasks, results):
                    if isinstance(result, Exception):
                        execution.fail_task(task_name, str(result))
                        raise result
            
            # Mark workflow as completed
            execution.complete()
            
            if progress_callback:
                await progress_callback({
                    "workflow_id": workflow.workflow_id,
                    "state": "completed",
                    "progress": 1.0
                })
            
            return execution.results
        
        except Exception as e:
            execution.fail(str(e))
            raise
    
    async def _execute_task(
        self,
        task: WorkflowTask,
        execution: WorkflowExecution,
        correlation_id: str
    ) -> Any:
        """Execute a single task with semaphore control"""
        
        async with self.task_semaphore:
            try:
                # Send message to agent
                response = await self.send_message(
                    receiver=task.agent,
                    task=task.task,
                    parameters=task.parameters,
                    correlation_id=correlation_id,
                    priority=task.priority,
                    timeout=task.timeout
                )
                
                # Extract result
                result = response.payload.get("result")
                execution.complete_task(task.name, result)
                
                return result
            
            except Exception as e:
                execution.fail_task(task.name, str(e))
                raise
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        with self.workflow_lock:
            if workflow_id not in self.workflows:
                raise ValueError(f"Workflow '{workflow_id}' not found")
            
            return self.workflows[workflow_id].get_status()
    
    def cancel_workflow(self, workflow_id: str):
        """Cancel workflow execution"""
        with self.workflow_lock:
            if workflow_id not in self.workflows:
                raise ValueError(f"Workflow '{workflow_id}' not found")
            
            self.workflows[workflow_id].cancel()
    
    # ==================== Monitoring ====================
    
    async def start_monitoring(self):
        """Start health monitoring task"""
        self.monitoring_task = asyncio.create_task(self._monitor_agents())
    
    async def stop_monitoring(self):
        """Stop health monitoring task"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_agents(self):
        """Monitor agent health"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_check_interval)
                
                with self.registry_lock:
                    for name, registration in list(self.agents.items()):
                        if not registration.is_healthy():
                            print(f"[A2ACoordinator] Agent '{name}' unhealthy, deregistering")
                            self.deregister_agent(name)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[A2ACoordinator] Monitoring error: {e}")
    
    def get_coordinator_metrics(self) -> Dict[str, Any]:
        """Get coordinator performance metrics"""
        with self.metrics_lock:
            with self.registry_lock:
                agent_count = len(self.agents)
                healthy_agents = sum(1 for r in self.agents.values() if r.is_healthy())
            
            with self.workflow_lock:
                active_workflows = sum(1 for w in self.workflows.values() 
                                      if w.state == WorkflowState.RUNNING)
            
            return {
                "total_messages": self.total_messages,
                "total_workflows": self.total_workflows,
                "registered_agents": agent_count,
                "healthy_agents": healthy_agents,
                "active_workflows": active_workflows,
                "queue_size": self.message_queue.size(),
                "dead_letters": len(self.message_queue.get_dead_letters())
            }
    
    async def shutdown(self):
        """Shutdown coordinator and cleanup resources"""
        # Stop monitoring
        await self.stop_monitoring()
        
        # Clear all agents
        with self.registry_lock:
            agent_names = list(self.agents.keys())
            for name in agent_names:
                self.deregister_agent(name)
        
        # Clear workflows
        with self.workflow_lock:
            self.workflows.clear()
        
        print("[A2ACoordinator] Shutdown complete")