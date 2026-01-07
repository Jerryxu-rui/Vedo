"""
Enhanced WebSocket API Routes
Real-time communication for workflows, agents, and coordinator

Part of Week 3: Frontend WebSocket Integration - Phase 1
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional
import logging
import json
import uuid

from utils.websocket_manager import ws_manager
from services.progress_broadcaster import progress_broadcaster
from services.a2a_agent_coordinator import A2AAgentCoordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# Global coordinator instance (will be injected in main app)
coordinator: Optional[A2AAgentCoordinator] = None


def set_coordinator(coord: A2AAgentCoordinator):
    """Set the global coordinator instance"""
    global coordinator
    coordinator = coord


@router.websocket("/workflow/{workflow_id}")
async def workflow_progress_stream(
    websocket: WebSocket,
    workflow_id: str,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for workflow progress updates
    
    Clients connect to this endpoint to receive real-time progress updates
    for a specific workflow execution.
    
    Args:
        websocket: WebSocket connection
        workflow_id: Workflow ID to monitor
        client_id: Optional client ID (generated if not provided)
    
    Message Types Sent:
        - progress: Workflow progress updates
        - error: Error messages
        - complete: Workflow completion
    
    Message Types Received:
        - control: Workflow control commands (pause, resume, cancel)
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = f"workflow_{workflow_id}_{uuid.uuid4().hex[:8]}"
    
    # Create room name for this workflow
    room = f"workflow_{workflow_id}"
    
    try:
        # Connect client to WebSocket manager
        await ws_manager.connect(
            client_id,
            websocket,
            room=room,
            metadata={
                "type": "workflow",
                "workflow_id": workflow_id
            }
        )
        
        # Subscribe broadcaster to this workflow
        progress_broadcaster.subscribe_to_workflow(workflow_id, room)
        
        # Send buffered messages if any
        await progress_broadcaster.send_buffered_messages(room, client_id)
        
        # Send initial status if workflow exists
        if coordinator:
            try:
                status = coordinator.get_workflow_status(workflow_id)
                await ws_manager.send_personal_message(client_id, {
                    "type": "status",
                    "workflow_id": workflow_id,
                    "status": status
                })
            except ValueError:
                # Workflow not found, send pending status
                await ws_manager.send_personal_message(client_id, {
                    "type": "status",
                    "workflow_id": workflow_id,
                    "status": {"state": "pending", "message": "Workflow not started yet"}
                })
        
        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle control messages
                if message.get("type") == "control":
                    await handle_workflow_control(
                        workflow_id,
                        message.get("action"),
                        client_id
                    )
                
                # Handle ping
                elif message.get("type") == "ping":
                    await ws_manager.send_personal_message(client_id, {
                        "type": "pong"
                    })
            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {client_id}")
                await ws_manager.send_personal_message(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from workflow {workflow_id}")
    
    except Exception as e:
        logger.error(f"Error in workflow WebSocket for {workflow_id}: {e}")
    
    finally:
        # Cleanup
        ws_manager.disconnect(client_id)
        
        # Unsubscribe if no more clients in room
        if not ws_manager.get_room_clients(room):
            progress_broadcaster.unsubscribe_from_workflow(workflow_id)


@router.websocket("/agent/{agent_name}")
async def agent_status_stream(
    websocket: WebSocket,
    agent_name: str,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for agent status updates
    
    Clients connect to this endpoint to receive real-time status updates
    for a specific agent.
    
    Args:
        websocket: WebSocket connection
        agent_name: Agent name to monitor
        client_id: Optional client ID (generated if not provided)
    
    Message Types Sent:
        - agent_status: Agent status and metrics
        - error: Error messages
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = f"agent_{agent_name}_{uuid.uuid4().hex[:8]}"
    
    # Create room name for this agent
    room = f"agent_{agent_name}"
    
    try:
        # Connect client
        await ws_manager.connect(
            client_id,
            websocket,
            room=room,
            metadata={
                "type": "agent",
                "agent_name": agent_name
            }
        )
        
        # Subscribe broadcaster to this agent
        progress_broadcaster.subscribe_to_agent(agent_name, room)
        
        # Send initial agent status if available
        if coordinator:
            try:
                status = coordinator.get_agent_status(agent_name)
                await ws_manager.send_personal_message(client_id, {
                    "type": "agent_status",
                    "agent_name": agent_name,
                    "status": status
                })
            except Exception as e:
                logger.warning(f"Could not get status for agent {agent_name}: {e}")
        
        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping
                if message.get("type") == "ping":
                    await ws_manager.send_personal_message(client_id, {
                        "type": "pong"
                    })
            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {client_id}")
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from agent {agent_name}")
    
    except Exception as e:
        logger.error(f"Error in agent WebSocket for {agent_name}: {e}")
    
    finally:
        # Cleanup
        ws_manager.disconnect(client_id)
        
        # Unsubscribe if no more clients in room
        if not ws_manager.get_room_clients(room):
            progress_broadcaster.unsubscribe_from_agent(agent_name, room)


@router.websocket("/coordinator")
async def coordinator_metrics_stream(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for coordinator metrics
    
    Clients connect to this endpoint to receive real-time metrics
    about the A2A coordinator (agent registry, workflow execution, etc.)
    
    Args:
        websocket: WebSocket connection
        client_id: Optional client ID (generated if not provided)
    
    Message Types Sent:
        - coordinator_metrics: Coordinator performance metrics
        - error: Error messages
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = f"coordinator_{uuid.uuid4().hex[:8]}"
    
    # Use global coordinator room
    room = "coordinator_metrics"
    
    try:
        # Connect client
        await ws_manager.connect(
            client_id,
            websocket,
            room=room,
            metadata={
                "type": "coordinator"
            }
        )
        
        # Subscribe to coordinator
        progress_broadcaster.subscribe_to_coordinator(room)
        
        # Send initial metrics if coordinator available
        if coordinator:
            try:
                metrics = coordinator.get_coordinator_metrics()
                await ws_manager.send_personal_message(client_id, {
                    "type": "coordinator_metrics",
                    **metrics
                })
            except Exception as e:
                logger.warning(f"Could not get coordinator metrics: {e}")
        
        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping
                if message.get("type") == "ping":
                    await ws_manager.send_personal_message(client_id, {
                        "type": "pong"
                    })
                
                # Handle metrics request
                elif message.get("type") == "get_metrics":
                    if coordinator:
                        metrics = coordinator.get_coordinator_metrics()
                        await ws_manager.send_personal_message(client_id, {
                            "type": "coordinator_metrics",
                            **metrics
                        })
            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {client_id}")
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from coordinator")
    
    except Exception as e:
        logger.error(f"Error in coordinator WebSocket: {e}")
    
    finally:
        # Cleanup
        ws_manager.disconnect(client_id)


# ==================== Helper Functions ====================

async def handle_workflow_control(
    workflow_id: str,
    action: str,
    client_id: str
):
    """
    Handle workflow control commands
    
    Args:
        workflow_id: Workflow ID
        action: Control action (pause, resume, cancel)
        client_id: Client ID making the request
    """
    if not coordinator:
        await ws_manager.send_personal_message(client_id, {
            "type": "error",
            "message": "Coordinator not available"
        })
        return
    
    try:
        if action == "cancel":
            coordinator.cancel_workflow(workflow_id)
            await ws_manager.send_personal_message(client_id, {
                "type": "control_response",
                "action": action,
                "status": "success",
                "message": f"Workflow {workflow_id} cancelled"
            })
        
        elif action == "pause":
            # TODO: Implement pause functionality
            await ws_manager.send_personal_message(client_id, {
                "type": "control_response",
                "action": action,
                "status": "not_implemented",
                "message": "Pause functionality not yet implemented"
            })
        
        elif action == "resume":
            # TODO: Implement resume functionality
            await ws_manager.send_personal_message(client_id, {
                "type": "control_response",
                "action": action,
                "status": "not_implemented",
                "message": "Resume functionality not yet implemented"
            })
        
        else:
            await ws_manager.send_personal_message(client_id, {
                "type": "error",
                "message": f"Unknown action: {action}"
            })
    
    except Exception as e:
        logger.error(f"Error handling workflow control: {e}")
        await ws_manager.send_personal_message(client_id, {
            "type": "error",
            "message": f"Control action failed: {str(e)}"
        })


# ==================== Status Endpoints ====================

@router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket statistics
    
    Returns:
        Dictionary with WebSocket and broadcaster statistics
    """
    return {
        "websocket": ws_manager.get_stats(),
        "broadcaster": progress_broadcaster.get_stats()
    }


@router.get("/client/{client_id}")
async def get_client_info(client_id: str):
    """
    Get information about a specific client
    
    Args:
        client_id: Client ID
    
    Returns:
        Client information dictionary
    """
    info = ws_manager.get_client_info(client_id)
    if not info:
        raise HTTPException(status_code=404, detail="Client not found")
    return info