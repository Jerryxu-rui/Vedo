/**
 * SegmentPreview Component
 * Video player with review controls for individual segments
 */

import React, { useState, useRef, useEffect } from 'react';
import type { VideoSegment } from '../types/segment';
import './SegmentPreview.css';

interface SegmentPreviewProps {
  segment: VideoSegment;
  onApprove?: (segmentId: string, rating?: number, feedback?: string) => void;
  onReject?: (segmentId: string, reason: string, changes?: any) => void;
  onRegenerate?: (segmentId: string, changes: any) => void;
  onClose?: () => void;
  showControls?: boolean;
}

export const SegmentPreview: React.FC<SegmentPreviewProps> = ({
  segment,
  onApprove,
  onReject,
  onRegenerate,
  onClose,
  showControls = true
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [editedPrompt, setEditedPrompt] = useState(segment.generation_prompt || segment.prompt || '');
  const [editedTitle, setEditedTitle] = useState(segment.title);
  const [editedDescription, setEditedDescription] = useState(segment.description || '');

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => setCurrentTime(video.currentTime);
    const handleDurationChange = () => setDuration(video.duration);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, []);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const time = parseFloat(e.target.value);
    video.currentTime = time;
    setCurrentTime(time);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const vol = parseFloat(e.target.value);
    video.volume = vol;
    setVolume(vol);
    setIsMuted(vol === 0);
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handlePlaybackRateChange = (rate: number) => {
    const video = videoRef.current;
    if (!video) return;

    video.playbackRate = rate;
    setPlaybackRate(rate);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleApprove = () => {
    if (onApprove) {
      onApprove(segment.id, rating || undefined, feedback || undefined);
      setShowReviewForm(false);
      setRating(0);
      setFeedback('');
    }
  };

  const handleReject = () => {
    if (onReject && rejectReason) {
      onReject(segment.id, rejectReason);
      setShowReviewForm(false);
      setRejectReason('');
    }
  };

  const handleEdit = () => {
    setShowEditForm(true);
    setEditedPrompt(segment.generation_prompt || segment.prompt || '');
    setEditedTitle(segment.title);
    setEditedDescription(segment.description || '');
  };

  const handleSaveEdit = () => {
    if (onRegenerate && editedPrompt) {
      onRegenerate(segment.id, {
        prompt: editedPrompt,
        title: editedTitle,
        description: editedDescription
      });
      setShowEditForm(false);
    }
  };

  const handleCancelEdit = () => {
    setShowEditForm(false);
    setEditedPrompt(segment.generation_prompt || segment.prompt || '');
    setEditedTitle(segment.title);
    setEditedDescription(segment.description || '');
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'generating': return '#f59e0b';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getApprovalStatusColor = (status: string): string => {
    switch (status) {
      case 'approved': return '#10b981';
      case 'rejected': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div className="segment-preview">
      <div className="segment-preview-header">
        <div className="segment-info">
          <h3>Segment {segment.segment_number}: {segment.title}</h3>
          <div className="segment-metadata">
            <span className="status-badge" style={{ backgroundColor: getStatusColor(segment.status) }}>
              {segment.status}
            </span>
            <span className="status-badge" style={{ backgroundColor: getApprovalStatusColor(segment.approval_status) }}>
              {segment.approval_status}
            </span>
            {segment.quality_score && (
              <span className="quality-score">
                Quality: {(segment.quality_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
        {onClose && (
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        )}
      </div>

      <div className="video-container">
        {segment.video_url ? (
          <video
            ref={videoRef}
            src={segment.video_url}
            poster={segment.thumbnail_url}
            className="video-player"
          />
        ) : (
          <div className="video-placeholder">
            {segment.thumbnail_url ? (
              <img src={segment.thumbnail_url} alt="Segment thumbnail" />
            ) : (
              <div className="no-video">No video available</div>
            )}
          </div>
        )}

        {segment.video_url && (
          <div className="video-controls">
            <button className="control-button" onClick={togglePlay}>
              {isPlaying ? '⏸' : '▶'}
            </button>

            <div className="time-display">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            <input
              type="range"
              min="0"
              max={duration || 0}
              value={currentTime}
              onChange={handleSeek}
              className="seek-bar"
            />

            <button className="control-button" onClick={toggleMute}>
              {isMuted ? '🔇' : '🔊'}
            </button>

            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={volume}
              onChange={handleVolumeChange}
              className="volume-slider"
            />

            <select
              value={playbackRate}
              onChange={(e) => handlePlaybackRateChange(parseFloat(e.target.value))}
              className="playback-rate-select"
            >
              <option value="0.5">0.5x</option>
              <option value="0.75">0.75x</option>
              <option value="1">1x</option>
              <option value="1.25">1.25x</option>
              <option value="1.5">1.5x</option>
              <option value="2">2x</option>
            </select>
          </div>
        )}
      </div>

      {segment.description && (
        <div className="segment-description">
          <h4>Description</h4>
          <p>{segment.description}</p>
        </div>
      )}

      {segment.generation_prompt && (
        <div className="segment-prompt">
          <h4>Generation Prompt</h4>
          <p>{segment.generation_prompt}</p>
        </div>
      )}

      {showControls && segment.status === 'completed' && (
        <div className="review-controls">
          {!showReviewForm && !showEditForm ? (
            <div className="review-buttons">
              <button
                className="approve-button"
                onClick={() => setShowReviewForm(true)}
                disabled={segment.approval_status === 'approved'}
              >
                ✓ Approve
              </button>
              <button
                className="reject-button"
                onClick={() => setShowReviewForm(true)}
                disabled={segment.approval_status === 'rejected'}
              >
                ✗ Reject
              </button>
              <button
                className="edit-button"
                onClick={handleEdit}
              >
                ✏️ Edit
              </button>
              {onRegenerate && (
                <button
                  className="regenerate-button"
                  onClick={() => onRegenerate(segment.id, {})}
                >
                  🔄 Regenerate
                </button>
              )}
            </div>
          ) : showReviewForm ? (
            <div className="review-form">
              <h4>Review Segment</h4>
              
              <div className="rating-section">
                <label>Rating (optional):</label>
                <div className="star-rating">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      className={`star ${rating >= star ? 'active' : ''}`}
                      onClick={() => setRating(star)}
                    >
                      ★
                    </button>
                  ))}
                </div>
              </div>

              <div className="feedback-section">
                <label>Feedback:</label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Add your feedback here..."
                  rows={4}
                />
              </div>

              <div className="reject-section">
                <label>Rejection Reason (if rejecting):</label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Explain why you're rejecting this segment..."
                  rows={3}
                />
              </div>

              <div className="form-actions">
                <button className="approve-button" onClick={handleApprove}>
                  Submit Approval
                </button>
                <button
                  className="reject-button"
                  onClick={handleReject}
                  disabled={!rejectReason}
                >
                  Submit Rejection
                </button>
                <button
                  className="cancel-button"
                  onClick={() => {
                    setShowReviewForm(false);
                    setRating(0);
                    setFeedback('');
                    setRejectReason('');
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : showEditForm ? (
            <div className="edit-form">
              <h4>Edit Segment</h4>
              
              <div className="edit-section">
                <label>Title:</label>
                <input
                  type="text"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  placeholder="Segment title..."
                  className="edit-input"
                />
              </div>

              <div className="edit-section">
                <label>Description:</label>
                <textarea
                  value={editedDescription}
                  onChange={(e) => setEditedDescription(e.target.value)}
                  placeholder="Segment description..."
                  rows={3}
                  className="edit-textarea"
                />
              </div>

              <div className="edit-section">
                <label>Generation Prompt:</label>
                <textarea
                  value={editedPrompt}
                  onChange={(e) => setEditedPrompt(e.target.value)}
                  placeholder="Edit the prompt for regenerating this segment..."
                  rows={6}
                  className="edit-textarea"
                />
                <p className="edit-hint">
                  💡 Modify the prompt to change how this segment is generated.
                  Click "Save & Regenerate" to create a new version with your changes.
                </p>
              </div>

              <div className="form-actions">
                <button
                  className="save-button"
                  onClick={handleSaveEdit}
                  disabled={!editedPrompt.trim()}
                >
                  💾 Save & Regenerate
                </button>
                <button
                  className="cancel-button"
                  onClick={handleCancelEdit}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default SegmentPreview;