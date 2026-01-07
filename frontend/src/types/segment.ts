/**
 * Shared type definitions for video segments
 */

export interface VideoSegment {
  id: string;
  episode_id: string;
  segment_number: number;
  title: string;
  description?: string;
  prompt?: string;
  video_url?: string;
  thumbnail_url?: string;
  duration?: number;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  approval_status: 'pending' | 'approved' | 'rejected';
  quality_score?: number;
  generation_prompt?: string;
  parent_segment_id?: string | null;
  version?: number;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface CompilationJob {
  id: string;
  episode_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  segment_ids: string[];
  transition_style: string;
  output_video_url?: string;
  output_duration?: number;
  output_file_size?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface CompilationConfig {
  segment_ids?: string[];
  transition_style: 'cut' | 'fade' | 'dissolve';
  audio_config: {
    volume_normalization: boolean;
    target_volume: number;
    background_music?: string;
    music_volume: number;
  };
}