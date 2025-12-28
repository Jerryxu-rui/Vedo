"""
WebSocket API Routes
WebSocket实时通信端点
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import logging

from utils.websocket_manager import ws_manager

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None, description="Client ID for reconnection")
):
    """
    WebSocket连接端点
    
    客户端可以通过此端点建立WebSocket连接，接收实时更新。
    
    连接后，客户端可以发送订阅消息来订阅特定主题：
    ```json
    {
        "action": "subscribe",
        "topic": "episode/{episode_id}"
    }
    ```
    
    取消订阅：
    ```json
    {
        "action": "unsubscribe",
        "topic": "episode/{episode_id}"
    }
    ```
    
    消息格式：
    - progress: 进度更新
    - status: 状态更新
    - error: 错误消息
    - warning: 警告消息
    - info: 信息消息
    - complete: 完成消息
    - heartbeat: 心跳消息
    """
    # 生成客户端ID
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
    
    try:
        # 连接客户端
        await ws_manager.connect(client_id, websocket)
        
        # 处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_json()
                
                action = data.get("action")
                topic = data.get("topic")
                
                if action == "subscribe" and topic:
                    ws_manager.subscribe(client_id, topic)
                    await ws_manager.send_personal_message(client_id, {
                        "type": "info",
                        "message": f"Subscribed to topic: {topic}"
                    })
                
                elif action == "unsubscribe" and topic:
                    ws_manager.unsubscribe(client_id, topic)
                    await ws_manager.send_personal_message(client_id, {
                        "type": "info",
                        "message": f"Unsubscribed from topic: {topic}"
                    })
                
                elif action == "ping":
                    await ws_manager.send_personal_message(client_id, {
                        "type": "info",
                        "message": "pong"
                    })
                
                else:
                    await ws_manager.send_personal_message(client_id, {
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
            
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
                break
            
            except RuntimeError as e:
                # Handle "WebSocket is not connected" error specifically
                if "WebSocket is not connected" in str(e):
                    logger.info(f"Client {client_id} WebSocket connection lost: {e}")
                    break
                else:
                    logger.error(f"Runtime error processing message from {client_id}: {e}")
                    await ws_manager.send_personal_message(client_id, {
                        "type": "error",
                        "message": f"Runtime error: {str(e)}"
                    })
            
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")
                await ws_manager.send_personal_message(client_id, {
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                })
    
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    
    finally:
        ws_manager.disconnect(client_id)


@router.get("/stats")
async def get_websocket_stats():
    """
    获取WebSocket统计信息
    
    返回当前连接数、订阅数等信息
    """
    return ws_manager.get_stats()


@router.post("/broadcast")
async def broadcast_message(message: dict):
    """
    广播消息给所有连接的客户端
    
    仅用于测试和管理目的
    """
    await ws_manager.broadcast(message)
    return {"message": "Broadcast sent", "recipients": len(ws_manager.active_connections)}


@router.post("/publish/{topic}")
async def publish_to_topic(topic: str, message: dict):
    """
    发布消息到特定主题
    
    仅用于测试和管理目的
    """
    await ws_manager.publish(topic, message)
    subscriber_count = len(ws_manager.subscriptions.get(topic, set()))
    return {
        "message": "Message published",
        "topic": topic,
        "subscribers": subscriber_count
    }