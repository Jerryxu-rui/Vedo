"""
WebSocket Manager
WebSocket连接管理和实时进度推送
"""

from typing import Dict, Set, Optional, Any, Callable
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    PROGRESS = "progress"
    STATUS = "status"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    COMPLETE = "complete"
    HEARTBEAT = "heartbeat"


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 订阅关系: {topic: Set[client_id]}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # 心跳任务
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        # 消息历史: {topic: List[message]}
        self.message_history: Dict[str, list] = {}
        self.max_history_size = 100
    
    async def connect(self, client_id: str, websocket: WebSocket):
        """
        连接客户端
        
        Args:
            client_id: 客户端ID
            websocket: WebSocket连接
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # 启动心跳
        self.heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat(client_id)
        )
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # 发送欢迎消息
        await self.send_personal_message(
            client_id,
            {
                "type": MessageType.INFO.value,
                "message": "Connected to ViMax WebSocket server",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def disconnect(self, client_id: str):
        """
        断开客户端连接
        
        Args:
            client_id: 客户端ID
        """
        # 取消心跳任务
        if client_id in self.heartbeat_tasks:
            self.heartbeat_tasks[client_id].cancel()
            del self.heartbeat_tasks[client_id]
        
        # 移除连接
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 取消所有订阅
        for topic in list(self.subscriptions.keys()):
            if client_id in self.subscriptions[topic]:
                self.subscriptions[topic].remove(client_id)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
        
        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """
        发送个人消息
        
        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        广播消息给所有连接
        
        Args:
            message: 消息内容
        """
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def subscribe(self, client_id: str, topic: str):
        """
        订阅主题
        
        Args:
            client_id: 客户端ID
            topic: 主题名称
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        
        self.subscriptions[topic].add(client_id)
        logger.info(f"Client {client_id} subscribed to topic: {topic}")
        
        # 发送历史消息
        if topic in self.message_history:
            asyncio.create_task(
                self._send_history(client_id, topic)
            )
    
    def unsubscribe(self, client_id: str, topic: str):
        """
        取消订阅主题
        
        Args:
            client_id: 客户端ID
            topic: 主题名称
        """
        if topic in self.subscriptions and client_id in self.subscriptions[topic]:
            self.subscriptions[topic].remove(client_id)
            
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
            
            logger.info(f"Client {client_id} unsubscribed from topic: {topic}")
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """
        发布消息到主题
        
        Args:
            topic: 主题名称
            message: 消息内容
        """
        # 添加时间戳
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # 保存到历史
        if topic not in self.message_history:
            self.message_history[topic] = []
        
        self.message_history[topic].append(message)
        
        # 限制历史大小
        if len(self.message_history[topic]) > self.max_history_size:
            self.message_history[topic] = self.message_history[topic][-self.max_history_size:]
        
        # 发送给订阅者（如果有的话）
        if topic in self.subscriptions and self.subscriptions[topic]:
            disconnected_clients = []
            
            for client_id in list(self.subscriptions[topic]):  # Use list() to avoid modification during iteration
                if client_id in self.active_connections:
                    try:
                        websocket = self.active_connections[client_id]
                        # Check if websocket is still connected
                        if websocket.client_state.name == "CONNECTED":
                            await websocket.send_json(message)
                        else:
                            logger.warning(f"WebSocket for {client_id} is not connected (state: {websocket.client_state.name})")
                            disconnected_clients.append(client_id)
                    except RuntimeError as e:
                        if "WebSocket is not connected" in str(e):
                            logger.debug(f"WebSocket for {client_id} already disconnected, skipping")
                            disconnected_clients.append(client_id)
                        else:
                            logger.error(f"Error publishing to {client_id}: {e}")
                            disconnected_clients.append(client_id)
                    except Exception as e:
                        logger.error(f"Error publishing to {client_id}: {e}")
                        disconnected_clients.append(client_id)
            
            # 清理断开的连接
            for client_id in disconnected_clients:
                self.disconnect(client_id)
        else:
            # No subscribers, just log at debug level
            logger.debug(f"No subscribers for topic: {topic}, message saved to history")
    
    async def send_progress(
        self,
        topic: str,
        percentage: float,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        发送进度更新
        
        Args:
            topic: 主题名称
            percentage: 进度百分比 (0.0-1.0)
            message: 进度消息
            details: 额外详情
        """
        await self.publish(topic, {
            "type": MessageType.PROGRESS.value,
            "percentage": percentage,
            "message": message,
            "details": details or {}
        })
    
    async def send_status(
        self,
        topic: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        发送状态更新
        
        Args:
            topic: 主题名称
            status: 状态值
            message: 状态消息
            details: 额外详情
        """
        await self.publish(topic, {
            "type": MessageType.STATUS.value,
            "status": status,
            "message": message,
            "details": details or {}
        })
    
    async def send_error(
        self,
        topic: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ):
        """
        发送错误消息
        
        Args:
            topic: 主题名称
            error_message: 错误消息
            error_details: 错误详情
        """
        await self.publish(topic, {
            "type": MessageType.ERROR.value,
            "message": error_message,
            "details": error_details or {}
        })
    
    async def send_warning(
        self,
        topic: str,
        warning_message: str,
        warning_details: Optional[Dict[str, Any]] = None
    ):
        """
        发送警告消息
        
        Args:
            topic: 主题名称
            warning_message: 警告消息
            warning_details: 警告详情
        """
        await self.publish(topic, {
            "type": MessageType.WARNING.value,
            "message": warning_message,
            "details": warning_details or {}
        })
    
    async def send_completion(
        self,
        topic: str,
        message: str,
        result: Optional[Dict[str, Any]] = None
    ):
        """
        发送完成消息
        
        Args:
            topic: 主题名称
            message: 完成消息
            result: 结果数据
        """
        await self.publish(topic, {
            "type": MessageType.COMPLETE.value,
            "message": message,
            "result": result or {}
        })
    
    async def _heartbeat(self, client_id: str):
        """
        心跳任务
        
        Args:
            client_id: 客户端ID
        """
        try:
            while True:
                await asyncio.sleep(30)  # 每30秒发送一次心跳
                
                if client_id in self.active_connections:
                    try:
                        await self.active_connections[client_id].send_json({
                            "type": MessageType.HEARTBEAT.value,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Heartbeat failed for {client_id}: {e}")
                        self.disconnect(client_id)
                        break
                else:
                    break
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat task cancelled for {client_id}")
    
    async def _send_history(self, client_id: str, topic: str):
        """
        发送历史消息
        
        Args:
            client_id: 客户端ID
            topic: 主题名称
        """
        if topic in self.message_history and client_id in self.active_connections:
            try:
                # 发送历史消息标记
                await self.send_personal_message(client_id, {
                    "type": MessageType.INFO.value,
                    "message": f"Sending {len(self.message_history[topic])} historical messages for topic: {topic}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # 发送历史消息
                for message in self.message_history[topic]:
                    await self.send_personal_message(client_id, message)
                    await asyncio.sleep(0.01)  # 避免消息过快
                
            except Exception as e:
                logger.error(f"Error sending history to {client_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "topics": list(self.subscriptions.keys()),
            "topic_subscriber_count": {
                topic: len(subs) for topic, subs in self.subscriptions.items()
            }
        }


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()


class ProgressWebSocketCallback:
    """
    进度回调的WebSocket适配器
    将ProgressCallback的更新转发到WebSocket
    """
    
    def __init__(self, topic: str, manager: WebSocketManager = ws_manager):
        """
        Args:
            topic: WebSocket主题
            manager: WebSocket管理器
        """
        self.topic = topic
        self.manager = manager
    
    async def update(self, percentage: float, message: str):
        """
        更新进度 (ProgressCallback接口)
        
        Args:
            percentage: 进度百分比 (0.0-1.0)
            message: 进度消息
        """
        await self.manager.send_progress(
            self.topic,
            percentage,
            message
        )
    
    async def __call__(self, percentage: float, message: str):
        """
        进度回调
        
        Args:
            percentage: 进度百分比 (0.0-1.0)
            message: 进度消息
        """
        await self.update(percentage, message)


def create_progress_websocket_callback(
    topic: str,
    manager: WebSocketManager = ws_manager
) -> Callable:
    """
    创建进度WebSocket回调
    
    Args:
        topic: WebSocket主题
        manager: WebSocket管理器
    
    Returns:
        异步回调函数
    """
    callback = ProgressWebSocketCallback(topic, manager)
    return callback