"""
Progress Broadcaster Service
Bridges A2A Coordinator events to WebSocket clients

Part of Week 3: Frontend WebSocket Integration - Phase 1
"""

from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime
import asyncio
import logging
from collections import defaultdict

from utils.websocket_manager import WebSocketManager, ws_manager

logger = logging.getLogger(__name__)


class ProgressBroadcaster:
    """
    Progress Broadcaster Service
    
    Subscribes to A2A Coordinator events and broadcasts them to WebSocket clients.
    Provides room-based routing for efficient message delivery.
    """
    
    def __init__(self, ws_manager: WebSocketManager = ws_manager):
        """
        Initialize Progress Broadcaster
        
        Args:
            ws_manager: WebSocket manager instance
        """
        self.ws_manager = ws_manager
        
        # Workflow subscriptions: {workflow_id: room_name}
        self.workflow_rooms: Dict[str, str] = {}
        
        # Agent subscriptions: {agent_name: Set[room_name]}
        self.agent_rooms: Dict[str, Set[str]] = defaultdict(set)
        
        # Coordinator room (for global metrics)
        self.coordinator_room = "coordinator_metrics"
        
        # Message buffer for disconnected clients: {room: List[message]}
        self.message_buffer: Dict[str, list] = defaultdict(list)
        self.max_buffer_size = 50
        
        logger.info("Progress Broadcaster initialized")
    
    # ==================== Subscription Management ====================
    
    def subscribe_to_workflow(self, workflow_id: str, room: str):
        """
        Subscribe a room to workflow updates
        
        Args:
            workflow_id: Workflow ID to monitor
            room: Room name to broadcast to
        """
        self.workflow_rooms[workflow_id] = room
        logger.info(f"Room '{room}' subscribed to workflow: {workflow_id}")
    
    def unsubscribe_from_workflow(self, workflow_id: str):
        """
        Unsubscribe from workflow updates
        
        Args:
            workflow_id: Workflow ID
        """
        if workflow_id in self.workflow_rooms:
            room = self.workflow_rooms[workflow_id]
            del self.workflow_rooms[workflow_id]
            logger.info(f"Room '{room}' unsubscribed from workflow: {workflow_id}")
    
    def subscribe_to_agent(self, agent_name: str, room: str):
        """
        Subscribe a room to agent status updates
        
        Args:
            agent_name: Agent name to monitor
            room: Room name to broadcast to
        """
        self.agent_rooms[agent_name].add(room)
        logger.info(f"Room '{room}' subscribed to agent: {agent_name}")
    
    def unsubscribe_from_agent(self, agent_name: str, room: str):
        """
        Unsubscribe from agent updates
        
        Args:
            agent_name: Agent name
            room: Room name
        """
        if agent_name in self.agent_rooms:
            self.agent_rooms[agent_name].discard(room)
            if not self.agent_rooms[agent_name]:
                del self.agent_rooms[agent_name]
            logger.info(f"Room '{room}' unsubscribed from agent: {agent_name}")
    
    def subscribe_to_coordinator(self, room: str):
        """
        Subscribe a room to coordinator metrics
        
        Args:
            room: Room name to broadcast to
        """
        # Coordinator uses a single global room
        logger.info(f"Room '{room}' subscribed to coordinator metrics")
    
    # ==================== Broadcasting Methods ====================
    
    async def broadcast_progress(
        self,
        workflow_id: str,
        progress_data: Dict[str, Any]
    ):
        """
        Broadcast workflow progress update
        
        Args:
            workflow_id: Workflow ID
            progress_data: Progress information
        """
        if workflow_id not in self.workflow_rooms:
            logger.debug(f"No room subscribed to workflow: {workflow_id}")
            return
        
        room = self.workflow_rooms[workflow_id]
        
        message = {
            "type": "progress",
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            **progress_data
        }
        
        # Broadcast to room
        await self._broadcast_to_room(room, message)
    
    async def broadcast_workflow_state(
        self,
        workflow_id: str,
        state: str,
        progress: float = 0.0,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast workflow state change
        
        Args:
            workflow_id: Workflow ID
            state: Workflow state (pending, running, completed, failed)
            progress: Progress value (0.0 to 1.0)
            stage: Current stage name
            message: Human-readable message
            details: Additional details
        """
        progress_data = {
            "state": state,
            "progress": progress,
            "stage": stage,
            "message": message,
            "details": details or {}
        }
        
        await self.broadcast_progress(workflow_id, progress_data)
    
    async def broadcast_agent_status(
        self,
        agent_name: str,
        status_data: Dict[str, Any]
    ):
        """
        Broadcast agent status update
        
        Args:
            agent_name: Agent name
            status_data: Status information
        """
        if agent_name not in self.agent_rooms:
            logger.debug(f"No rooms subscribed to agent: {agent_name}")
            return
        
        message = {
            "type": "agent_status",
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            **status_data
        }
        
        # Broadcast to all subscribed rooms
        for room in self.agent_rooms[agent_name]:
            await self._broadcast_to_room(room, message)
    
    async def broadcast_coordinator_metrics(
        self,
        metrics: Dict[str, Any]
    ):
        """
        Broadcast coordinator metrics
        
        Args:
            metrics: Coordinator metrics
        """
        message = {
            "type": "coordinator_metrics",
            "timestamp": datetime.utcnow().isoformat(),
            **metrics
        }
        
        # Broadcast to coordinator room
        await self._broadcast_to_room(self.coordinator_room, message)
    
    async def broadcast_error(
        self,
        target_type: str,
        target_id: str,
        error_message: str,
        error_type: str = "Error",
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast error message
        
        Args:
            target_type: Type of target (workflow, agent, coordinator)
            target_id: Target ID (workflow_id or agent_name)
            error_message: Error description
            error_type: Error type
            retryable: Whether error is retryable
            details: Additional error details
        """
        message = {
            "type": "error",
            "target_type": target_type,
            "target_id": target_id,
            "message": error_message,
            "error_type": error_type,
            "retryable": retryable,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Determine room based on target type
        room = None
        if target_type == "workflow" and target_id in self.workflow_rooms:
            room = self.workflow_rooms[target_id]
        elif target_type == "agent" and target_id in self.agent_rooms:
            # Broadcast to all rooms subscribed to this agent
            for agent_room in self.agent_rooms[target_id]:
                await self._broadcast_to_room(agent_room, message)
            return
        elif target_type == "coordinator":
            room = self.coordinator_room
        
        if room:
            await self._broadcast_to_room(room, message)
    
    # ==================== Internal Methods ====================
    
    async def _broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """
        Internal method to broadcast message to room
        
        Args:
            room: Room name
            message: Message to broadcast
        """
        try:
            # Get clients in room
            clients = self.ws_manager.get_room_clients(room)
            
            if not clients:
                # No clients, buffer the message
                self._buffer_message(room, message)
                logger.debug(f"No clients in room '{room}', message buffered")
                return
            
            # Broadcast to room
            await self.ws_manager.broadcast_to_room(room, message)
            logger.debug(f"Broadcasted message to room '{room}' ({len(clients)} clients)")
        
        except Exception as e:
            logger.error(f"Error broadcasting to room '{room}': {e}")
    
    def _buffer_message(self, room: str, message: Dict[str, Any]):
        """
        Buffer message for disconnected clients
        
        Args:
            room: Room name
            message: Message to buffer
        """
        self.message_buffer[room].append(message)
        
        # Limit buffer size
        if len(self.message_buffer[room]) > self.max_buffer_size:
            self.message_buffer[room] = self.message_buffer[room][-self.max_buffer_size:]
    
    async def send_buffered_messages(self, room: str, client_id: str):
        """
        Send buffered messages to a client
        
        Args:
            room: Room name
            client_id: Client ID
        """
        if room not in self.message_buffer:
            return
        
        messages = self.message_buffer[room]
        if not messages:
            return
        
        logger.info(f"Sending {len(messages)} buffered messages to client {client_id}")
        
        try:
            for message in messages:
                await self.ws_manager.send_personal_message(client_id, message)
                await asyncio.sleep(0.01)  # Avoid flooding
        
        except Exception as e:
            logger.error(f"Error sending buffered messages to {client_id}: {e}")
    
    def clear_buffer(self, room: str):
        """
        Clear message buffer for a room
        
        Args:
            room: Room name
        """
        if room in self.message_buffer:
            del self.message_buffer[room]
            logger.debug(f"Cleared message buffer for room: {room}")
    
    # ==================== Callback Factories ====================
    
    def create_workflow_callback(self, workflow_id: str) -> Callable:
        """
        Create a progress callback for a workflow
        
        Args:
            workflow_id: Workflow ID
        
        Returns:
            Async callback function
        """
        async def callback(progress_data: Dict[str, Any]):
            await self.broadcast_progress(workflow_id, progress_data)
        
        return callback
    
    def create_agent_callback(self, agent_name: str) -> Callable:
        """
        Create a status callback for an agent
        
        Args:
            agent_name: Agent name
        
        Returns:
            Async callback function
        """
        async def callback(status_data: Dict[str, Any]):
            await self.broadcast_agent_status(agent_name, status_data)
        
        return callback
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broadcaster statistics"""
        return {
            "workflow_subscriptions": len(self.workflow_rooms),
            "agent_subscriptions": len(self.agent_rooms),
            "total_agent_rooms": sum(len(rooms) for rooms in self.agent_rooms.values()),
            "buffered_rooms": len(self.message_buffer),
            "total_buffered_messages": sum(len(msgs) for msgs in self.message_buffer.values()),
            "workflows": list(self.workflow_rooms.keys()),
            "agents": list(self.agent_rooms.keys())
        }


# Global Progress Broadcaster instance
progress_broadcaster = ProgressBroadcaster()


# Helper functions for easy access

async def broadcast_workflow_progress(
    workflow_id: str,
    state: str,
    progress: float = 0.0,
    stage: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Helper function to broadcast workflow progress
    
    Args:
        workflow_id: Workflow ID
        state: Workflow state
        progress: Progress value (0.0 to 1.0)
        stage: Current stage
        message: Progress message
        details: Additional details
    """
    await progress_broadcaster.broadcast_workflow_state(
        workflow_id, state, progress, stage, message, details
    )


async def broadcast_agent_update(
    agent_name: str,
    status: str,
    metrics: Optional[Dict[str, Any]] = None
):
    """
    Helper function to broadcast agent status
    
    Args:
        agent_name: Agent name
        status: Agent status
        metrics: Performance metrics
    """
    await progress_broadcaster.broadcast_agent_status(
        agent_name,
        {
            "status": status,
            "metrics": metrics or {}
        }
    )