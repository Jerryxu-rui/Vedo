"""
Chat Service
Handles LLM chat interactions with streaming support and conversation management
"""
from typing import AsyncGenerator, Dict, List, Optional, Any
from datetime import datetime
import json
import asyncio
from sqlalchemy.orm import Session

from services.llm_registry import LLMRegistry, LLMCapability
from database_models import ConversationThread, ConversationMessage, LLMAPIKey
from utils.error_handling import handle_llm_error
from utils.retry_handler import retry_with_backoff


class ChatService:
    """Service for managing LLM chat interactions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm_registry = LLMRegistry()
    
    async def create_thread(
        self,
        user_id: str,
        llm_model: str,
        episode_id: Optional[str] = None,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> ConversationThread:
        """Create a new conversation thread"""
        
        # Validate model exists
        model_capability = self.llm_registry.get_model(llm_model)
        if not model_capability:
            raise ValueError(f"Invalid LLM model: {llm_model}")
        
        # Create thread
        thread = ConversationThread(
            user_id=user_id,
            episode_id=episode_id,
            title=title or f"Conversation with {model_capability.display_name}",
            llm_model=llm_model,
            system_prompt=system_prompt or self._get_default_system_prompt(),
            context=context or {},
            status='active',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        
        return thread
    
    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> ConversationMessage:
        """Add a message to a conversation thread"""
        
        if role not in ['user', 'assistant', 'system']:
            raise ValueError(f"Invalid role: {role}")
        
        message = ConversationMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            message_metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    async def get_thread_messages(
        self,
        thread_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get messages from a conversation thread"""
        
        query = self.db.query(ConversationMessage).filter(
            ConversationMessage.thread_id == thread_id
        ).order_by(ConversationMessage.created_at.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    async def stream_chat(
        self,
        thread_id: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from LLM
        
        Yields:
            Chunks of the response text as they arrive
        """
        
        # Get thread
        thread = self.db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")
        
        # Get model capability with fallback
        model_capability = self.llm_registry.get_model(thread.llm_model)
        if not model_capability:
            # Fallback to default model
            default_model = self.llm_registry.get_default_model()
            print(f"[WARNING] Model {thread.llm_model} not found, falling back to {default_model}")
            model_capability = self.llm_registry.get_model(default_model)
            if not model_capability:
                raise ValueError(f"Invalid LLM model: {thread.llm_model}")
            # Update thread to use fallback model
            thread.llm_model = default_model
            self.db.commit()
        
        if not model_capability.supports_streaming:
            raise ValueError(f"Model {thread.llm_model} does not support streaming")
        
        # Add user message
        await self.add_message(thread_id, 'user', user_message)
        
        # Get conversation history
        messages = await self.get_thread_messages(thread_id)
        
        # Build message history for API
        api_messages = self._build_api_messages(messages, thread.system_prompt)
        
        # Get API key
        api_key = await self._get_api_key(thread.user_id, model_capability.provider.value)
        
        # Stream response
        full_response = ""
        try:
            async for chunk in self._stream_from_provider(
                model_capability,
                api_key,
                api_messages,
                temperature,
                max_tokens
            ):
                full_response += chunk
                yield chunk
            
            # Save assistant response
            await self.add_message(
                thread_id,
                'assistant',
                full_response,
                metadata={
                    'model': thread.llm_model,
                    'temperature': temperature,
                    'tokens': len(full_response.split())  # Rough estimate
                }
            )
            
        except Exception as e:
            error_msg = f"Error streaming from {model_capability.provider.value}: {str(e)}"
            await self.add_message(
                thread_id,
                'system',
                f"Error: {error_msg}",
                metadata={'error': True}
            )
            raise
    
    async def chat(
        self,
        thread_id: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Non-streaming chat response
        
        Returns:
            Complete response text
        """
        
        # Get thread
        thread = self.db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")
        
        # Get model capability with fallback
        model_capability = self.llm_registry.get_model(thread.llm_model)
        if not model_capability:
            # Fallback to default model
            default_model = self.llm_registry.get_default_model()
            print(f"[WARNING] Model {thread.llm_model} not found, falling back to {default_model}")
            model_capability = self.llm_registry.get_model(default_model)
            if not model_capability:
                raise ValueError(f"Invalid LLM model: {thread.llm_model}")
            # Update thread to use fallback model
            thread.llm_model = default_model
            self.db.commit()
        
        # Add user message
        await self.add_message(thread_id, 'user', user_message)
        
        # Get conversation history
        messages = await self.get_thread_messages(thread_id)
        
        # Build message history for API
        api_messages = self._build_api_messages(messages, thread.system_prompt)
        
        # Get API key
        api_key = await self._get_api_key(thread.user_id, model_capability.provider.value)
        
        # Get response
        try:
            response = await self._call_provider(
                model_capability,
                api_key,
                api_messages,
                temperature,
                max_tokens
            )
            
            # Save assistant response
            await self.add_message(
                thread_id,
                'assistant',
                response,
                metadata={
                    'model': thread.llm_model,
                    'temperature': temperature,
                    'tokens': len(response.split())  # Rough estimate
                }
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Error calling {model_capability.provider.value}: {str(e)}"
            await self.add_message(
                thread_id,
                'system',
                f"Error: {error_msg}",
                metadata={'error': True}
            )
            raise
    
    def _build_api_messages(
        self,
        messages: List[ConversationMessage],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build message list for API call"""
        
        api_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            api_messages.append({
                'role': 'system',
                'content': system_prompt
            })
        
        # Add conversation history
        for msg in messages:
            if msg.role != 'system':  # Skip system messages from history
                api_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })
        
        return api_messages
    
    async def _get_api_key(self, user_id: str, provider: str) -> str:
        """Get API key for provider"""
        
        # First, check environment variable (system-wide key)
        import os
        
        # Map provider to environment variable
        env_key_map = {
            'google': 'YUNWU_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',  # DeepSeek uses OpenAI-compatible API
            'anthropic': 'ANTHROPIC_API_KEY',
            'alibaba': 'QWEN_API_KEY'
        }
        
        env_var_name = env_key_map.get(provider, 'YUNWU_API_KEY')
        env_key = os.getenv(env_var_name)
        
        if env_key:
            print(f"[INFO] Using {env_var_name} from environment for {provider}")
            return env_key
        
        # Fallback to YUNWU_API_KEY if provider-specific key not found
        if env_var_name != 'YUNWU_API_KEY':
            fallback_key = os.getenv('YUNWU_API_KEY')
            if fallback_key:
                print(f"[INFO] Using YUNWU_API_KEY as fallback for {provider}")
                return fallback_key
        
        # Second, check database for user-specific key
        api_key_record = self.db.query(LLMAPIKey).filter(
            LLMAPIKey.user_id == user_id,
            LLMAPIKey.provider == provider,
            LLMAPIKey.is_active == True
        ).first()
        
        if not api_key_record:
            # TEMPORARY: Return mock key for demo purposes
            # TODO: Require users to add their own API keys
            print(f"[WARNING] No API key found for {provider}, using mock mode")
            return "MOCK_API_KEY_FOR_DEMO"
        
        # Update usage
        api_key_record.usage_count += 1
        api_key_record.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return api_key_record.api_key
    
    async def _stream_from_provider(
        self,
        model: LLMCapability,
        api_key: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int]
    ) -> AsyncGenerator[str, None]:
        """Stream response from LLM provider"""
        
        # Log model selection for tracking
        print(f"\n{'='*80}")
        print(f"[ChatService._stream_from_provider] MODEL SELECTION TRACKING")
        print(f"{'='*80}")
        print(f"[Model] Selected by user: {model.name}")
        print(f"[Model] Display name: {model.display_name}")
        print(f"[Model] Provider: {model.provider.value}")
        print(f"[Model] API endpoint: {model.api_endpoint}")
        print(f"[Model] Supports streaming: {model.supports_streaming}")
        print(f"[API Key] Using key for provider: {model.provider.value}")
        print(f"[API Key] Key prefix: {api_key[:10]}..." if len(api_key) > 10 else f"[API Key] {api_key}")
        print(f"{'='*80}\n")
        
        if model.provider.value == 'google':
            # Use Google Gemini API
            print(f"[ChatService] Routing to _stream_gemini for model: {model.name}")
            async for chunk in self._stream_gemini(model, api_key, messages, temperature, max_tokens):
                yield chunk
        
        elif model.provider.value == 'openai':
            # Use OpenAI API
            print(f"[ChatService] Routing to _stream_openai_compatible for OpenAI model: {model.name}")
            async for chunk in self._stream_openai_compatible(model, api_key, messages, temperature, max_tokens, is_deepseek=False):
                yield chunk
        
        elif model.provider.value == 'anthropic':
            # Use Anthropic API
            print(f"[ChatService] Routing to _stream_anthropic for model: {model.name}")
            async for chunk in self._stream_anthropic(model, api_key, messages, temperature, max_tokens):
                yield chunk
        
        elif model.provider.value == 'alibaba':
            # Use Alibaba Qwen API
            print(f"[ChatService] Routing to _stream_qwen for model: {model.name}")
            async for chunk in self._stream_qwen(model, api_key, messages, temperature, max_tokens):
                yield chunk
        
        elif model.provider.value == 'deepseek':
            # Use DeepSeek API (OpenAI-compatible)
            print(f"[ChatService] Routing to _stream_openai_compatible for DeepSeek model: {model.name}")
            async for chunk in self._stream_openai_compatible(model, api_key, messages, temperature, max_tokens, is_deepseek=True):
                yield chunk
        
        else:
            raise ValueError(f"Unsupported provider: {model.provider.value}")
    
    async def _call_provider(
        self,
        model: LLMCapability,
        api_key: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int]
    ) -> str:
        """Non-streaming call to LLM provider"""
        
        # Placeholder - would use provider-specific SDKs
        response = ""
        async for chunk in self._stream_from_provider(model, api_key, messages, temperature, max_tokens):
            response += chunk
        return response
    
    # Provider-specific streaming methods
    
    async def _stream_gemini(self, model, api_key, messages, temperature, max_tokens):
        """Stream from Google Gemini via Yunwu AI OpenAI-compatible API"""
        import aiohttp
        
        # Use Yunwu AI's OpenAI-compatible endpoint
        base_url = "https://yunwu.ai/v1/chat/completions"
        
        payload = {
            "model": model.name,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(base_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        # Check if it's a model availability error
                        if response.status == 503 and "No available channels" in error_text:
                            # Try with default model as fallback
                            default_model = self.llm_registry.get_default_model()
                            if payload["model"] != default_model:
                                print(f"[WARNING] Model {payload['model']} unavailable, retrying with {default_model}")
                                payload["model"] = default_model
                                async with session.post(base_url, json=payload, headers=headers) as retry_response:
                                    if retry_response.status != 200:
                                        retry_error = await retry_response.text()
                                        raise Exception(f"API error {retry_response.status}: {retry_error}")
                                    # Stream the retry response
                                    async for line in retry_response.content:
                                        line_text = line.decode('utf-8').strip()
                                        if line_text.startswith('data: '):
                                            data_str = line_text[6:]
                                            if data_str == '[DONE]':
                                                break
                                            try:
                                                import json
                                                data = json.loads(data_str)
                                                if 'choices' in data and len(data['choices']) > 0:
                                                    delta = data['choices'][0].get('delta', {})
                                                    content = delta.get('content', '')
                                                    if content:
                                                        yield content
                                            except json.JSONDecodeError:
                                                continue
                                    return
                        raise Exception(f"API error {response.status}: {error_text}")
                    
                    # Stream the response
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith('data: '):
                            data_str = line_text[6:]  # Remove 'data: ' prefix
                            if data_str == '[DONE]':
                                break
                            try:
                                import json
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"[ERROR] Gemini API call failed: {e}")
            raise
    
    async def _stream_openai_compatible(self, model, api_key, messages, temperature, max_tokens, is_deepseek=False):
        """Stream from OpenAI-compatible APIs (OpenAI or DeepSeek)"""
        # TEMPORARY: Mock response for demo
        if api_key == "MOCK_API_KEY_FOR_DEMO":
            response = self._generate_mock_response(messages)
            for char in response:
                yield char
                await asyncio.sleep(0.01)
        else:
            import aiohttp
            
            # Select correct API endpoint based on provider
            if is_deepseek:
                base_url = "https://api.deepseek.com/v1/chat/completions"
                provider_name = "DeepSeek"
            else:
                base_url = "https://api.openai.com/v1/chat/completions"
                provider_name = "OpenAI"
            
            payload = {
                "model": model.name,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Log API request details
            print(f"\n{'='*80}")
            print(f"[ChatService._stream_openai_compatible] API REQUEST")
            print(f"{'='*80}")
            print(f"[API] Provider: {provider_name}")
            print(f"[API] Endpoint: {base_url}")
            print(f"[API] Model requested: {model.name}")
            print(f"[API] Temperature: {temperature}")
            print(f"[API] Max tokens: {max_tokens}")
            print(f"[API] Stream: True")
            print(f"[API] Message count: {len(messages)}")
            print(f"{'='*80}\n")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(base_url, json=payload, headers=headers) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            print(f"[ERROR] {provider_name} API error {response.status}: {error_text}")
                            raise Exception(f"{provider_name} API error {response.status}: {error_text}")
                        
                        print(f"[SUCCESS] {provider_name} API responded with status 200, streaming response...")
                        
                        # Stream the response
                        async for line in response.content:
                            line_text = line.decode('utf-8').strip()
                            if line_text.startswith('data: '):
                                data_str = line_text[6:]
                                if data_str == '[DONE]':
                                    print(f"[SUCCESS] {provider_name} streaming completed")
                                    break
                                try:
                                    import json
                                    data = json.loads(data_str)
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
            except Exception as e:
                print(f"[ERROR] {provider_name} API call failed: {e}")
                raise
    
    async def _stream_anthropic(self, model, api_key, messages, temperature, max_tokens):
        """Stream from Anthropic Claude"""
        # TEMPORARY: Mock response for demo
        if api_key == "MOCK_API_KEY_FOR_DEMO":
            response = self._generate_mock_response(messages)
            for char in response:
                yield char
                await asyncio.sleep(0.01)
        else:
            # TODO: Implement with anthropic SDK
            yield "Claude response placeholder"
    
    async def _stream_qwen(self, model, api_key, messages, temperature, max_tokens):
        """Stream from Alibaba Qwen"""
        # TEMPORARY: Mock response for demo
        if api_key == "MOCK_API_KEY_FOR_DEMO":
            response = self._generate_mock_response(messages)
            for char in response:
                yield char
                await asyncio.sleep(0.01)
        else:
            # TODO: Implement with dashscope SDK
            yield "Qwen response placeholder"
    
    def _generate_mock_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a mock response based on user message"""
        if not messages:
            return "你好！我是Seko，很高兴为您服务。"
        
        last_message = messages[-1]['content'].lower()
        
        # Simple keyword-based responses
        if any(word in last_message for word in ['hello', 'hi', '你好', '嗨']):
            return "你好！我是Seko，一个专业的视频生成助手。我可以帮助您：\n\n1. 创建精彩的视频内容\n2. 回答关于视频制作的问题\n3. 提供创意建议和指导\n\n请告诉我您需要什么帮助？"
        
        elif any(word in last_message for word in ['help', '帮助', '功能', 'what can you do', '你能做什么']):
            return "我可以帮助您完成以下任务：\n\n📹 **视频生成**\n- 从创意到成片的完整工作流\n- 自动生成故事大纲、角色设计、场景设计\n- 智能分镜和视频合成\n\n💬 **对话交流**\n- 回答视频制作相关问题\n- 提供创意建议\n- 指导使用系统功能\n\n🎨 **创意支持**\n- 帮助完善视频创意\n- 提供视觉风格建议\n- 优化剧本和分镜\n\n您想从哪里开始？"
        
        elif any(word in last_message for word in ['how', '怎么', '如何']):
            return "让我来帮您了解如何使用系统：\n\n**创建视频的步骤：**\n1. 输入您的视频创意或想法\n2. 系统会生成详细的故事大纲\n3. 确认大纲后，生成角色和场景设计\n4. 查看分镜剧本\n5. 一键生成最终视频\n\n**对话交流：**\n- 直接输入问题或想法\n- 我会智能判断您是想对话还是生成视频\n- 随时可以切换模式\n\n您想尝试创建视频还是继续了解更多？"
        
        elif any(word in last_message for word in ['video', 'create', 'make', '视频', '创建', '生成', '制作']):
            return "太好了！您想创建视频。\n\n要开始视频生成，请告诉我：\n- 视频的主题或故事\n- 想要的风格（如：科幻、浪漫、悬疑等）\n- 大概的时长或场景数量\n\n例如：\"创建一个关于太空探索的科幻短片\"\n\n我会为您生成完整的视频项目！"
        
        else:
            return f"我理解您说的是：\"{messages[-1]['content']}\"\n\n作为视频生成助手，我可以：\n- 回答您的问题\n- 提供建议和指导\n- 帮助您创建视频内容\n\n请告诉我更多细节，我会尽力帮助您！"
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for video generation assistant"""
        return """You are Seko, an AI assistant specialized in video generation and creative storytelling. 
You help users create compelling video content by:
- Understanding their creative vision and requirements
- Generating detailed scene descriptions and storyboards
- Coordinating with specialized agents for video generation
- Providing guidance on visual styles and cinematography
- Maintaining consistency across scenes and characters

Be creative, helpful, and professional in your responses."""