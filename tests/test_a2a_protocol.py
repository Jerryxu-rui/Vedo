"""
Comprehensive A2A Protocol Tests
Tests for A2A protocol, agent coordinator, and screenwriter agent

Part of Week 2: Agent Coordinator Refactor - Phase 3
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from services.a2a_protocol import (
    A2AMessage,
    MessageType,
    Priority,
    AgentStatus,
    AgentCapability,
    AgentMetadata,
    WorkflowTask,
    WorkflowDefinition,
    A2AError,
    AgentNotFoundError,
    AgentBusyError,
    TaskTimeoutError,
    DependencyError,
    create_request_message,
    create_notification_message
)

from services.a2a_agent_coordinator import (
    A2AAgentCoordinator,
    LoadBalancingStrategy
)

from agents.base_a2a_agent import BaseA2AAgent, SimpleA2AAgent, create_simple_agent
from agents.screenwriter_a2a import ScreenwriterA2AAgent


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_agent():
    """Create a simple mock agent for testing"""
    
    capabilities = [
        AgentCapability(
            name="test_task",
            description="A test task",
            input_schema={"data": "string"},
            output_schema={"result": "string"}
        )
    ]
    
    async def test_handler(data: str) -> str:
        await asyncio.sleep(0.1)  # Simulate work
        return f"Processed: {data}"
    
    agent = create_simple_agent(
        name="test_agent",
        capabilities=capabilities,
        task_handlers={"test_task": test_handler}
    )
    
    return agent


@pytest.fixture
def mock_agent_slow():
    """Create a slow mock agent for timeout testing"""
    
    capabilities = [
        AgentCapability(
            name="slow_task",
            description="A slow task",
            input_schema={"data": "string"},
            output_schema={"result": "string"}
        )
    ]
    
    async def slow_handler(data: str) -> str:
        await asyncio.sleep(5)  # Simulate slow work
        return f"Processed: {data}"
    
    agent = create_simple_agent(
        name="slow_agent",
        capabilities=capabilities,
        task_handlers={"slow_task": slow_handler}
    )
    
    return agent


@pytest.fixture
def mock_agent_error():
    """Create a mock agent that raises errors"""
    
    capabilities = [
        AgentCapability(
            name="error_task",
            description="A task that errors",
            input_schema={"data": "string"},
            output_schema={"result": "string"}
        )
    ]
    
    async def error_handler(data: str) -> str:
        raise ValueError("Intentional error for testing")
    
    agent = create_simple_agent(
        name="error_agent",
        capabilities=capabilities,
        task_handlers={"error_task": error_handler}
    )
    
    return agent


@pytest.fixture
async def coordinator():
    """Create coordinator instance"""
    coord = A2AAgentCoordinator()
    yield coord
    # Cleanup
    await coord.shutdown()


# ============================================================================
# Message Creation and Validation Tests
# ============================================================================

class TestMessageCreation:
    """Test A2A message creation and validation"""
    
    def test_create_request_message(self):
        """Test creating a request message"""
        msg = create_request_message(
            sender="agent_a",
            receiver="agent_b",
            task="test_task",
            parameters={"data": "test"},
            priority=Priority.HIGH
        )
        
        assert msg.sender == "agent_a"
        assert msg.receiver == "agent_b"
        assert msg.message_type == MessageType.REQUEST
        assert msg.payload["task"] == "test_task"
        assert msg.payload["parameters"]["data"] == "test"
        assert msg.priority == Priority.HIGH
        assert msg.message_id is not None
    
    def test_create_notification_message(self):
        """Test creating a notification message"""
        msg = create_notification_message(
            sender="agent_a",
            receiver="agent_b",
            event="task_complete",
            data={"result": "success"}
        )
        
        assert msg.sender == "agent_a"
        assert msg.receiver == "agent_b"
        assert msg.message_type == MessageType.NOTIFICATION
        assert msg.payload["event"] == "task_complete"
        assert msg.payload["data"]["result"] == "success"
        assert msg.priority == Priority.LOW
    
    def test_create_response_message(self):
        """Test creating a response from a request"""
        request = create_request_message(
            sender="agent_a",
            receiver="agent_b",
            task="test_task",
            parameters={"data": "test"}
        )
        
        response = request.create_response({"result": "success"})
        
        assert response.sender == "agent_b"
        assert response.receiver == "agent_a"
        assert response.message_type == MessageType.RESPONSE
        assert response.payload["result"]["result"] == "success"
        assert response.correlation_id == request.message_id
    
    def test_create_error_message(self):
        """Test creating an error message"""
        request = create_request_message(
            sender="agent_a",
            receiver="agent_b",
            task="test_task",
            parameters={"data": "test"}
        )
        
        error = request.create_error("Something went wrong", "TestError")
        
        assert error.sender == "agent_b"
        assert error.receiver == "agent_a"
        assert error.message_type == MessageType.ERROR
        assert error.payload["error"] == "Something went wrong"
        assert error.payload["error_type"] == "TestError"
        assert error.priority == Priority.HIGH
    
    def test_create_progress_message(self):
        """Test creating a progress message"""
        request = create_request_message(
            sender="agent_a",
            receiver="agent_b",
            task="test_task",
            parameters={"data": "test"}
        )
        
        progress = request.create_progress(0.5, "processing", "Halfway done")
        
        assert progress.sender == "agent_b"
        assert progress.receiver == "agent_a"
        assert progress.message_type == MessageType.PROGRESS
        assert progress.payload["progress"] == 0.5
        assert progress.payload["stage"] == "processing"
        assert progress.payload["message"] == "Halfway done"
        assert progress.priority == Priority.LOW


# ============================================================================
# Workflow Validation Tests
# ============================================================================

class TestWorkflowValidation:
    """Test workflow definition and validation"""
    
    def test_simple_workflow_validation(self):
        """Test validating a simple workflow"""
        workflow = WorkflowDefinition(
            name="simple_workflow",
            tasks=[
                WorkflowTask(
                    name="task1",
                    agent="agent_a",
                    task="do_something",
                    parameters={}
                ),
                WorkflowTask(
                    name="task2",
                    agent="agent_b",
                    task="do_something_else",
                    parameters={},
                    dependencies=["task1"]
                )
            ]
        )
        
        assert workflow.validate_dependencies() is True
    
    def test_workflow_invalid_dependency(self):
        """Test workflow with invalid dependency"""
        workflow = WorkflowDefinition(
            name="invalid_workflow",
            tasks=[
                WorkflowTask(
                    name="task1",
                    agent="agent_a",
                    task="do_something",
                    parameters={},
                    dependencies=["nonexistent_task"]
                )
            ]
        )
        
        assert workflow.validate_dependencies() is False
    
    def test_workflow_execution_order_linear(self):
        """Test execution order for linear workflow"""
        workflow = WorkflowDefinition(
            name="linear_workflow",
            tasks=[
                WorkflowTask(name="task1", agent="agent_a", task="task", parameters={}),
                WorkflowTask(name="task2", agent="agent_b", task="task", parameters={}, dependencies=["task1"]),
                WorkflowTask(name="task3", agent="agent_c", task="task", parameters={}, dependencies=["task2"])
            ]
        )
        
        order = workflow.get_execution_order()
        
        assert len(order) == 3
        assert order[0] == ["task1"]
        assert order[1] == ["task2"]
        assert order[2] == ["task3"]
    
    def test_workflow_execution_order_parallel(self):
        """Test execution order for parallel workflow"""
        workflow = WorkflowDefinition(
            name="parallel_workflow",
            tasks=[
                WorkflowTask(name="task1", agent="agent_a", task="task", parameters={}),
                WorkflowTask(name="task2", agent="agent_b", task="task", parameters={}, dependencies=["task1"]),
                WorkflowTask(name="task3", agent="agent_c", task="task", parameters={}, dependencies=["task1"]),
                WorkflowTask(name="task4", agent="agent_d", task="task", parameters={}, dependencies=["task2", "task3"])
            ]
        )
        
        order = workflow.get_execution_order()
        
        assert len(order) == 3
        assert order[0] == ["task1"]
        assert set(order[1]) == {"task2", "task3"}  # Can run in parallel
        assert order[2] == ["task4"]
    
    def test_workflow_circular_dependency(self):
        """Test workflow with circular dependency"""
        workflow = WorkflowDefinition(
            name="circular_workflow",
            tasks=[
                WorkflowTask(name="task1", agent="agent_a", task="task", parameters={}, dependencies=["task2"]),
                WorkflowTask(name="task2", agent="agent_b", task="task", parameters={}, dependencies=["task1"])
            ]
        )
        
        with pytest.raises(ValueError, match="Circular dependency"):
            workflow.get_execution_order()
    
    def test_workflow_complex_dag(self):
        """Test complex DAG workflow"""
        workflow = WorkflowDefinition(
            name="complex_workflow",
            tasks=[
                WorkflowTask(name="A", agent="agent", task="task", parameters={}),
                WorkflowTask(name="B", agent="agent", task="task", parameters={}, dependencies=["A"]),
                WorkflowTask(name="C", agent="agent", task="task", parameters={}, dependencies=["A"]),
                WorkflowTask(name="D", agent="agent", task="task", parameters={}, dependencies=["B"]),
                WorkflowTask(name="E", agent="agent", task="task", parameters={}, dependencies=["B", "C"]),
                WorkflowTask(name="F", agent="agent", task="task", parameters={}, dependencies=["D", "E"])
            ]
        )
        
        order = workflow.get_execution_order()
        
        # Verify execution order respects dependencies
        assert order[0] == ["A"]
        assert set(order[1]) == {"B", "C"}
        assert "D" in order[2] or "E" in order[2]
        assert "F" in order[-1]


# ============================================================================
# Agent Coordinator Tests
# ============================================================================

class TestAgentCoordinator:
    """Test A2A Agent Coordinator"""
    
    @pytest.mark.asyncio
    async def test_register_agent(self, coordinator, mock_agent):
        """Test registering an agent"""
        coordinator.register_agent(mock_agent)
        
        assert "test_agent" in coordinator.agents
        assert coordinator.agents["test_agent"].agent == mock_agent
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, coordinator, mock_agent):
        """Test unregistering an agent"""
        coordinator.register_agent(mock_agent)
        await coordinator.unregister_agent("test_agent")
        
        assert "test_agent" not in coordinator.agents
    
    @pytest.mark.asyncio
    async def test_discover_agents_by_capability(self, coordinator, mock_agent):
        """Test discovering agents by capability"""
        coordinator.register_agent(mock_agent)
        
        agents = coordinator.discover_agents_by_capability("test_task")
        
        assert len(agents) == 1
        assert agents[0] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_send_message(self, coordinator, mock_agent):
        """Test sending a message to an agent"""
        coordinator.register_agent(mock_agent)
        
        message = create_request_message(
            sender="coordinator",
            receiver="test_agent",
            task="test_task",
            parameters={"data": "hello"}
        )
        
        response = await coordinator.send_message(message)
        
        assert response.message_type == MessageType.RESPONSE
        assert "Processed: hello" in str(response.payload)
    
    @pytest.mark.asyncio
    async def test_send_message_agent_not_found(self, coordinator):
        """Test sending message to non-existent agent"""
        message = create_request_message(
            sender="coordinator",
            receiver="nonexistent_agent",
            task="test_task",
            parameters={"data": "hello"}
        )
        
        with pytest.raises(AgentNotFoundError):
            await coordinator.send_message(message)
    
    @pytest.mark.asyncio
    async def test_execute_workflow_simple(self, coordinator, mock_agent):
        """Test executing a simple workflow"""
        coordinator.register_agent(mock_agent)
        
        workflow = WorkflowDefinition(
            name="test_workflow",
            tasks=[
                WorkflowTask(
                    name="task1",
                    agent="test_agent",
                    task="test_task",
                    parameters={"data": "test"}
                )
            ]
        )
        
        result = await coordinator.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert "task1" in result["results"]
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_dependencies(self, coordinator):
        """Test executing workflow with dependencies"""
        # Create two agents
        agent1 = create_simple_agent(
            name="agent1",
            capabilities=[
                AgentCapability(
                    name="task1",
                    description="Task 1",
                    input_schema={},
                    output_schema={"value": "string"}
                )
            ],
            task_handlers={
                "task1": lambda: {"value": "result1"}
            }
        )
        
        agent2 = create_simple_agent(
            name="agent2",
            capabilities=[
                AgentCapability(
                    name="task2",
                    description="Task 2",
                    input_schema={"input": "string"},
                    output_schema={"value": "string"}
                )
            ],
            task_handlers={
                "task2": lambda input: {"value": f"result2_{input}"}
            }
        )
        
        coordinator.register_agent(agent1)
        coordinator.register_agent(agent2)
        
        workflow = WorkflowDefinition(
            name="dependent_workflow",
            tasks=[
                WorkflowTask(
                    name="task1",
                    agent="agent1",
                    task="task1",
                    parameters={}
                ),
                WorkflowTask(
                    name="task2",
                    agent="agent2",
                    task="task2",
                    parameters={"input": "test"},
                    dependencies=["task1"]
                )
            ]
        )
        
        result = await coordinator.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert "task1" in result["results"]
        assert "task2" in result["results"]
    
    @pytest.mark.asyncio
    async def test_load_balancing_round_robin(self, coordinator):
        """Test round-robin load balancing"""
        # Create multiple agents with same capability
        for i in range(3):
            agent = create_simple_agent(
                name=f"agent{i}",
                capabilities=[
                    AgentCapability(
                        name="shared_task",
                        description="Shared task",
                        input_schema={},
                        output_schema={}
                    )
                ],
                task_handlers={"shared_task": lambda: {"agent": i}}
            )
            coordinator.register_agent(agent)
        
        # Send multiple messages
        selected_agents = []
        for _ in range(6):
            agent = coordinator.select_agent_for_task(
                "shared_task",
                strategy=LoadBalancingStrategy.ROUND_ROBIN
            )
            selected_agents.append(agent)
        
        # Should cycle through agents
        assert selected_agents == ["agent0", "agent1", "agent2", "agent0", "agent1", "agent2"]
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, coordinator, mock_agent):
        """Test agent health monitoring"""
        coordinator.register_agent(mock_agent)
        
        # Check initial health
        assert coordinator.agents["test_agent"].status == AgentStatus.IDLE
        
        # Simulate heartbeat
        await coordinator.update_agent_heartbeat("test_agent")
        
        # Agent should still be healthy
        assert coordinator.agents["test_agent"].status == AgentStatus.IDLE


# ============================================================================
# Screenwriter Agent Tests
# ============================================================================

class TestScreenwriterAgent:
    """Test Screenwriter A2A Agent"""
    
    @pytest.fixture
    def screenwriter(self):
        """Create screenwriter agent"""
        return ScreenwriterA2AAgent(chat_model="gpt-4o-mini")
    
    def test_screenwriter_capabilities(self, screenwriter):
        """Test screenwriter capabilities"""
        capabilities = screenwriter.get_capabilities()
        
        assert len(capabilities) == 2
        
        cap_names = [cap.name for cap in capabilities]
        assert "develop_story" in cap_names
        assert "write_script" in cap_names
    
    def test_screenwriter_dependencies(self, screenwriter):
        """Test screenwriter has no dependencies"""
        deps = screenwriter.get_dependencies()
        assert len(deps) == 0
    
    @pytest.mark.asyncio
    async def test_screenwriter_develop_story(self, screenwriter):
        """Test story development (integration test - requires API key)"""
        # Skip if no API key
        pytest.skip("Requires OpenAI API key")
        
        message = create_request_message(
            sender="test",
            receiver="screenwriter",
            task="develop_story",
            parameters={
                "idea": "A robot learns to feel emotions",
                "user_requirement": "Short story for young adults, 3 scenes"
            }
        )
        
        response = await screenwriter.handle_message(message)
        
        assert response.message_type == MessageType.RESPONSE
        assert "story" in response.payload["result"]
    
    @pytest.mark.asyncio
    async def test_screenwriter_write_script(self, screenwriter):
        """Test script writing (integration test - requires API key)"""
        # Skip if no API key
        pytest.skip("Requires OpenAI API key")
        
        story = "A simple story about a robot discovering emotions."
        
        message = create_request_message(
            sender="test",
            receiver="screenwriter",
            task="write_script",
            parameters={
                "story": story,
                "user_requirement": "3 scenes"
            }
        )
        
        response = await screenwriter.handle_message(message)
        
        assert response.message_type == MessageType.RESPONSE
        assert "script" in response.payload["result"]
        assert isinstance(response.payload["result"]["script"], list)
    
    @pytest.mark.asyncio
    async def test_screenwriter_invalid_task(self, screenwriter):
        """Test handling invalid task"""
        message = create_request_message(
            sender="test",
            receiver="screenwriter",
            task="invalid_task",
            parameters={}
        )
        
        response = await screenwriter.handle_message(message)
        
        assert response.message_type == MessageType.ERROR
    
    @pytest.mark.asyncio
    async def test_screenwriter_missing_parameters(self, screenwriter):
        """Test handling missing parameters"""
        message = create_request_message(
            sender="test",
            receiver="screenwriter",
            task="develop_story",
            parameters={}  # Missing 'idea'
        )
        
        response = await screenwriter.handle_message(message)
        
        assert response.message_type == MessageType.ERROR
        assert "idea" in response.payload["error"].lower()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_screenwriter(self, coordinator):
        """Test complete workflow with screenwriter agent"""
        # Skip if no API key
        pytest.skip("Requires OpenAI API key")
        
        # Register screenwriter
        screenwriter = ScreenwriterA2AAgent(chat_model="gpt-4o-mini")
        await coordinator.register_agent(screenwriter)
        
        # Create workflow: develop story -> write script
        workflow = WorkflowDefinition(
            name="story_to_script",
            tasks=[
                WorkflowTask(
                    name="develop",
                    agent="screenwriter",
                    task="develop_story",
                    parameters={
                        "idea": "A time traveler's paradox",
                        "user_requirement": "Short story, 2 scenes"
                    }
                ),
                WorkflowTask(
                    name="script",
                    agent="screenwriter",
                    task="write_script",
                    parameters={
                        "story": "${develop.story}",  # Reference previous result
                        "user_requirement": "2 scenes"
                    },
                    dependencies=["develop"]
                )
            ]
        )
        
        result = await coordinator.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert "develop" in result["results"]
        assert "script" in result["results"]
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, coordinator):
        """Test parallel task execution"""
        # Create multiple independent agents
        for i in range(3):
            agent = create_simple_agent(
                name=f"worker{i}",
                capabilities=[
                    AgentCapability(
                        name="work",
                        description="Do work",
                        input_schema={},
                        output_schema={}
                    )
                ],
                task_handlers={
                    "work": lambda: asyncio.sleep(0.1) or {"done": True}
                }
            )
            await coordinator.register_agent(agent)
        
        # Create workflow with parallel tasks
        workflow = WorkflowDefinition(
            name="parallel_work",
            tasks=[
                WorkflowTask(name="work1", agent="worker0", task="work", parameters={}),
                WorkflowTask(name="work2", agent="worker1", task="work", parameters={}),
                WorkflowTask(name="work3", agent="worker2", task="work", parameters={})
            ]
        )
        
        import time
        start = time.time()
        result = await coordinator.execute_workflow(workflow)
        duration = time.time() - start
        
        # Should complete in ~0.1s (parallel) not ~0.3s (sequential)
        assert duration < 0.3
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, coordinator, mock_agent_error):
        """Test error handling in workflow execution"""
        await coordinator.register_agent(mock_agent_error)
        
        workflow = WorkflowDefinition(
            name="error_workflow",
            tasks=[
                WorkflowTask(
                    name="error_task",
                    agent="error_agent",
                    task="error_task",
                    parameters={"data": "test"}
                )
            ]
        )
        
        result = await coordinator.execute_workflow(workflow)
        
        assert result["status"] == "failed"
        assert "error_task" in result["errors"]


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_high_message_throughput(self, coordinator, mock_agent):
        """Test handling high message throughput"""
        await coordinator.register_agent(mock_agent)
        
        # Send 100 messages concurrently
        messages = [
            create_request_message(
                sender="test",
                receiver="test_agent",
                task="test_task",
                parameters={"data": f"test{i}"}
            )
            for i in range(100)
        ]
        
        import time
        start = time.time()
        responses = await asyncio.gather(*[
            coordinator.send_message(msg) for msg in messages
        ])
        duration = time.time() - start
        
        assert len(responses) == 100
        assert all(r.message_type == MessageType.RESPONSE for r in responses)
        print(f"Processed 100 messages in {duration:.2f}s ({100/duration:.1f} msg/s)")
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, coordinator):
        """Test executing multiple workflows concurrently"""
        # Create agent
        agent = create_simple_agent(
            name="worker",
            capabilities=[
                AgentCapability(
                    name="work",
                    description="Do work",
                    input_schema={},
                    output_schema={}
                )
            ],
            task_handlers={
                "work": lambda: asyncio.sleep(0.1) or {"done": True}
            }
        )
        await coordinator.register_agent(agent)
        
        # Create 10 workflows
        workflows = [
            WorkflowDefinition(
                name=f"workflow{i}",
                tasks=[
                    WorkflowTask(
                        name="task",
                        agent="worker",
                        task="work",
                        parameters={}
                    )
                ]
            )
            for i in range(10)
        ]
        
        import time
        start = time.time()
        results = await asyncio.gather(*[
            coordinator.execute_workflow(wf) for wf in workflows
        ])
        duration = time.time() - start
        
        assert len(results) == 10
        assert all(r["status"] == "completed" for r in results)
        print(f"Executed 10 workflows in {duration:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])