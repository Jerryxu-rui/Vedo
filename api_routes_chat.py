"""
API Routes for Chat and LLM Interactions
Handles conversation threads, streaming chat, and agent orchestration
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_db
from services.chat_service import ChatService
from services.agent_orchestrator import AgentOrchestrator, AgentType
from services.llm_registry import LLMRegistry
from database_models import ConversationThread, ConversationMessage, LLMAPIKey
from datetime import datetime
import json
import asyncio

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# Request/Response Models

class CreateThreadRequest(BaseModel):
    """Request to create a new conversation thread"""
    user_id: str
    llm_model: str
    episode_id: Optional[str] = None
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    message: str
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    stream: Optional[bool] = False


class IntentClassificationRequest(BaseModel):
    """Request to classify user intent"""
    message: str
    model: str = "gemini-2.5-flash"
    context: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    """Request to start a multi-agent workflow"""
    user_id: str
    llm_model: str
    user_request: str
    episode_id: Optional[str] = None


class AddAPIKeyRequest(BaseModel):
    """Request to add an LLM API key"""
    provider: str
    api_key: str
    api_endpoint: Optional[str] = None


# Endpoints

@router.get("/models")
async def get_available_llm_models():
    """Get all available LLM models"""
    try:
        llm_registry = LLMRegistry()
        models = llm_registry.list_all_models()
        return {
            "models": models,
            "default_model": llm_registry.get_default_model()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch LLM models: {str(e)}")


@router.post("/classify-intent")
async def classify_intent(request: IntentClassificationRequest, db: Session = Depends(get_db)):
    """
    使用LLM进行意图分类（使用新的LLM Intent Analyzer）
    
    快速、准确地判断用户意图：对话 vs 视频生成
    包含内容验证，确保视频生成请求有足够的细节
    """
    try:
        from services.intent_analyzer_llm import LLMIntentAnalyzer, IntentType
        
        analyzer = LLMIntentAnalyzer(db)
        
        # 使用新的LLM分析器
        intent = await analyzer.analyze(
            user_input=request.message,
            context=request.context or {}
        )
        
        # 转换为API响应格式
        response_data = {
            "intent": "video_generation" if intent.type == IntentType.VIDEO_GENERATION else "chat",
            "confidence": intent.confidence,
            "reasoning": intent.reasoning,
            "model_used": request.model,
            "original_message": request.message
        }
        
        # 如果有内容验证信息，添加到响应中
        if intent.content_validation:
            response_data["content_validation"] = {
                "is_valid": intent.content_validation.is_valid,
                "has_subject": intent.content_validation.has_subject,
                "has_action": intent.content_validation.has_action,
                "has_context": intent.content_validation.has_context,
                "missing_elements": intent.content_validation.missing_elements,
                "suggestions": intent.content_validation.suggestions
            }
        
        # 如果需要澄清，添加提示
        if intent.parameters.get("needs_clarification"):
            response_data["needs_clarification"] = True
            response_data["clarification_message"] = "请提供更多视频创意的细节"
        
        return response_data
        
    except ValueError as e:
        # API key configuration error
        error_msg = str(e)
        if "API keys" in error_msg or "API key" in error_msg or "YUNWU_API_KEY" in error_msg:
            print(f"[Intent Classification] API Key Error: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "api_key_required",
                    "message": "LLM API密钥未配置。请设置 YUNWU_API_KEY 环境变量。",
                    "message_en": "LLM API key not configured. Please set YUNWU_API_KEY environment variable.",
                    "action_required": "set_environment_variable",
                    "env_var_name": "YUNWU_API_KEY",
                    "details": str(e)
                }
            )
        else:
            raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        print(f"[Intent Classification] Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Intent classification failed: {str(e)}"
        )


@router.post("/threads")
async def create_thread(request: CreateThreadRequest, db: Session = Depends(get_db)):
    """Create a new conversation thread"""
    try:
        print(f"[CreateThread] Request: user_id={request.user_id}, model={request.llm_model}")
        chat_service = ChatService(db)
        thread = await chat_service.create_thread(
            user_id=request.user_id,
            llm_model=request.llm_model,
            episode_id=request.episode_id,
            title=request.title,
            system_prompt=request.system_prompt
        )
        print(f"[CreateThread] Success: thread_id={thread.id}")
        return thread.to_dict()
    except ValueError as e:
        print(f"[CreateThread] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[CreateThread] Exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}")


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, db: Session = Depends(get_db)):
    """Get conversation thread details"""
    try:
        thread = db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        return thread.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread: {str(e)}")


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get messages from a conversation thread"""
    try:
        chat_service = ChatService(db)
        messages = await chat_service.get_thread_messages(thread_id, limit)
        return {
            "thread_id": thread_id,
            "messages": [msg.to_dict() for msg in messages],
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a message and get response (non-streaming)"""
    try:
        chat_service = ChatService(db)
        
        if request.stream:
            raise HTTPException(
                status_code=400,
                detail="Use /threads/{thread_id}/stream endpoint for streaming responses"
            )
        
        response = await chat_service.chat(
            thread_id=thread_id,
            user_message=request.message,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return {
            "thread_id": thread_id,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.post("/threads/{thread_id}/stream")
async def stream_message(
    thread_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a message and stream the response"""
    try:
        chat_service = ChatService(db)
        
        async def generate():
            try:
                async for chunk in chat_service.stream_chat(
                    thread_id=thread_id,
                    user_message=request.message,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    # Send as Server-Sent Events format
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                # Send completion signal
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream message: {str(e)}")


@router.post("/workflows")
async def create_workflow(request: WorkflowRequest, db: Session = Depends(get_db)):
    """Create and start a multi-agent workflow"""
    try:
        orchestrator = AgentOrchestrator(db)
        thread = await orchestrator.create_workflow(
            user_id=request.user_id,
            llm_model=request.llm_model,
            user_request=request.user_request,
            episode_id=request.episode_id
        )
        return {
            "thread_id": thread.id,
            "status": "created",
            "message": "Workflow created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@router.post("/workflows/{thread_id}/execute")
async def execute_workflow(
    thread_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Execute a multi-agent workflow with streaming updates"""
    try:
        orchestrator = AgentOrchestrator(db)
        
        async def generate():
            try:
                async for update in orchestrator.execute_workflow(
                    thread_id=thread_id,
                    user_request=request.message
                ):
                    # Send workflow updates as Server-Sent Events
                    yield f"data: {json.dumps(update)}\n\n"
                    await asyncio.sleep(0.1)  # Small delay for better streaming
            except Exception as e:
                yield f"data: {json.dumps({'stage': 'error', 'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")


@router.get("/workflows/{thread_id}/status")
async def get_workflow_status(thread_id: str, db: Session = Depends(get_db)):
    """Get current status of a workflow"""
    try:
        orchestrator = AgentOrchestrator(db)
        status = await orchestrator.get_workflow_status(thread_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")


@router.post("/workflows/{thread_id}/cancel")
async def cancel_workflow(thread_id: str, db: Session = Depends(get_db)):
    """Cancel an ongoing workflow"""
    try:
        orchestrator = AgentOrchestrator(db)
        await orchestrator.cancel_workflow(thread_id)
        return {
            "thread_id": thread_id,
            "status": "cancelled",
            "message": "Workflow cancelled successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")


@router.post("/api-keys")
async def add_api_key(
    request: AddAPIKeyRequest,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Add or update an LLM API key for a user"""
    try:
        # Check if key already exists
        existing_key = db.query(LLMAPIKey).filter(
            LLMAPIKey.user_id == user_id,
            LLMAPIKey.provider == request.provider
        ).first()
        
        if existing_key:
            # Update existing key
            existing_key.api_key = request.api_key
            existing_key.api_endpoint = request.api_endpoint
            existing_key.is_active = True
            existing_key.updated_at = datetime.utcnow()
        else:
            # Create new key
            new_key = LLMAPIKey(
                user_id=user_id,
                provider=request.provider,
                api_key=request.api_key,
                api_endpoint=request.api_endpoint,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_key)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"API key for {request.provider} added successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add API key: {str(e)}")


@router.get("/api-keys")
async def get_api_keys(user_id: str, db: Session = Depends(get_db)):
    """Get all API keys for a user (masked)"""
    try:
        keys = db.query(LLMAPIKey).filter(
            LLMAPIKey.user_id == user_id
        ).all()
        
        return {
            "api_keys": [key.to_dict() for key in keys]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch API keys: {str(e)}")


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, db: Session = Depends(get_db)):
    """Delete an API key"""
    try:
        key = db.query(LLMAPIKey).filter(LLMAPIKey.id == key_id).first()
        
        if not key:
            raise HTTPException(status_code=404, detail=f"API key not found: {key_id}")
        
        db.delete(key)
        db.commit()
        
        return {
            "status": "success",
            "message": "API key deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete API key: {str(e)}")


# WebSocket endpoint for real-time chat
@router.websocket("/ws/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: str, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    try:
        chat_service = ChatService(db)
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get('message', '')
            temperature = data.get('temperature', 0.7)
            
            if not message:
                continue
            
            # Stream response
            try:
                async for chunk in chat_service.stream_chat(
                    thread_id=thread_id,
                    user_message=message,
                    temperature=temperature
                ):
                    await websocket.send_json({
                        'type': 'chunk',
                        'content': chunk
                    })
                
                # Send completion signal
                await websocket.send_json({
                    'type': 'done'
                })
            except Exception as e:
                await websocket.send_json({
                    'type': 'error',
                    'error': str(e)
                })
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for thread {thread_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        await websocket.close()