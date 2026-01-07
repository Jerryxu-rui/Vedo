"""
Unified Job Manager Service
Provides database-backed job storage replacing in-memory dictionaries
Supports migration from in-memory to database storage
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database_models import VideoGenerationJob
from database import get_db


class JobManager:
    """
    Unified job manager with database persistence
    Replaces in-memory job dictionaries across the application
    """
    
    def __init__(self):
        """Initialize job manager"""
        self._memory_cache: Dict[str, Dict[str, Any]] = {}  # Optional in-memory cache
        self._cache_enabled = True
    
    def create_job(
        self,
        job_id: str,
        job_type: str,
        content: str,
        user_requirement: Optional[str] = None,
        style: Optional[str] = None,
        project_title: Optional[str] = None,
        mode: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        working_dir: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Create a new job in database
        
        Args:
            job_id: Unique job identifier
            job_type: Type of job (idea2video, script2video, conversational)
            content: Main content (idea or script)
            user_requirement: User requirements
            style: Visual style
            project_title: Project title
            mode: Generation mode (idea/script)
            request_data: Full request payload
            working_dir: Working directory path
            db: Database session (optional, will create if not provided)
        
        Returns:
            Job dictionary
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            job = VideoGenerationJob(
                id=job_id,
                job_type=job_type,
                mode=mode,
                status='queued',
                content=content,
                user_requirement=user_requirement,
                style=style,
                project_title=project_title,
                request_data=request_data or {},
                working_dir=working_dir,
                progress=0.0
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            job_dict = job.to_dict()
            
            # Update cache
            if self._cache_enabled:
                self._memory_cache[job_id] = job_dict
            
            return job_dict
        
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create job: {str(e)}")
        finally:
            if should_close_db:
                db.close()
    
    def get_job(self, job_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """
        Get job by ID
        
        Args:
            job_id: Job identifier
            db: Database session (optional)
        
        Returns:
            Job dictionary or None if not found
        """
        # Check cache first
        if self._cache_enabled and job_id in self._memory_cache:
            return self._memory_cache[job_id]
        
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            job = db.query(VideoGenerationJob).filter(VideoGenerationJob.id == job_id).first()
            
            if not job:
                return None
            
            job_dict = job.to_dict()
            
            # Update cache
            if self._cache_enabled:
                self._memory_cache[job_id] = job_dict
            
            return job_dict
        
        finally:
            if should_close_db:
                db.close()
    
    def update_job(
        self,
        job_id: str,
        updates: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update job fields
        
        Args:
            job_id: Job identifier
            updates: Dictionary of fields to update
            db: Database session (optional)
        
        Returns:
            Updated job dictionary or None if not found
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            job = db.query(VideoGenerationJob).filter(VideoGenerationJob.id == job_id).first()
            
            if not job:
                return None
            
            # Update fields
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            # Update timestamp
            job.updated_at = datetime.utcnow()
            
            # Handle status transitions
            if 'status' in updates:
                if updates['status'] == 'processing' and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif updates['status'] in ['completed', 'failed', 'cancelled'] and not job.completed_at:
                    job.completed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(job)
            
            job_dict = job.to_dict()
            
            # Update cache
            if self._cache_enabled:
                self._memory_cache[job_id] = job_dict
            
            return job_dict
        
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update job: {str(e)}")
        finally:
            if should_close_db:
                db.close()
    
    def delete_job(self, job_id: str, db: Optional[Session] = None) -> bool:
        """
        Delete job from database
        
        Args:
            job_id: Job identifier
            db: Database session (optional)
        
        Returns:
            True if deleted, False if not found
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            job = db.query(VideoGenerationJob).filter(VideoGenerationJob.id == job_id).first()
            
            if not job:
                return False
            
            db.delete(job)
            db.commit()
            
            # Remove from cache
            if self._cache_enabled and job_id in self._memory_cache:
                del self._memory_cache[job_id]
            
            return True
        
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to delete job: {str(e)}")
        finally:
            if should_close_db:
                db.close()
    
    def list_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        List jobs with filtering and pagination
        
        Args:
            limit: Maximum number of jobs to return
            offset: Pagination offset
            status: Filter by status (optional)
            job_type: Filter by job type (optional)
            db: Database session (optional)
        
        Returns:
            Dictionary with jobs list and pagination info
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            query = db.query(VideoGenerationJob)
            
            # Apply filters
            if status:
                query = query.filter(VideoGenerationJob.status == status)
            if job_type:
                query = query.filter(VideoGenerationJob.job_type == job_type)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            jobs = query.order_by(desc(VideoGenerationJob.created_at)).offset(offset).limit(limit).all()
            
            return {
                'jobs': [job.to_dict() for job in jobs],
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                }
            }
        
        finally:
            if should_close_db:
                db.close()
    
    def update_progress(
        self,
        job_id: str,
        progress: float,
        current_stage: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update job progress
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            current_stage: Current stage description
            db: Database session (optional)
        
        Returns:
            Updated job dictionary or None if not found
        """
        updates = {'progress': progress}
        if current_stage:
            updates['current_stage'] = current_stage
        
        return self.update_job(job_id, updates, db)
    
    def update_shots(
        self,
        job_id: str,
        total_shots: Optional[int] = None,
        completed_shots: Optional[int] = None,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update shot counts
        
        Args:
            job_id: Job identifier
            total_shots: Total number of shots
            completed_shots: Number of completed shots
            db: Database session (optional)
        
        Returns:
            Updated job dictionary or None if not found
        """
        updates = {}
        if total_shots is not None:
            updates['total_shots'] = total_shots
        if completed_shots is not None:
            updates['completed_shots'] = completed_shots
        
        # Auto-calculate progress if both values available
        if total_shots and completed_shots:
            updates['progress'] = (completed_shots / total_shots) * 100
        
        return self.update_job(job_id, updates, db)
    
    def mark_completed(
        self,
        job_id: str,
        result_data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Mark job as completed
        
        Args:
            job_id: Job identifier
            result_data: Final result data
            db: Database session (optional)
        
        Returns:
            Updated job dictionary or None if not found
        """
        return self.update_job(job_id, {
            'status': 'completed',
            'progress': 100.0,
            'result_data': result_data
        }, db)
    
    def mark_failed(
        self,
        job_id: str,
        error_message: str,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Mark job as failed
        
        Args:
            job_id: Job identifier
            error_message: Error description
            db: Database session (optional)
        
        Returns:
            Updated job dictionary or None if not found
        """
        return self.update_job(job_id, {
            'status': 'failed',
            'error_message': error_message
        }, db)
    
    def get_active_jobs(self, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """
        Get all active (queued or processing) jobs
        
        Args:
            db: Database session (optional)
        
        Returns:
            List of active job dictionaries
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            jobs = db.query(VideoGenerationJob).filter(
                VideoGenerationJob.status.in_(['queued', 'processing'])
            ).order_by(VideoGenerationJob.created_at).all()
            
            return [job.to_dict() for job in jobs]
        
        finally:
            if should_close_db:
                db.close()
    
    def clear_cache(self):
        """Clear in-memory cache"""
        self._memory_cache.clear()
    
    def migrate_from_dict(self, jobs_dict: Dict[str, Dict[str, Any]], db: Optional[Session] = None):
        """
        Migrate jobs from in-memory dictionary to database
        
        Args:
            jobs_dict: Dictionary of jobs to migrate
            db: Database session (optional)
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            migrated_count = 0
            
            for job_id, job_data in jobs_dict.items():
                # Check if job already exists
                existing = db.query(VideoGenerationJob).filter(VideoGenerationJob.id == job_id).first()
                if existing:
                    continue
                
                # Create new job from dict data
                job = VideoGenerationJob(
                    id=job_id,
                    job_type=job_data.get('type', 'unknown'),
                    status=job_data.get('status', 'queued'),
                    content=job_data.get('request', {}).get('idea') or job_data.get('request', {}).get('script', ''),
                    user_requirement=job_data.get('request', {}).get('user_requirement'),
                    style=job_data.get('request', {}).get('style'),
                    project_title=job_data.get('request', {}).get('project_title'),
                    request_data=job_data.get('request', {}),
                    working_dir=job_data.get('working_dir'),
                    progress=job_data.get('progress', 0.0),
                    current_stage=job_data.get('current_stage'),
                    result_data=job_data.get('result'),
                    error_message=job_data.get('error'),
                    created_at=datetime.fromisoformat(job_data['created_at']) if 'created_at' in job_data else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(job_data['updated_at']) if 'updated_at' in job_data else datetime.utcnow()
                )
                
                db.add(job)
                migrated_count += 1
            
            db.commit()
            print(f"[JobManager] Migrated {migrated_count} jobs to database")
        
        except Exception as e:
            db.rollback()
            print(f"[JobManager] Migration failed: {str(e)}")
            raise
        finally:
            if should_close_db:
                db.close()


# Global job manager instance
job_manager = JobManager()