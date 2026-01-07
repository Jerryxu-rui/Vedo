"""
Direct Pipeline API Routes
直接管道API路由 - 支持直接调用idea2video和script2video管道
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import os
import uuid

from database import get_db
from database_models import Episode
from pipelines.idea2video_pipeline import Idea2VideoPipeline
from pipelines.script2video_pipeline import Script2VideoPipeline

router = APIRouter(prefix="/api/v1/direct-pipeline", tags=["direct-pipeline"])


# ============================================================================
# Request/Response Models
# ============================================================================

class Idea2VideoRequest(BaseModel):
    """Idea转视频请求"""
    idea: str = Field(..., description="User's creative idea")
    user_requirement: str = Field(
        default="For adults, do not exceed 3 scenes. Each scene should be no more than 5 shots.",
        description="User requirements for the video"
    )
    style: str = Field(default="Cartoon style", description="Visual style")
    series_id: Optional[str] = Field(default=None, description="Optional series ID")
    episode_number: Optional[int] = Field(default=None, description="Optional episode number")
    title: Optional[str] = Field(default=None, description="Optional video title")


class Script2VideoRequest(BaseModel):
    """Script转视频请求"""
    script: str = Field(..., description="Complete script content")
    user_requirement: str = Field(
        default="Fast-paced with no more than 15 shots.",
        description="User requirements for the video"
    )
    style: str = Field(default="Anime Style", description="Visual style")
    series_id: Optional[str] = Field(default=None, description="Optional series ID")
    episode_number: Optional[int] = Field(default=None, description="Optional episode number")
    title: Optional[str] = Field(default=None, description="Optional video title")


class PipelineJobResponse(BaseModel):
    """管道任务响应"""
    job_id: str
    episode_id: Optional[str] = None
    status: str
    message: str
    pipeline_type: str
    created_at: str


class PipelineStatusResponse(BaseModel):
    """管道状态响应"""
    job_id: str
    episode_id: Optional[str] = None
    status: str
    pipeline_type: str
    progress: Optional[float] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


# ============================================================================
# Job Management
# ============================================================================

# In-memory job storage (in production, use Redis or database)
pipeline_jobs: Dict[str, Dict[str, Any]] = {}


def create_job(
    pipeline_type: str,
    episode_id: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None
) -> str:
    """创建管道任务"""
    job_id = str(uuid.uuid4())
    pipeline_jobs[job_id] = {
        "job_id": job_id,
        "episode_id": episode_id,
        "pipeline_type": pipeline_type,
        "status": "pending",
        "progress": 0.0,
        "video_path": None,
        "error": None,
        "request_data": request_data or {},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return job_id


def update_job(job_id: str, **kwargs):
    """更新任务状态"""
    if job_id in pipeline_jobs:
        pipeline_jobs[job_id].update(kwargs)
        pipeline_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """获取任务信息"""
    return pipeline_jobs.get(job_id)


# ============================================================================
# Background Tasks
# ============================================================================

async def run_idea2video_pipeline(
    job_id: str,
    idea: str,
    user_requirement: str,
    style: str,
    episode_id: Optional[str] = None
):
    """后台运行Idea2Video管道"""
    try:
        update_job(job_id, status="running", progress=0.1)
        
        # 创建工作目录
        working_dir = f".working_dir/idea2video/{job_id}"
        os.makedirs(working_dir, exist_ok=True)
        
        # 初始化管道
        pipeline = Idea2VideoPipeline.init_from_config(
            config_path="configs/idea2video.yaml"
        )
        pipeline.working_dir = working_dir
        
        update_job(job_id, progress=0.2)
        
        # 执行管道
        print(f"[Idea2Video Pipeline] Starting for job {job_id}")
        print(f"[Idea2Video Pipeline] Idea: {idea[:100]}...")
        print(f"[Idea2Video Pipeline] Style: {style}")
        
        final_video_path = await pipeline(
            idea=idea,
            user_requirement=user_requirement,
            style=style
        )
        
        update_job(
            job_id,
            status="completed",
            progress=1.0,
            video_path=final_video_path
        )
        
        print(f"[Idea2Video Pipeline] Completed for job {job_id}")
        print(f"[Idea2Video Pipeline] Video saved to: {final_video_path}")
        
    except Exception as e:
        print(f"[Idea2Video Pipeline] Error for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        update_job(
            job_id,
            status="failed",
            error=str(e)
        )


async def run_script2video_pipeline(
    job_id: str,
    script: str,
    user_requirement: str,
    style: str,
    episode_id: Optional[str] = None
):
    """后台运行Script2Video管道"""
    try:
        update_job(job_id, status="running", progress=0.1)
        
        # 创建工作目录
        working_dir = f".working_dir/script2video/{job_id}"
        os.makedirs(working_dir, exist_ok=True)
        
        # 初始化管道
        pipeline = Script2VideoPipeline.init_from_config(
            config_path="configs/script2video.yaml"
        )
        pipeline.working_dir = working_dir
        
        update_job(job_id, progress=0.2)
        
        # 执行管道
        print(f"[Script2Video Pipeline] Starting for job {job_id}")
        print(f"[Script2Video Pipeline] Script length: {len(script)} characters")
        print(f"[Script2Video Pipeline] Style: {style}")
        
        final_video_path = await pipeline(
            script=script,
            user_requirement=user_requirement,
            style=style
        )
        
        update_job(
            job_id,
            status="completed",
            progress=1.0,
            video_path=final_video_path
        )
        
        print(f"[Script2Video Pipeline] Completed for job {job_id}")
        print(f"[Script2Video Pipeline] Video saved to: {final_video_path}")
        
    except Exception as e:
        print(f"[Script2Video Pipeline] Error for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        update_job(
            job_id,
            status="failed",
            error=str(e)
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/idea2video", response_model=PipelineJobResponse, deprecated=True)
async def create_idea2video_job(
    request: Idea2VideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建Idea转视频任务
    
    **⚠️ DEPRECATED**: 此端点已弃用，将在v4.0中移除。
    请使用统一端点: `POST /api/v1/videos/generate`
    
    **迁移指南**:
    ```python
    # 旧方式 (已弃用)
    POST /api/v1/direct-pipeline/idea2video
    {
        "idea": "your idea",
        "style": "Cartoon style"
    }
    
    # 新方式 (推荐)
    POST /api/v1/videos/generate
    {
        "mode": "idea",
        "content": "your idea",
        "style": "Cartoon style"
    }
    ```
    
    从创意想法直接生成完整视频，包含以下步骤：
    1. 根据idea生成故事
    2. 提取角色并生成角色肖像
    3. 根据故事编写剧本
    4. 为每个场景生成视频
    5. 合并所有场景视频
    
    这是一个长时间运行的任务，会在后台执行。
    使用返回的job_id查询任务状态和结果。
    """
    try:
        # 可选：创建Episode记录
        episode_id = None
        if request.series_id and request.episode_number:
            episode = Episode(
                series_id=request.series_id,
                episode_number=request.episode_number,
                title=request.title or f"Episode {request.episode_number}",
                status="generating"
            )
            db.add(episode)
            db.commit()
            episode_id = episode.id
        
        # 创建任务
        job_id = create_job(
            pipeline_type="idea2video",
            episode_id=episode_id,
            request_data=request.dict()
        )
        
        # 在后台运行管道
        background_tasks.add_task(
            run_idea2video_pipeline,
            job_id=job_id,
            idea=request.idea,
            user_requirement=request.user_requirement,
            style=request.style,
            episode_id=episode_id
        )
        
        return PipelineJobResponse(
            job_id=job_id,
            episode_id=episode_id,
            status="pending",
            message="Idea2Video pipeline job created and started",
            pipeline_type="idea2video",
            created_at=pipeline_jobs[job_id]["created_at"]
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/script2video", response_model=PipelineJobResponse, deprecated=True)
async def create_script2video_job(
    request: Script2VideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建Script转视频任务
    
    **⚠️ DEPRECATED**: 此端点已弃用，将在v4.0中移除。
    请使用统一端点: `POST /api/v1/videos/generate`
    
    **迁移指南**:
    ```python
    # 旧方式 (已弃用)
    POST /api/v1/direct-pipeline/script2video
    {
        "script": "your script",
        "style": "Anime Style"
    }
    
    # 新方式 (推荐)
    POST /api/v1/videos/generate
    {
        "mode": "script",
        "content": "your script",
        "style": "Anime Style"
    }
    ```
    
    从完整剧本直接生成视频，包含以下步骤：
    1. 提取角色并生成角色肖像
    2. 设计分镜剧本
    3. 分解视觉描述
    4. 构建镜头树
    5. 为每个镜头生成关键帧
    6. 生成视频片段
    7. 合并所有视频片段
    
    这是一个长时间运行的任务，会在后台执行。
    使用返回的job_id查询任务状态和结果。
    """
    try:
        # 可选：创建Episode记录
        episode_id = None
        if request.series_id and request.episode_number:
            episode = Episode(
                series_id=request.series_id,
                episode_number=request.episode_number,
                title=request.title or f"Episode {request.episode_number}",
                status="generating"
            )
            db.add(episode)
            db.commit()
            episode_id = episode.id
        
        # 创建任务
        job_id = create_job(
            pipeline_type="script2video",
            episode_id=episode_id,
            request_data=request.dict()
        )
        
        # 在后台运行管道
        background_tasks.add_task(
            run_script2video_pipeline,
            job_id=job_id,
            script=request.script,
            user_requirement=request.user_requirement,
            style=request.style,
            episode_id=episode_id
        )
        
        return PipelineJobResponse(
            job_id=job_id,
            episode_id=episode_id,
            status="pending",
            message="Script2Video pipeline job created and started",
            pipeline_type="script2video",
            created_at=pipeline_jobs[job_id]["created_at"]
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_job_status(job_id: str):
    """
    获取管道任务状态
    
    查询任务的当前状态、进度和结果。
    
    状态值：
    - pending: 任务已创建，等待执行
    - running: 任务正在执行
    - completed: 任务已完成
    - failed: 任务失败
    """
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return PipelineStatusResponse(
        job_id=job["job_id"],
        episode_id=job.get("episode_id"),
        status=job["status"],
        pipeline_type=job["pipeline_type"],
        progress=job.get("progress"),
        video_path=job.get("video_path"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )


@router.get("/jobs", response_model=list[PipelineStatusResponse])
async def list_pipeline_jobs(
    pipeline_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """
    列出所有管道任务
    
    可选过滤条件：
    - pipeline_type: 'idea2video' 或 'script2video'
    - status: 'pending', 'running', 'completed', 'failed'
    - limit: 返回的最大任务数量
    """
    jobs = list(pipeline_jobs.values())
    
    # 过滤
    if pipeline_type:
        jobs = [j for j in jobs if j["pipeline_type"] == pipeline_type]
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    
    # 按创建时间倒序排序
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 限制数量
    jobs = jobs[:limit]
    
    return [
        PipelineStatusResponse(
            job_id=job["job_id"],
            episode_id=job.get("episode_id"),
            status=job["status"],
            pipeline_type=job["pipeline_type"],
            progress=job.get("progress"),
            video_path=job.get("video_path"),
            error=job.get("error"),
            created_at=job["created_at"],
            updated_at=job["updated_at"]
        )
        for job in jobs
    ]


@router.delete("/job/{job_id}")
async def cancel_pipeline_job(job_id: str):
    """
    取消管道任务
    
    注意：已经在运行中的任务可能无法立即停止，
    但会被标记为已取消，不会继续后续步骤。
    """
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job['status']}"
        )
    
    update_job(job_id, status="cancelled")
    
    return {"message": f"Job {job_id} cancelled", "job_id": job_id}


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "direct-pipeline-api",
        "total_jobs": len(pipeline_jobs),
        "active_jobs": len([j for j in pipeline_jobs.values() if j["status"] == "running"])
    }