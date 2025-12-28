"""
Conversational Episode Workflow Engine
对话式集数生产工作流引擎

管理从创意/剧本到成片的完整对话式生产流程
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio
from pydantic import BaseModel


class WorkflowState(str, Enum):
    """工作流状态枚举"""
    INITIAL = "initial"  # 初始状态
    OUTLINE_GENERATING = "outline_generating"  # 正在生成大纲
    OUTLINE_GENERATED = "outline_generated"  # 大纲已生成
    OUTLINE_CONFIRMED = "outline_confirmed"  # 大纲已确认
    REFINING = "refining"  # 正在细化剧情
    REFINED = "refined"  # 剧情已细化
    CHARACTERS_GENERATING = "characters_generating"  # 正在生成角色
    CHARACTERS_GENERATED = "characters_generated"  # 角色已生成
    CHARACTERS_CONFIRMED = "characters_confirmed"  # 角色已确认
    SCENES_GENERATING = "scenes_generating"  # 正在生成场景
    SCENES_GENERATED = "scenes_generated"  # 场景已生成
    SCENES_CONFIRMED = "scenes_confirmed"  # 场景已确认
    STORYBOARD_GENERATING = "storyboard_generating"  # 正在生成分镜
    STORYBOARD_GENERATED = "storyboard_generated"  # 分镜已生成
    STORYBOARD_CONFIRMED = "storyboard_confirmed"  # 分镜已确认
    VIDEO_GENERATING = "video_generating"  # 正在生成视频
    VIDEO_COMPLETED = "video_completed"  # 视频已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class WorkflowMode(str, Enum):
    """工作流模式"""
    IDEA = "idea"  # 从创意开始
    SCRIPT = "script"  # 从剧本开始


class WorkflowAction(str, Enum):
    """用户可执行的操作"""
    CONFIRM = "confirm"  # 确认当前步骤
    EDIT = "edit"  # 编辑当前内容
    REGENERATE = "regenerate"  # 重新生成
    CANCEL = "cancel"  # 取消工作流
    NEXT = "next"  # 进入下一步


class OutlineData(BaseModel):
    """剧本大纲数据"""
    title: str
    genre: Optional[str] = None
    style: Optional[str] = None
    episode_count: int = 1
    synopsis: str
    characters_summary: List[Dict[str, str]] = []
    plot_summary: List[Dict[str, str]] = []
    highlights: List[str] = []


class CharacterData(BaseModel):
    """角色数据"""
    name: str
    description: str
    appearance: str
    personality: List[str] = []
    role: str  # "protagonist", "antagonist", "supporting"
    image_url: Optional[str] = None


class SceneData(BaseModel):
    """场景数据"""
    name: str
    description: str
    atmosphere: str
    image_url: Optional[str] = None


class ShotData(BaseModel):
    """分镜数据"""
    shot_number: int
    scene_name: str
    visual_desc: str
    camera_angle: str
    camera_movement: str
    character_action: Optional[str] = None
    dialogue: Optional[str] = None
    voice_actor: Optional[str] = None


class ConversationalEpisodeWorkflow:
    """对话式集数生产工作流"""
    
    def __init__(
        self,
        episode_id: int,
        mode: WorkflowMode,
        initial_content: str,
        style: str = "写实电影感"
    ):
        self.episode_id = episode_id
        self.mode = mode
        self.initial_content = initial_content
        self.style = style
        self.state = WorkflowState.INITIAL
        self.context: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "mode": mode,
            "style": style,
        }
        
        # 存储各步骤的数据
        self.outline: Optional[OutlineData] = None
        self.refined_content: Optional[str] = None
        self.characters: List[CharacterData] = []
        self.scenes: List[SceneData] = []
        self.storyboard: List[ShotData] = []
        
        # 错误信息
        self.error: Optional[str] = None
    
    def get_current_step_info(self) -> Dict[str, Any]:
        """获取当前步骤信息"""
        step_info = {
            "state": self.state,
            "step_name": self._get_step_name(),
            "step_description": self._get_step_description(),
            "available_actions": self._get_available_actions(),
            "progress_percentage": self._calculate_progress(),
        }
        return step_info
    
    def _get_step_name(self) -> str:
        """获取步骤名称"""
        step_names = {
            WorkflowState.INITIAL: "初始化",
            WorkflowState.OUTLINE_GENERATING: "生成剧本大纲",
            WorkflowState.OUTLINE_GENERATED: "剧本大纲已生成",
            WorkflowState.OUTLINE_CONFIRMED: "剧本大纲已确认",
            WorkflowState.REFINING: "细化剧情内容",
            WorkflowState.REFINED: "剧情内容已细化",
            WorkflowState.CHARACTERS_GENERATING: "生成角色设计",
            WorkflowState.CHARACTERS_GENERATED: "角色设计已生成",
            WorkflowState.CHARACTERS_CONFIRMED: "角色设计已确认",
            WorkflowState.SCENES_GENERATING: "生成场景设计",
            WorkflowState.SCENES_GENERATED: "场景设计已生成",
            WorkflowState.SCENES_CONFIRMED: "场景设计已确认",
            WorkflowState.STORYBOARD_GENERATING: "生成分镜剧本",
            WorkflowState.STORYBOARD_GENERATED: "分镜剧本已生成",
            WorkflowState.STORYBOARD_CONFIRMED: "分镜剧本已确认",
            WorkflowState.VIDEO_GENERATING: "生成视频",
            WorkflowState.VIDEO_COMPLETED: "视频生成完成",
            WorkflowState.FAILED: "失败",
            WorkflowState.CANCELLED: "已取消",
        }
        return step_names.get(self.state, "未知状态")
    
    def _get_step_description(self) -> str:
        """获取步骤描述"""
        descriptions = {
            WorkflowState.INITIAL: "准备开始生成剧本大纲",
            WorkflowState.OUTLINE_GENERATING: "AI正在根据您的创意生成剧本大纲，包括基础信息、主要角色和情节概要...",
            WorkflowState.OUTLINE_GENERATED: "剧本大纲已生成完成，请在右侧查看并确认",
            WorkflowState.OUTLINE_CONFIRMED: "剧本大纲已确认，准备细化剧情内容",
            WorkflowState.REFINING: "AI正在细化本集的剧情内容，包括故事梗概、剧本亮点和美术风格...",
            WorkflowState.REFINED: "剧情内容已细化完成，准备生成角色设计",
            WorkflowState.CHARACTERS_GENERATING: "AI正在设计角色造型并生成角色图片...",
            WorkflowState.CHARACTERS_GENERATED: "角色设计已完成，请在右侧查看角色卡片",
            WorkflowState.CHARACTERS_CONFIRMED: "角色设计已确认，准备生成场景设计",
            WorkflowState.SCENES_GENERATING: "AI正在设计场景并生成场景图片...",
            WorkflowState.SCENES_GENERATED: "场景设计已完成，请在右侧查看场景列表",
            WorkflowState.SCENES_CONFIRMED: "场景设计已确认，准备生成分镜剧本",
            WorkflowState.STORYBOARD_GENERATING: "AI正在绘制详细的分镜剧本...",
            WorkflowState.STORYBOARD_GENERATED: "分镜剧本已完成，请在右侧查看分镜表",
            WorkflowState.STORYBOARD_CONFIRMED: "分镜剧本已确认，准备开始视频生成",
            WorkflowState.VIDEO_GENERATING: "正在生成视频，这可能需要一些时间...",
            WorkflowState.VIDEO_COMPLETED: "视频生成完成！",
            WorkflowState.FAILED: "生成过程中出现错误",
            WorkflowState.CANCELLED: "工作流已被取消",
        }
        return descriptions.get(self.state, "")
    
    def _get_available_actions(self) -> List[str]:
        """获取当前可用的操作"""
        # 根据状态返回可用操作
        if self.state in [
            WorkflowState.OUTLINE_GENERATED,
            WorkflowState.CHARACTERS_GENERATED,
            WorkflowState.SCENES_GENERATED,
            WorkflowState.STORYBOARD_GENERATED,
        ]:
            return [WorkflowAction.CONFIRM, WorkflowAction.EDIT, WorkflowAction.REGENERATE]
        elif self.state in [
            WorkflowState.OUTLINE_GENERATING,
            WorkflowState.REFINING,
            WorkflowState.CHARACTERS_GENERATING,
            WorkflowState.SCENES_GENERATING,
            WorkflowState.STORYBOARD_GENERATING,
            WorkflowState.VIDEO_GENERATING,
        ]:
            return [WorkflowAction.CANCEL]
        elif self.state == WorkflowState.VIDEO_COMPLETED:
            return []
        else:
            return [WorkflowAction.NEXT]
    
    def _calculate_progress(self) -> float:
        """计算整体进度百分比"""
        progress_map = {
            WorkflowState.INITIAL: 0,
            WorkflowState.OUTLINE_GENERATING: 5,
            WorkflowState.OUTLINE_GENERATED: 10,
            WorkflowState.OUTLINE_CONFIRMED: 15,
            WorkflowState.REFINING: 20,
            WorkflowState.REFINED: 25,
            WorkflowState.CHARACTERS_GENERATING: 30,
            WorkflowState.CHARACTERS_GENERATED: 40,
            WorkflowState.CHARACTERS_CONFIRMED: 45,
            WorkflowState.SCENES_GENERATING: 50,
            WorkflowState.SCENES_GENERATED: 60,
            WorkflowState.SCENES_CONFIRMED: 65,
            WorkflowState.STORYBOARD_GENERATING: 70,
            WorkflowState.STORYBOARD_GENERATED: 80,
            WorkflowState.STORYBOARD_CONFIRMED: 85,
            WorkflowState.VIDEO_GENERATING: 90,
            WorkflowState.VIDEO_COMPLETED: 100,
        }
        return progress_map.get(self.state, 0)
    
    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """检查是否可以转换到新状态"""
        # 定义状态转换规则
        valid_transitions = {
            WorkflowState.INITIAL: [WorkflowState.OUTLINE_GENERATING],
            WorkflowState.OUTLINE_GENERATING: [WorkflowState.OUTLINE_GENERATED, WorkflowState.FAILED],
            WorkflowState.OUTLINE_GENERATED: [WorkflowState.OUTLINE_CONFIRMED, WorkflowState.OUTLINE_GENERATING],
            WorkflowState.OUTLINE_CONFIRMED: [WorkflowState.REFINING],
            WorkflowState.REFINING: [WorkflowState.REFINED, WorkflowState.FAILED],
            WorkflowState.REFINED: [WorkflowState.CHARACTERS_GENERATING],
            WorkflowState.CHARACTERS_GENERATING: [WorkflowState.CHARACTERS_GENERATED, WorkflowState.FAILED],
            WorkflowState.CHARACTERS_GENERATED: [WorkflowState.CHARACTERS_CONFIRMED, WorkflowState.CHARACTERS_GENERATING],
            WorkflowState.CHARACTERS_CONFIRMED: [WorkflowState.SCENES_GENERATING],
            WorkflowState.SCENES_GENERATING: [WorkflowState.SCENES_GENERATED, WorkflowState.FAILED],
            WorkflowState.SCENES_GENERATED: [WorkflowState.SCENES_CONFIRMED, WorkflowState.SCENES_GENERATING],
            WorkflowState.SCENES_CONFIRMED: [WorkflowState.STORYBOARD_GENERATING],
            WorkflowState.STORYBOARD_GENERATING: [WorkflowState.STORYBOARD_GENERATED, WorkflowState.FAILED],
            WorkflowState.STORYBOARD_GENERATED: [WorkflowState.STORYBOARD_CONFIRMED, WorkflowState.STORYBOARD_GENERATING],
            WorkflowState.STORYBOARD_CONFIRMED: [WorkflowState.VIDEO_GENERATING],
            WorkflowState.VIDEO_GENERATING: [WorkflowState.VIDEO_COMPLETED, WorkflowState.FAILED],
        }
        
        allowed_states = valid_transitions.get(self.state, [])
        return new_state in allowed_states
    
    def transition_to(self, new_state: WorkflowState) -> bool:
        """转换到新状态"""
        if self.can_transition_to(new_state):
            self.state = new_state
            self.context["updated_at"] = datetime.now().isoformat()
            self.context["last_state"] = self.state
            return True
        else:
            raise ValueError(
                f"Invalid state transition from {self.state} to {new_state}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "episode_id": self.episode_id,
            "mode": self.mode,
            "state": self.state,
            "style": self.style,
            "context": self.context,
            "outline": self.outline.dict() if self.outline else None,
            "refined_content": self.refined_content,
            "characters": [c.dict() for c in self.characters],
            "scenes": [s.dict() for s in self.scenes],
            "storyboard": [shot.dict() for shot in self.storyboard],
            "error": self.error,
            "step_info": self.get_current_step_info(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationalEpisodeWorkflow":
        """从字典创建实例"""
        workflow = cls(
            episode_id=data["episode_id"],
            mode=WorkflowMode(data["mode"]),
            initial_content=data.get("context", {}).get("initial_content", ""),
            style=data.get("style", "写实电影感"),
        )
        workflow.state = WorkflowState(data["state"])
        workflow.context = data.get("context", {})
        
        if data.get("outline"):
            workflow.outline = OutlineData(**data["outline"])
        
        workflow.refined_content = data.get("refined_content")
        
        if data.get("characters"):
            workflow.characters = [CharacterData(**c) for c in data["characters"]]
        
        if data.get("scenes"):
            workflow.scenes = [SceneData(**s) for s in data["scenes"]]
        
        if data.get("storyboard"):
            workflow.storyboard = [ShotData(**shot) for shot in data["storyboard"]]
        
        workflow.error = data.get("error")
        
        return workflow


class WorkflowManager:
    """工作流管理器 - 管理所有活跃的工作流实例"""
    
    def __init__(self):
        self.workflows: Dict[int, ConversationalEpisodeWorkflow] = {}
    
    def create_workflow(
        self,
        episode_id: int,
        mode: WorkflowMode,
        initial_content: str,
        style: str = "写实电影感"
    ) -> ConversationalEpisodeWorkflow:
        """创建新的工作流"""
        workflow = ConversationalEpisodeWorkflow(
            episode_id=episode_id,
            mode=mode,
            initial_content=initial_content,
            style=style
        )
        self.workflows[episode_id] = workflow
        return workflow
    
    def get_workflow(self, episode_id: int) -> Optional[ConversationalEpisodeWorkflow]:
        """获取工作流"""
        return self.workflows.get(episode_id)
    
    def remove_workflow(self, episode_id: int):
        """移除工作流"""
        if episode_id in self.workflows:
            del self.workflows[episode_id]
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        return [
            {
                "episode_id": wf.episode_id,
                "state": wf.state,
                "mode": wf.mode,
                "progress": wf._calculate_progress(),
            }
            for wf in self.workflows.values()
        ]


# 全局工作流管理器实例
workflow_manager = WorkflowManager()