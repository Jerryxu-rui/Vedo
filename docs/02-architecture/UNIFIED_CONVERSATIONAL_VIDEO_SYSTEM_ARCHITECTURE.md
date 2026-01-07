# 统一对话式视频生成编辑系统架构设计

**设计目标**: 创建一个以对话为中心的视频生成编辑系统，通过智能聊天界面协调多个专业智能体，在单一对话体验中完成视频创作的全流程。

---

## 🎯 核心理念

### 设计原则

1. **对话优先** - 聊天是唯一的用户界面，所有操作通过对话完成
2. **智能体协作** - 多个专业智能体通过工作流引擎协同工作
3. **上下文感知** - 系统理解对话历史和视频项目状态
4. **实时反馈** - 通过对话提供生成进度和结果预览
5. **迭代优化** - 支持通过对话进行多轮修改和完善

### 用户体验流程

```
用户: "我想创建一个关于春天的短视频"
系统: "好的！我将为您创建一个春天主题的视频。让我先构思剧本..."
     [Script Writer Agent 工作中]
系统: "剧本已完成！故事讲述了春天花开的美景。要查看详细剧本吗？"
用户: "看起来不错，继续生成视频"
系统: "开始生成视频..."
     [Video Generator Agent 工作中]
系统: "视频生成完成！[预览图] 您觉得怎么样？"
用户: "第二个镜头太暗了，能调亮一些吗？"
系统: "好的，我来调整第二个镜头的亮度..."
     [Editor Agent 工作中]
系统: "已调整完成！[更新的预览] 现在效果如何？"
```

---

## 🏗️ 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Conversational Interface                  │
│                     (Single Chat UI)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Conversational Orchestrator                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Intent Understanding & Context Management            │  │
│  │  - Natural Language Understanding                     │  │
│  │  - Conversation History Tracking                      │  │
│  │  - Project State Management                           │  │
│  │  - User Preference Learning                           │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Coordination & Workflow Engine                 │  │
│  │  - Agent Selection & Routing                          │  │
│  │  - Task Decomposition                                 │  │
│  │  - Parallel/Sequential Execution                      │  │
│  │  - Result Aggregation                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Script Writer │  │Video Generator│  │Editor Agent  │
│   Agent      │  │    Agent      │  │              │
├──────────────┤  ├──────────────┤  ├──────────────┤
│- Story       │  │- Scene Gen   │  │- Cut/Trim    │
│- Dialogue    │  │- Character   │  │- Color Grade │
│- Narration   │  │- Storyboard  │  │- Effects     │
│- Structure   │  │- Video Comp  │  │- Transitions │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Reviewer Agent                              │
│  - Quality Check                                             │
│  - Consistency Validation                                    │
│  - Suggestion Generation                                     │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Shared Knowledge Base                           │
│  - Project Assets (videos, images, audio)                   │
│  - Conversation History                                      │
│  - Workflow State                                            │
│  - User Preferences                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 核心组件设计

### 1. Conversational Orchestrator (对话编排器)

**职责**: 作为系统大脑，理解用户意图并协调所有智能体

#### 1.1 Intent Understanding Module

```python
class IntentUnderstandingModule:
    """
    理解用户意图并提取关键信息
    """
    
    async def analyze_message(
        self,
        message: str,
        conversation_history: List[Message],
        project_context: ProjectContext
    ) -> Intent:
        """
        分析用户消息，返回结构化意图
        
        Intent类型:
        - CREATE_VIDEO: 创建新视频
        - MODIFY_VIDEO: 修改现有视频
        - REVIEW_VIDEO: 查看/评审视频
        - QUERY_STATUS: 查询进度
        - PROVIDE_FEEDBACK: 提供反馈
        - REFINE_CONTENT: 细化内容
        """
        
        # 使用LLM理解意图
        intent_prompt = self._build_intent_prompt(
            message, 
            conversation_history,
            project_context
        )
        
        intent_result = await self.llm.analyze(intent_prompt)
        
        return Intent(
            type=intent_result.intent_type,
            confidence=intent_result.confidence,
            entities=intent_result.extracted_entities,
            context=intent_result.context_requirements
        )
```

#### 1.2 Context Management Module

```python
class ConversationContextManager:
    """
    管理对话上下文和项目状态
    """
    
    def __init__(self):
        self.conversation_history: List[Message] = []
        self.project_state: ProjectState = None
        self.active_agents: Dict[str, Agent] = {}
        self.pending_tasks: List[Task] = []
    
    async def update_context(
        self,
        user_message: str,
        system_response: str,
        agent_results: Dict[str, Any]
    ):
        """更新对话上下文"""
        
        # 添加到历史
        self.conversation_history.append(
            Message(role="user", content=user_message)
        )
        self.conversation_history.append(
            Message(role="assistant", content=system_response)
        )
        
        # 更新项目状态
        if agent_results:
            await self._update_project_state(agent_results)
        
        # 保持上下文窗口大小
        if len(self.conversation_history) > MAX_CONTEXT_LENGTH:
            self._compress_history()
    
    def get_relevant_context(self, intent: Intent) -> Dict[str, Any]:
        """获取与当前意图相关的上下文"""
        
        return {
            "recent_messages": self.conversation_history[-10:],
            "project_state": self.project_state.to_dict(),
            "active_workflows": [t.to_dict() for t in self.pending_tasks],
            "user_preferences": self._get_user_preferences()
        }
```

#### 1.3 Agent Coordination Module

```python
class AgentCoordinator:
    """
    协调多个智能体的工作
    """
    
    def __init__(self):
        self.agents = {
            "script_writer": ScriptWriterAgent(),
            "video_generator": VideoGeneratorAgent(),
            "editor": EditorAgent(),
            "reviewer": ReviewerAgent()
        }
        self.workflow_engine = WorkflowEngine()
    
    async def execute_intent(
        self,
        intent: Intent,
        context: Dict[str, Any]
    ) -> AgentExecutionResult:
        """
        根据意图执行相应的智能体工作流
        """
        
        # 1. 分解任务
        tasks = await self._decompose_intent_to_tasks(intent, context)
        
        # 2. 创建工作流
        workflow = self._create_workflow(tasks)
        
        # 3. 执行工作流
        result = await self.workflow_engine.execute(
            workflow,
            progress_callback=self._send_progress_update
        )
        
        # 4. 聚合结果
        aggregated_result = await self._aggregate_results(result)
        
        return aggregated_result
    
    async def _decompose_intent_to_tasks(
        self,
        intent: Intent,
        context: Dict[str, Any]
    ) -> List[Task]:
        """
        将意图分解为具体任务
        
        示例:
        Intent: CREATE_VIDEO("春天的故事")
        Tasks:
        1. ScriptWriterAgent.write_script(theme="春天")
        2. VideoGeneratorAgent.generate_characters(script)
        3. VideoGeneratorAgent.generate_scenes(script)
        4. VideoGeneratorAgent.generate_storyboard(script, characters, scenes)
        5. VideoGeneratorAgent.generate_video(storyboard)
        6. ReviewerAgent.review_video(video)
        """
        
        if intent.type == IntentType.CREATE_VIDEO:
            return [
                Task(
                    agent="script_writer",
                    action="write_script",
                    params={"theme": intent.entities.get("theme")},
                    dependencies=[]
                ),
                Task(
                    agent="video_generator",
                    action="generate_characters",
                    params={"script": "{{script_writer.write_script.output}}"},
                    dependencies=["script_writer.write_script"]
                ),
                # ... 更多任务
            ]
        
        elif intent.type == IntentType.MODIFY_VIDEO:
            # 根据修改类型选择合适的智能体
            modification_type = intent.entities.get("modification_type")
            
            if modification_type == "brightness":
                return [
                    Task(
                        agent="editor",
                        action="adjust_brightness",
                        params={
                            "shot_id": intent.entities.get("shot_id"),
                            "adjustment": intent.entities.get("adjustment")
                        }
                    )
                ]
        
        # ... 处理其他意图类型
```

### 2. Specialized Agents (专业智能体)

#### 2.1 Script Writer Agent

```python
class ScriptWriterAgent(BaseAgent):
    """
    剧本创作智能体
    """
    
    async def write_script(
        self,
        theme: str,
        style: str = "cinematic",
        duration: int = 60,
        context: Dict[str, Any] = None
    ) -> Script:
        """
        创作视频剧本
        """
        
        prompt = f"""
        创作一个关于"{theme}"的{duration}秒短视频剧本。
        风格: {style}
        
        要求:
        1. 包含清晰的故事结构(开始、发展、高潮、结尾)
        2. 描述主要角色和场景
        3. 包含对话或旁白
        4. 适合视觉呈现
        
        输出格式: JSON
        """
        
        script_json = await self.llm.generate(prompt)
        
        return Script.from_json(script_json)
    
    async def refine_script(
        self,
        script: Script,
        feedback: str
    ) -> Script:
        """
        根据反馈优化剧本
        """
        
        prompt = f"""
        原剧本:
        {script.to_text()}
        
        用户反馈:
        {feedback}
        
        请根据反馈优化剧本，保持故事连贯性。
        """
        
        refined_json = await self.llm.generate(prompt)
        
        return Script.from_json(refined_json)
```

#### 2.2 Video Generator Agent

```python
class VideoGeneratorAgent(BaseAgent):
    """
    视频生成智能体
    """
    
    async def generate_video_from_script(
        self,
        script: Script,
        style: str,
        progress_callback: Callable = None
    ) -> Video:
        """
        从剧本生成完整视频
        """
        
        # 1. 生成角色
        if progress_callback:
            await progress_callback(0.1, "正在生成角色...")
        
        characters = await self._generate_characters(script, style)
        
        # 2. 生成场景
        if progress_callback:
            await progress_callback(0.3, "正在生成场景...")
        
        scenes = await self._generate_scenes(script, style)
        
        # 3. 生成分镜
        if progress_callback:
            await progress_callback(0.5, "正在生成分镜...")
        
        storyboard = await self._generate_storyboard(
            script, characters, scenes
        )
        
        # 4. 生成视频片段
        if progress_callback:
            await progress_callback(0.7, "正在生成视频片段...")
        
        video_clips = await self._generate_video_clips(
            storyboard, characters, scenes
        )
        
        # 5. 合成最终视频
        if progress_callback:
            await progress_callback(0.9, "正在合成视频...")
        
        final_video = await self._compose_video(video_clips)
        
        if progress_callback:
            await progress_callback(1.0, "视频生成完成！")
        
        return final_video
```

#### 2.3 Editor Agent

```python
class EditorAgent(BaseAgent):
    """
    视频编辑智能体
    """
    
    async def adjust_brightness(
        self,
        video: Video,
        shot_id: str,
        adjustment: float
    ) -> Video:
        """调整镜头亮度"""
        
        shot = video.get_shot(shot_id)
        edited_shot = await self.video_processor.adjust_brightness(
            shot, adjustment
        )
        
        return video.replace_shot(shot_id, edited_shot)
    
    async def add_transition(
        self,
        video: Video,
        between_shots: Tuple[str, str],
        transition_type: str
    ) -> Video:
        """添加转场效果"""
        
        return await self.video_processor.add_transition(
            video, between_shots, transition_type
        )
    
    async def trim_shot(
        self,
        video: Video,
        shot_id: str,
        start_time: float,
        end_time: float
    ) -> Video:
        """裁剪镜头"""
        
        shot = video.get_shot(shot_id)
        trimmed_shot = await self.video_processor.trim(
            shot, start_time, end_time
        )
        
        return video.replace_shot(shot_id, trimmed_shot)
```

#### 2.4 Reviewer Agent

```python
class ReviewerAgent(BaseAgent):
    """
    视频评审智能体
    """
    
    async def review_video(
        self,
        video: Video,
        script: Script
    ) -> ReviewResult:
        """
        评审视频质量和一致性
        """
        
        # 1. 检查与剧本的一致性
        consistency_score = await self._check_script_consistency(
            video, script
        )
        
        # 2. 评估视觉质量
        visual_quality = await self._assess_visual_quality(video)
        
        # 3. 检查流畅度
        flow_score = await self._check_flow(video)
        
        # 4. 生成改进建议
        suggestions = await self._generate_suggestions(
            video, consistency_score, visual_quality, flow_score
        )
        
        return ReviewResult(
            overall_score=(consistency_score + visual_quality + flow_score) / 3,
            consistency_score=consistency_score,
            visual_quality=visual_quality,
            flow_score=flow_score,
            suggestions=suggestions
        )
```

### 3. Workflow Engine (工作流引擎)

```python
class WorkflowEngine:
    """
    执行智能体工作流
    """
    
    async def execute(
        self,
        workflow: Workflow,
        progress_callback: Callable = None
    ) -> WorkflowResult:
        """
        执行工作流
        
        支持:
        - 顺序执行
        - 并行执行
        - 条件分支
        - 错误重试
        - 状态持久化
        """
        
        execution_context = ExecutionContext(
            workflow_id=workflow.id,
            start_time=datetime.now()
        )
        
        try:
            # 按依赖关系排序任务
            sorted_tasks = self._topological_sort(workflow.tasks)
            
            # 执行任务
            for task in sorted_tasks:
                # 检查依赖是否完成
                if not self._dependencies_satisfied(task, execution_context):
                    await self._wait_for_dependencies(task, execution_context)
                
                # 执行任务
                result = await self._execute_task(
                    task,
                    execution_context,
                    progress_callback
                )
                
                # 保存结果
                execution_context.task_results[task.id] = result
                
                # 持久化状态
                await self._save_state(execution_context)
            
            return WorkflowResult(
                success=True,
                results=execution_context.task_results,
                execution_time=datetime.now() - execution_context.start_time
            )
            
        except Exception as e:
            # 错误处理和恢复
            return await self._handle_workflow_error(
                e, execution_context, workflow
            )
```

---

## 💬 对话交互设计

### 对话流程示例

#### 场景1: 创建新视频

```
User: "帮我创建一个关于春天的30秒短视频"

System: "好的！我将为您创建一个春天主题的30秒短视频。
        
        📝 正在构思剧本...
        
        [Script Writer Agent 工作中]"

System: "✅ 剧本创作完成！
        
        故事概要:
        春天来临，花园里的花朵逐渐绽放。一只蝴蝶在花丛中翩翩起舞，
        最后停在一朵盛开的樱花上。
        
        主要场景:
        1. 清晨的花园 (5秒)
        2. 花朵绽放特写 (10秒)
        3. 蝴蝶飞舞 (10秒)
        4. 蝴蝶停在樱花上 (5秒)
        
        您觉得这个剧本如何？可以说"继续生成"或提出修改建议。"

User: "很好，继续生成视频"

System: "开始生成视频...
        
        🎨 正在生成角色和场景... (30%)
        [Video Generator Agent 工作中]"

System: "🎬 正在生成分镜... (60%)
        [Video Generator Agent 工作中]"

System: "🎥 正在合成视频... (90%)
        [Video Generator Agent 工作中]"

System: "✅ 视频生成完成！
        
        [视频预览缩略图]
        
        📊 质量评估:
        - 视觉质量: 9.2/10
        - 流畅度: 8.8/10
        - 剧本一致性: 9.5/10
        
        您可以:
        - 说"播放视频"查看完整视频
        - 说"下载视频"保存到本地
        - 提出修改建议(如"第二个镜头太暗了")"

User: "第三个镜头的蝴蝶飞得太快了，能慢一些吗？"

System: "好的，我来调整第三个镜头的速度...
        
        🎬 正在编辑... (Editor Agent 工作中)"

System: "✅ 已调整完成！
        
        [更新的预览]
        
        现在蝴蝶的飞行速度降低了30%，看起来更优雅了。
        还需要其他调整吗？"
```

#### 场景2: 迭代优化

```
User: "能把整个视频的色调调得更温暖一些吗？"

System: "好的，我将为整个视频添加温暖的色调...
        
        🎨 正在调整色彩... (Editor Agent 工作中)"

System: "✅ 色调调整完成！
        
        [对比图: 调整前 vs 调整后]
        
        已为视频添加了温暖的橙黄色调，更符合春天的氛围。
        效果满意吗？"

User: "完美！现在可以下载了"

System: "太好了！视频已准备好下载。
        
        📥 [下载视频] (MP4, 1920x1080, 30fps, 5.2MB)
        
        感谢使用！如果需要创建更多视频或进行其他编辑，
        随时告诉我。"
```

### 对话响应模板

```python
class ConversationalResponseGenerator:
    """
    生成自然的对话响应
    """
    
    RESPONSE_TEMPLATES = {
        "video_creation_started": [
            "好的！我将为您创建{description}。",
            "明白了！开始创作{description}...",
            "收到！让我为您制作{description}。"
        ],
        
        "progress_update": [
            "🎨 正在{action}... ({progress}%)",
            "⏳ {action}中，请稍候... ({progress}%)",
            "📊 进度: {action} - {progress}%完成"
        ],
        
        "completion": [
            "✅ {task}完成！",
            "🎉 {task}已完成！",
            "👍 {task}成功！"
        ],
        
        "request_feedback": [
            "您觉得{item}如何？",
            "{item}效果满意吗？",
            "对{item}有什么建议吗？"
        ],
        
        "modification_started": [
            "好的，我来{action}...",
            "明白了，正在{action}...",
            "收到！开始{action}..."
        ]
    }
    
    def generate_response(
        self,
        template_key: str,
        **kwargs
    ) -> str:
        """生成自然的响应"""
        
        templates = self.RESPONSE_TEMPLATES.get(template_key, [])
        template = random.choice(templates)
        
        return template.format(**kwargs)
```

---

## 🔄 状态管理

### Project State Schema

```python
class ProjectState:
    """
    项目状态
    """
    
    project_id: str
    created_at: datetime
    updated_at: datetime
    
    # 剧本状态
    script: Optional[Script] = None
    script_version: int = 0
    script_status: ScriptStatus = ScriptStatus.NOT_STARTED
    
    # 视频生成状态
    characters: List[Character] = []
    scenes: List[Scene] = []
    storyboard: List[Shot] = []
    video: Optional[Video] = None
    video_status: VideoStatus = VideoStatus.NOT_STARTED
    
    # 工作流状态
    active_workflows: List[WorkflowExecution] = []
    completed_tasks: List[Task] = []
    pending_tasks: List[Task] = []
    
    # 用户交互
    conversation_history: List[Message] = []
    user_preferences: Dict[str, Any] = {}
    
    # 版本历史
    versions: List[ProjectVersion] = []
    
    def create_snapshot(self) -> ProjectVersion:
        """创建当前状态快照"""
        return ProjectVersion(
            version_number=len(self.versions) + 1,
            timestamp=datetime.now(),
            script=self.script.copy() if self.script else None,
            video=self.video.copy() if self.video else None,
            description=f"Version {len(self.versions) + 1}"
        )
    
    def rollback_to_version(self, version_number: int):
        """回滚到指定版本"""
        version = next(
            (v for v in self.versions if v.version_number == version_number),
            None
        )
        
        if version:
            self.script = version.script
            self.video = version.video
            self.script_version = version_number
```

---

## 🚀 实现路线图

### Phase 1: 核心对话系统

**目标**: 建立基础对话框架和意图理解

- [ ] 实现 `ConversationalOrchestrator` 核心类
- [ ] 实现 `IntentUnderstandingModule`
- [ ] 实现 `ConversationContextManager`
- [ ] 创建基础对话UI
- [ ] 实现对话历史持久化
- [ ] 添加实时WebSocket通信

### Phase 2: 智能体集成

**目标**: 集成现有pipeline作为智能体

- [ ] 创建 `ScriptWriterAgent`
- [ ] 创建 `VideoGeneratorAgent`
- [ ] 创建 `EditorAgent`
- [ ] 创建 `ReviewerAgent`
- [ ] 实现智能体间通信协议

### Phase 3: 工作流引擎

**目标**: 实现灵活的工作流编排

- [ ] 实现 `WorkflowEngine` 核心逻辑
- [ ] 支持任务依赖管理
- [ ] 实现并行执行
- [ ] 添加错误恢复机制
- [ ] 实现状态持久化和恢复

### Phase 4: 高级对话功能

**目标**: 增强对话体验

- [ ] 实现多轮对话上下文理解
- [ ] 添加主动建议功能
- [ ] 实现语音输入支持
- [ ] 添加视频预览内嵌
- [ ] 实现版本管理和回滚

### Phase 5: 优化和测试

**目标**: 性能优化和全面测试

- [ ] 性能优化(缓存、并行)
- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 用户体验测试
- [ ] 文档完善

---

## 🔗 相关文档

- [API整合规划](../03-api-integration/API_INTEGRATION_PLAN.md)
- [统一API设计](../03-api-integration/UNIFIED_API_DESIGN.md)