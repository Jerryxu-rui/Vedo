"""
Pipeline Adapter for Conversational Workflow
将现有的Idea2Video和Script2Video pipeline适配到对话式工作流中
"""

from typing import Dict, Any, List, Optional
import asyncio
import os
from pathlib import Path

from pipelines.idea2video_pipeline import Idea2VideoPipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
from workflows.conversational_episode_workflow import (
    OutlineData, CharacterData, SceneData, ShotData
)
from agents.scene_image_generator import SceneImageGenerator
from agents.personality_extractor import PersonalityExtractor
from utils.async_wrapper import ProgressCallback, AsyncBatchProcessor


class PipelineAdapter:
    """
    适配器类，用于将现有pipeline的功能分解为对话式工作流的各个步骤
    """
    
    def __init__(self, config_path: str, mode: str = "idea"):
        """
        初始化适配器
        
        Args:
            config_path: 配置文件路径
            mode: 'idea' 或 'script'
        """
        self.mode = mode
        self.config_path = config_path
        self.pipeline = None
        self.scene_generator = None
        self.personality_extractor = PersonalityExtractor()
        self.batch_processor = AsyncBatchProcessor(max_concurrent=3)
        
    async def initialize_pipeline(self):
        """初始化pipeline"""
        if self.mode == "idea":
            self.pipeline = Idea2VideoPipeline.init_from_config(self.config_path)
        else:
            self.pipeline = Script2VideoPipeline.init_from_config(self.config_path)
        
        # Initialize scene image generator with the same image generator as pipeline
        if self.pipeline and hasattr(self.pipeline, 'image_generator'):
            self.scene_generator = SceneImageGenerator(self.pipeline.image_generator)
    
    async def generate_outline_from_idea(
        self,
        idea: str,
        style: str = "写实电影感"
    ) -> OutlineData:
        """
        从创意生成剧本大纲
        
        这是Idea2Video模式的第一步
        """
        if not self.pipeline:
            await self.initialize_pipeline()
        
        try:
            # Enhanced user requirement that emphasizes the user's specific idea
            user_requirement = (
                f"请基于用户提供的创意，创作一个{style}风格的故事。"
                f"重要：必须紧密围绕用户的核心创意展开，充分体现创意中的关键元素、场景和情节。"
                f"故事应该生动、具体，包含丰富的视觉细节和角色互动。"
            )
            
            # 调用pipeline的develop_story方法生成故事
            story = await self.pipeline.develop_story(
                idea=idea,
                user_requirement=user_requirement
            )
            
            # 从故事中提取角色信息
            characters = await self.pipeline.extract_characters(story=story)
            
            # 将故事分段作为plot_summary
            paragraphs = [p.strip() for p in story.split('\n\n') if p.strip()]
            
            # 构建角色摘要
            characters_summary = []
            for char in characters[:5]:  # 最多5个主要角色
                characters_summary.append({
                    "name": char.identifier_in_scene,
                    "role": "主角" if char.idx == 0 else "配角",
                    "description": f"{char.static_features} {char.dynamic_features}"
                })
            
            # 构建剧情摘要
            plot_summary = []
            for i, para in enumerate(paragraphs[:5]):  # 最多5个段落
                plot_summary.append({
                    "act": f"第{i+1}幕",
                    "description": para[:200] + "..." if len(para) > 200 else para
                })
            
            outline = OutlineData(
                title=f"基于创意的故事",
                genre="未分类",
                style=style,
                episode_count=1,
                synopsis=paragraphs[0][:300] if paragraphs else story[:300],
                characters_summary=characters_summary,
                plot_summary=plot_summary,
                highlights=["AI生成", style, "原创故事"]
            )
            
            return outline
            
        except Exception as e:
            print(f"Error generating outline from idea: {e}")
            # 返回基础大纲
            return OutlineData(
                title="新故事",
                genre="未分类",
                style=style,
                episode_count=1,
                synopsis=idea[:300],
                characters_summary=[],
                plot_summary=[{"act": "开端", "description": idea[:200]}],
                highlights=[style]
            )
    
    async def generate_outline_from_script(
        self,
        script: str,
        style: str = "写实电影感"
    ) -> OutlineData:
        """
        从剧本提取大纲信息
        
        这是Script2Video模式的第一步
        """
        # Script2Video模式下，直接从剧本提取信息
        # 可以使用NLP或简单的规则提取
        
        # 简单实现：将剧本分段作为plot_summary
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
        
        outline = OutlineData(
            title="Episode 1",
            genre="未分类",
            style=style,
            episode_count=1,
            synopsis=paragraphs[0] if paragraphs else script[:200],
            characters_summary=[],
            plot_summary=[
                {"act": f"Part {i+1}", "description": p}
                for i, p in enumerate(paragraphs[:5])
            ],
            highlights=[]
        )
        
        return outline
    
    async def extract_and_generate_characters(
        self,
        content: str,
        style: str = "写实电影感",
        progress: Optional[ProgressCallback] = None
    ) -> List[CharacterData]:
        """
        提取并生成角色设计
        
        从内容中提取角色，并生成角色图片
        
        Args:
            content: Story content
            style: Visual style
            progress: Optional progress callback
        """
        if not self.pipeline:
            await self.initialize_pipeline()
        
        try:
            if progress:
                await progress.update(0.1, "Extracting characters from content...")
            
            # 调用pipeline的extract_characters方法
            characters_in_scene = await self.pipeline.extract_characters(story=content)
            
            if progress:
                await progress.update(0.3, f"Found {len(characters_in_scene)} characters, generating portraits...")
            
            # 生成角色肖像
            character_portraits_registry = await self.pipeline.generate_character_portraits(
                characters=characters_in_scene,
                character_portraits_registry=None,
                style=style
            )
            
            if progress:
                await progress.update(0.7, "Extracting personality traits...")
            
            # 转换为CharacterData格式
            characters = []
            for char in characters_in_scene:
                # 获取角色图片路径
                portrait_info = character_portraits_registry.get(char.identifier_in_scene, {})
                front_portrait = portrait_info.get("front", {})
                image_path = front_portrait.get("path", "")
                
                # 使用PersonalityExtractor提取性格特征
                full_description = f"{char.static_features} {char.dynamic_features}"
                personality = self.personality_extractor.extract_traits_simple(
                    description=full_description,
                    max_traits=5
                )
                
                character = CharacterData(
                    name=char.identifier_in_scene,
                    role="protagonist" if char.idx == 0 else "supporting",
                    description=char.static_features,
                    appearance=char.dynamic_features,
                    personality=personality,
                    image_url=image_path
                )
                characters.append(character)
            
            return characters
            
        except Exception as e:
            print(f"Error extracting characters: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认角色（不设置image_url，让前端显示占位符）
            return [
                CharacterData(
                    name="主角",
                    role="protagonist",
                    description="故事的主要角色",
                    appearance="待定",
                    personality=["勇敢", "善良"],
                    image_url=None
                )
            ]
    
    async def generate_scenes(
        self,
        outline: OutlineData,
        characters: List[CharacterData],
        style: str = "写实电影感",
        progress: Optional[ProgressCallback] = None
    ) -> List[SceneData]:
        """
        生成场景设计
        
        根据大纲和角色生成场景
        
        Args:
            outline: Story outline
            characters: List of characters
            style: Visual style
            progress: Optional progress callback
        """
        if not self.pipeline:
            await self.initialize_pipeline()
        
        try:
            if progress:
                await progress.update(0.1, "Analyzing plot structure...")
            
            # 从plot_summary中提取场景信息
            scenes = []
            total_scenes = min(len(outline.plot_summary), 5)
            
            for i, plot_point in enumerate(outline.plot_summary[:5]):
                if progress:
                    scene_progress = 0.1 + (i / total_scenes) * 0.9
                    await progress.update(scene_progress, f"Generating scene {i+1}/{total_scenes}...")
                scene_desc = plot_point.get("description", "")
                
                # 简单的场景名称提取（可以改进）
                scene_name = plot_point.get("act", f"场景 {i+1}")
                
                # 推断氛围
                atmosphere = "平静"
                if any(word in scene_desc for word in ["紧张", "危险", "冲突"]):
                    atmosphere = "紧张"
                elif any(word in scene_desc for word in ["温馨", "温暖", "幸福"]):
                    atmosphere = "温馨"
                elif any(word in scene_desc for word in ["悲伤", "难过", "痛苦"]):
                    atmosphere = "悲伤"
                elif any(word in scene_desc for word in ["神秘", "诡异", "奇怪"]):
                    atmosphere = "神秘"
                
                # 生成场景图片（如果scene_generator可用）
                image_url = None
                scene_image_error = None
                if self.scene_generator:
                    try:
                        print(f"[Scene {i+1}] Generating image for: {scene_name}")
                        image_output = await self.scene_generator.generate_scene_image(
                            scene_name=scene_name,
                            scene_description=scene_desc,
                            atmosphere=atmosphere,
                            style=style
                        )
                        
                        # 保存图片
                        if image_output.fmt == "url":
                            # URL格式，直接使用
                            image_url = image_output.data
                            print(f"[Scene {i+1}] Image URL: {image_url}")
                        else:
                            # 保存到本地
                            scene_dir = os.path.join(self.pipeline.working_dir, "scenes")
                            os.makedirs(scene_dir, exist_ok=True)
                            image_path = os.path.join(scene_dir, f"scene_{i+1}.{image_output.ext}")
                            image_output.save(image_path)
                            image_url = f"./{os.path.relpath(image_path, '.')}"
                            print(f"[Scene {i+1}] Image saved to: {image_path}")
                    except Exception as e:
                        scene_image_error = str(e)
                        print(f"[Scene {i+1}] ERROR generating scene image for {scene_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Store error but continue - frontend will show placeholder
                
                scene = SceneData(
                    name=scene_name,
                    description=scene_desc,
                    atmosphere=atmosphere,
                    image_url=image_url
                )
                
                # Log scene creation result
                if image_url:
                    print(f"[Scene {i+1}] Created successfully with image")
                elif scene_image_error:
                    print(f"[Scene {i+1}] Created without image due to error: {scene_image_error}")
                else:
                    print(f"[Scene {i+1}] Created without image (no generator available)")
                scenes.append(scene)
            
            return scenes
            
        except Exception as e:
            print(f"Error generating scenes: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认场景（不设置image_url，让前端显示占位符）
            return [
                SceneData(
                    name="开场",
                    description="故事开始的场景",
                    atmosphere="平静",
                    image_url=None
                )
            ]
    
    async def generate_storyboard(
        self,
        outline: OutlineData,
        characters: List[CharacterData],
        scenes: List[SceneData],
        style: str = "写实电影感",
        script: Optional[str] = None,
        progress: Optional[ProgressCallback] = None
    ) -> List[ShotData]:
        """
        生成分镜剧本
        
        根据大纲、角色和场景生成详细的分镜
        
        Args:
            outline: Story outline
            characters: List of characters
            scenes: List of scenes
            style: Visual style
            script: Optional script content
            progress: Optional progress callback
        """
        if not self.pipeline:
            await self.initialize_pipeline()
        
        try:
            if progress:
                await progress.update(0.1, "Preparing script...")
            
            # 如果没有提供script，从大纲生成增强的script，包含视觉细节
            if not script:
                script = f"# 故事概要\n{outline.synopsis}\n\n"
                
                # Add character descriptions for visual context
                if characters:
                    script += "# 主要角色\n"
                    for char in characters[:3]:  # Top 3 characters
                        script += f"- {char.name}: {char.description} {char.appearance}\n"
                    script += "\n"
                
                # Add scene descriptions with visual details
                script += "# 场景剧本\n"
                for i, plot in enumerate(outline.plot_summary):
                    script += f"## {plot.get('act', f'场景{i+1}')}\n"
                    script += f"{plot.get('description', '')}\n"
                    
                    # Add corresponding scene atmosphere if available
                    if i < len(scenes):
                        script += f"氛围：{scenes[i].atmosphere}\n"
                        script += f"场景描述：{scenes[i].description}\n"
                    script += "\n"
            
            if progress:
                await progress.update(0.3, "Converting characters...")
            
            # 转换角色格式为CharacterInScene
            from interfaces import CharacterInScene
            characters_in_scene = []
            for i, char in enumerate(characters):
                char_in_scene = CharacterInScene(
                    idx=i,
                    identifier_in_scene=char.name,
                    static_features=char.description,
                    dynamic_features=char.appearance,
                    is_visible=True  # Default to visible
                )
                characters_in_scene.append(char_in_scene)
            
            if progress:
                await progress.update(0.5, "Designing storyboard...")
            
            # 调用pipeline的design_storyboard方法
            # Note: Idea2VideoPipeline doesn't have design_storyboard, need to use Script2VideoPipeline's storyboard_artist
            if hasattr(self.pipeline, 'design_storyboard'):
                storyboard_brief = await self.pipeline.design_storyboard(
                    script=script,
                    characters=characters_in_scene,
                    user_requirement=f"风格：{style}"
                )
            elif hasattr(self.pipeline, 'storyboard_artist'):
                # For Idea2VideoPipeline, use storyboard_artist directly
                from agents import StoryboardArtist
                if not hasattr(self.pipeline, 'storyboard_artist'):
                    self.pipeline.storyboard_artist = StoryboardArtist(chat_model=self.pipeline.chat_model)
                
                storyboard_brief = await self.pipeline.storyboard_artist.design_storyboard(
                    script=script,
                    characters=characters_in_scene,
                    user_requirement=f"风格：{style}",
                    retry_timeout=150
                )
            else:
                raise AttributeError(f"Pipeline {type(self.pipeline).__name__} doesn't have design_storyboard or storyboard_artist")
            
            if progress:
                await progress.update(0.8, "Converting storyboard format...")
            
            # 转换为ShotData格式
            shots = []
            for shot_brief in storyboard_brief:
                # Extract camera info from visual description (simple heuristic)
                camera_angle = "中景"
                camera_movement = "稳定"
                
                visual_lower = shot_brief.visual_desc.lower()
                if "close" in visual_lower or "特写" in shot_brief.visual_desc:
                    camera_angle = "特写"
                elif "wide" in visual_lower or "远景" in shot_brief.visual_desc:
                    camera_angle = "远景"
                elif "medium" in visual_lower or "中景" in shot_brief.visual_desc:
                    camera_angle = "中景"
                
                if "pan" in visual_lower or "摇" in shot_brief.visual_desc:
                    camera_movement = "摇镜"
                elif "zoom" in visual_lower or "推" in shot_brief.visual_desc:
                    camera_movement = "推近"
                elif "track" in visual_lower or "跟" in shot_brief.visual_desc:
                    camera_movement = "跟随"
                
                shot = ShotData(
                    shot_number=shot_brief.idx + 1,
                    scene_name=scenes[0].name if scenes else "场景1",
                    visual_desc=shot_brief.visual_desc,
                    camera_angle=camera_angle,
                    camera_movement=camera_movement,
                    character_action=None,
                    dialogue=None,
                    voice_actor=None
                )
                shots.append(shot)
            
            return shots
            
        except Exception as e:
            print(f"Error generating storyboard: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认分镜
            return [
                ShotData(
                    shot_number=1,
                    scene_name=scenes[0].name if scenes else "场景1",
                    visual_desc="开场镜头，展示主要场景",
                    camera_angle="中景",
                    camera_movement="稳定",
                    character_action=None,
                    dialogue=None,
                    voice_actor=None
                ),
                ShotData(
                    shot_number=2,
                    scene_name=scenes[0].name if scenes else "场景1",
                    visual_desc="角色特写，展示表情",
                    camera_angle="特写",
                    camera_movement="推近",
                    character_action=None,
                    dialogue=None,
                    voice_actor=None
                )
            ]
    
    async def generate_video(
        self,
        storyboard: List[ShotData],
        characters: List[CharacterData],
        scenes: List[SceneData],
        style: str = "写实电影感",
        episode_id: str = "default",
        working_dir: Optional[str] = None,
        progress: Optional[ProgressCallback] = None
    ) -> Dict[str, Any]:
        """
        生成最终视频
        
        根据分镜剧本生成视频
        
        Args:
            storyboard: List of shot data
            characters: List of characters
            scenes: List of scenes
            style: Visual style
            episode_id: Episode ID for naming
            working_dir: Optional working directory
            progress: Optional progress callback
            
        Returns:
            Dictionary with video generation results
        """
        if not self.pipeline:
            await self.initialize_pipeline()
        
        try:
            # Import video generation adapter
            from workflows.video_generation_adapter import create_video_adapter
            
            # Set working directory
            if working_dir:
                self.pipeline.working_dir = working_dir
            else:
                working_dir = self.pipeline.working_dir
            
            # Create video adapter
            video_adapter = create_video_adapter(
                video_generator=self.pipeline.video_generator,
                image_generator=self.pipeline.image_generator,
                working_dir=working_dir,
                max_concurrent_shots=2
            )
            
            # Generate episode video
            result = await video_adapter.generate_episode_video(
                storyboard=storyboard,
                characters=characters,
                scenes=scenes,
                style=style,
                episode_id=episode_id,
                progress_callback=progress
            )
            
            return result
            
        except Exception as e:
            print(f"Error generating video: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


class Idea2VideoAdapter(PipelineAdapter):
    """Idea2Video模式的适配器"""
    
    def __init__(self, config_path: str = "configs/idea2video.yaml"):
        super().__init__(config_path, mode="idea")
    
    async def generate_outline(self, idea: str, style: str = "写实电影感") -> OutlineData:
        """生成大纲"""
        return await self.generate_outline_from_idea(idea, style)


class Script2VideoAdapter(PipelineAdapter):
    """Script2Video模式的适配器"""
    
    def __init__(self, config_path: str = "configs/script2video.yaml"):
        super().__init__(config_path, mode="script")
    
    async def generate_outline(self, script: str, style: str = "写实电影感") -> OutlineData:
        """生成大纲"""
        return await self.generate_outline_from_script(script, style)


# 工厂函数
def create_adapter(mode: str, config_path: Optional[str] = None) -> PipelineAdapter:
    """
    创建适配器实例
    
    Args:
        mode: 'idea' 或 'script'
        config_path: 可选的配置文件路径
    
    Returns:
        PipelineAdapter实例
    """
    if mode == "idea":
        return Idea2VideoAdapter(config_path or "configs/idea2video.yaml")
    elif mode == "script":
        return Script2VideoAdapter(config_path or "configs/script2video.yaml")
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'idea' or 'script'")