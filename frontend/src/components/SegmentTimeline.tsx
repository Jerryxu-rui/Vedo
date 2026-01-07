/**
 * SegmentTimeline Component
 * Visual timeline with drag-and-drop for segment management
 */

import React, { useState, useRef, useEffect } from 'react';
import type { VideoSegment } from '../types/segment';
import './SegmentTimeline.css';

interface SegmentTimelineProps {
  segments: VideoSegment[];
  onSegmentClick?: (segment: VideoSegment) => void;
  onSegmentReorder?: (segmentId: string, newPosition: number) => void;
  onSegmentDelete?: (segmentId: string) => void;
  selectedSegmentId?: string;
  showApprovedOnly?: boolean;
}

export const SegmentTimeline: React.FC<SegmentTimelineProps> = ({
  segments,
  onSegmentClick,
  onSegmentReorder,
  onSegmentDelete,
  selectedSegmentId,
  showApprovedOnly = false
}) => {
  const [draggedSegment, setDraggedSegment] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [filteredSegments, setFilteredSegments] = useState<VideoSegment[]>([]);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [sortBy, setSortBy] = useState<'number' | 'status' | 'quality'>('number');
  const timelineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let filtered = [...segments];

    // Filter by approval status if needed
    if (showApprovedOnly) {
      filtered = filtered.filter(s => s.approval_status === 'approved');
    }

    // Sort segments
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'number':
          return a.segment_number - b.segment_number;
        case 'status':
          const statusOrder = { completed: 0, generating: 1, pending: 2, failed: 3 };
          return statusOrder[a.status] - statusOrder[b.status];
        case 'quality':
          return (b.quality_score || 0) - (a.quality_score || 0);
        default:
          return 0;
      }
    });

    setFilteredSegments(filtered);
  }, [segments, showApprovedOnly, sortBy]);

  const handleDragStart = (e: React.DragEvent, segmentId: string) => {
    setDraggedSegment(segmentId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  const handleDrop = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    
    if (!draggedSegment || !onSegmentReorder) return;

    const draggedIndex = filteredSegments.findIndex(s => s.id === draggedSegment);
    
    if (draggedIndex !== targetIndex) {
      onSegmentReorder(draggedSegment, targetIndex);
    }

    setDraggedSegment(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedSegment(null);
    setDragOverIndex(null);
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'completed': return '✓';
      case 'generating': return '⟳';
      case 'failed': return '✗';
      default: return '○';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'generating': return '#f59e0b';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getApprovalBadge = (status: string): string => {
    switch (status) {
      case 'approved': return '✓';
      case 'rejected': return '✗';
      default: return '?';
    }
  };

  const getTotalDuration = (): string => {
    const total = filteredSegments.reduce((sum, seg) => sum + (seg.duration || 0), 0);
    const mins = Math.floor(total / 60);
    const secs = Math.floor(total % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getApprovedCount = (): number => {
    return filteredSegments.filter(s => s.approval_status === 'approved').length;
  };

  const getCompletedCount = (): number => {
    return filteredSegments.filter(s => s.status === 'completed').length;
  };

  return (
    <div className="segment-timeline" ref={timelineRef}>
      <div className="timeline-header">
        <div className="timeline-info">
          <h3>Video Timeline</h3>
          <div className="timeline-stats">
            <span className="stat">
              {filteredSegments.length} segments
            </span>
            <span className="stat">
              {getCompletedCount()}/{filteredSegments.length} completed
            </span>
            <span className="stat">
              {getApprovedCount()}/{filteredSegments.length} approved
            </span>
            <span className="stat">
              Total: {getTotalDuration()}
            </span>
          </div>
        </div>

        <div className="timeline-controls">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="sort-select"
          >
            <option value="number">Sort by Number</option>
            <option value="status">Sort by Status</option>
            <option value="quality">Sort by Quality</option>
          </select>

          <div className="view-toggle">
            <button
              className={`view-button ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid view"
            >
              ⊞
            </button>
            <button
              className={`view-button ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List view"
            >
              ☰
            </button>
          </div>
        </div>
      </div>

      <div className={`timeline-content ${viewMode}`}>
        {filteredSegments.length === 0 ? (
          <div className="empty-timeline">
            <p>No segments available</p>
            {showApprovedOnly && (
              <p className="hint">Try disabling "Show Approved Only" filter</p>
            )}
          </div>
        ) : (
          filteredSegments.map((segment, index) => (
            <div
              key={segment.id}
              className={`segment-card ${viewMode} ${
                selectedSegmentId === segment.id ? 'selected' : ''
              } ${draggedSegment === segment.id ? 'dragging' : ''} ${
                dragOverIndex === index ? 'drag-over' : ''
              }`}
              draggable={!!onSegmentReorder}
              onDragStart={(e) => handleDragStart(e, segment.id)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              onClick={() => onSegmentClick && onSegmentClick(segment)}
            >
              <div className="segment-thumbnail">
                {segment.thumbnail_url ? (
                  <img src={segment.thumbnail_url} alt={segment.title} />
                ) : (
                  <div className="no-thumbnail">
                    <span className="segment-number">#{segment.segment_number}</span>
                  </div>
                )}
                
                <div className="segment-overlay">
                  <span
                    className="status-icon"
                    style={{ color: getStatusColor(segment.status) }}
                  >
                    {getStatusIcon(segment.status)}
                  </span>
                  {segment.duration && (
                    <span className="duration">
                      {Math.floor(segment.duration)}s
                    </span>
                  )}
                </div>

                <div className="approval-badge" data-status={segment.approval_status}>
                  {getApprovalBadge(segment.approval_status)}
                </div>
              </div>

              <div className="segment-info">
                <div className="segment-title">
                  <span className="segment-number">#{segment.segment_number}</span>
                  <span className="title-text">{segment.title}</span>
                </div>

                {viewMode === 'list' && segment.description && (
                  <p className="segment-description">{segment.description}</p>
                )}

                <div className="segment-metadata">
                  <span className="status-badge" style={{ backgroundColor: getStatusColor(segment.status) }}>
                    {segment.status}
                  </span>
                  {segment.quality_score && (
                    <span className="quality-badge">
                      {(segment.quality_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>

              {onSegmentDelete && (
                <button
                  className="delete-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSegmentDelete(segment.id);
                  }}
                  title="Delete segment"
                >
                  ✕
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {onSegmentReorder && filteredSegments.length > 0 && (
        <div className="timeline-footer">
          <p className="drag-hint">💡 Drag and drop segments to reorder them</p>
        </div>
      )}
    </div>
  );
};

export default SegmentTimeline;