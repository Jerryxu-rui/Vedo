/**
 * CompilationPanel Component
 * Controls for compiling approved segments into final video
 */

import React, { useState, useEffect } from 'react';
import type { VideoSegment, CompilationJob, CompilationConfig } from '../types/segment';
import './CompilationPanel.css';

interface CompilationPanelProps {
  episodeId: string;
  segments: VideoSegment[];
  onCompile: (config: CompilationConfig) => void;
  onCancel?: (jobId: string) => void;
  onDownload?: (jobId: string) => void;
  currentJob?: CompilationJob;
  previousJobs?: CompilationJob[];
}

export const CompilationPanel: React.FC<CompilationPanelProps> = ({
  episodeId,
  segments,
  onCompile,
  onCancel,
  onDownload,
  currentJob,
  previousJobs = []
}) => {
  const [selectedSegments, setSelectedSegments] = useState<string[]>([]);
  const [transitionStyle, setTransitionStyle] = useState<'cut' | 'fade' | 'dissolve'>('cut');
  const [volumeNormalization, setVolumeNormalization] = useState(true);
  const [targetVolume, setTargetVolume] = useState(0.8);
  const [musicVolume, setMusicVolume] = useState(0.3);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const approvedSegments = segments.filter(s => s.approval_status === 'approved');

  useEffect(() => {
    // Auto-select all approved segments by default
    if (selectedSegments.length === 0 && approvedSegments.length > 0) {
      setSelectedSegments(approvedSegments.map(s => s.id));
    }
  }, [approvedSegments]);

  const handleCompile = () => {
    const config: CompilationConfig = {
      segment_ids: selectedSegments.length > 0 ? selectedSegments : undefined,
      transition_style: transitionStyle,
      audio_config: {
        volume_normalization: volumeNormalization,
        target_volume: targetVolume,
        music_volume: musicVolume
      }
    };

    onCompile(config);
  };

  const toggleSegmentSelection = (segmentId: string) => {
    setSelectedSegments(prev =>
      prev.includes(segmentId)
        ? prev.filter(id => id !== segmentId)
        : [...prev, segmentId]
    );
  };

  const selectAllSegments = () => {
    setSelectedSegments(approvedSegments.map(s => s.id));
  };

  const deselectAllSegments = () => {
    setSelectedSegments([]);
  };

  const getTotalDuration = (): string => {
    const selected = segments.filter(s => selectedSegments.includes(s.id));
    const total = selected.reduce((sum, seg) => sum + (seg.duration || 0), 0);
    const mins = Math.floor(total / 60);
    const secs = Math.floor(total % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'processing': return '#f59e0b';
      case 'failed': return '#ef4444';
      case 'cancelled': return '#6b7280';
      default: return '#6b7280';
    }
  };

  return (
    <div className="compilation-panel">
      <div className="panel-header">
        <h3>Compile Final Video</h3>
        <p className="panel-description">
          Select segments and configure compilation settings
        </p>
      </div>

      {currentJob && currentJob.status === 'processing' && (
        <div className="compilation-progress">
          <div className="progress-header">
            <h4>Compiling Video...</h4>
            {onCancel && (
              <button
                className="cancel-button"
                onClick={() => onCancel(currentJob.id)}
              >
                Cancel
              </button>
            )}
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${currentJob.progress}%` }}
            />
          </div>
          <p className="progress-text">{currentJob.progress.toFixed(0)}% complete</p>
        </div>
      )}

      {currentJob && currentJob.status === 'completed' && (
        <div className="compilation-result success">
          <div className="result-icon">✓</div>
          <div className="result-info">
            <h4>Compilation Successful!</h4>
            <div className="result-metadata">
              <span>Duration: {formatDuration(currentJob.output_duration)}</span>
              <span>Size: {formatFileSize(currentJob.output_file_size)}</span>
              <span>Segments: {currentJob.segment_ids.length}</span>
            </div>
          </div>
          {onDownload && (
            <button
              className="download-button"
              onClick={() => onDownload(currentJob.id)}
            >
              Download Video
            </button>
          )}
        </div>
      )}

      {currentJob && currentJob.status === 'failed' && (
        <div className="compilation-result error">
          <div className="result-icon">✗</div>
          <div className="result-info">
            <h4>Compilation Failed</h4>
            <p className="error-message">{currentJob.error_message}</p>
          </div>
        </div>
      )}

      <div className="segment-selection">
        <div className="selection-header">
          <h4>Select Segments ({selectedSegments.length}/{approvedSegments.length})</h4>
          <div className="selection-actions">
            <button className="text-button" onClick={selectAllSegments}>
              Select All
            </button>
            <button className="text-button" onClick={deselectAllSegments}>
              Deselect All
            </button>
          </div>
        </div>

        {approvedSegments.length === 0 ? (
          <div className="empty-segments">
            <p>No approved segments available for compilation</p>
            <p className="hint">Approve some segments first</p>
          </div>
        ) : (
          <div className="segment-list">
            {approvedSegments.map(segment => (
              <label key={segment.id} className="segment-checkbox">
                <input
                  type="checkbox"
                  checked={selectedSegments.includes(segment.id)}
                  onChange={() => toggleSegmentSelection(segment.id)}
                />
                <span className="segment-label">
                  <span className="segment-number">#{segment.segment_number}</span>
                  <span className="segment-title">{segment.title}</span>
                  {segment.duration && (
                    <span className="segment-duration">
                      {Math.floor(segment.duration)}s
                    </span>
                  )}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="compilation-settings">
        <h4>Compilation Settings</h4>

        <div className="setting-group">
          <label>Transition Style</label>
          <div className="transition-options">
            <button
              className={`transition-button ${transitionStyle === 'cut' ? 'active' : ''}`}
              onClick={() => setTransitionStyle('cut')}
            >
              <span className="transition-icon">✂</span>
              <span>Cut</span>
            </button>
            <button
              className={`transition-button ${transitionStyle === 'fade' ? 'active' : ''}`}
              onClick={() => setTransitionStyle('fade')}
            >
              <span className="transition-icon">◐</span>
              <span>Fade</span>
            </button>
            <button
              className={`transition-button ${transitionStyle === 'dissolve' ? 'active' : ''}`}
              onClick={() => setTransitionStyle('dissolve')}
            >
              <span className="transition-icon">◎</span>
              <span>Dissolve</span>
            </button>
          </div>
        </div>

        <button
          className="advanced-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? '▼' : '▶'} Advanced Audio Settings
        </button>

        {showAdvanced && (
          <div className="advanced-settings">
            <div className="setting-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={volumeNormalization}
                  onChange={(e) => setVolumeNormalization(e.target.checked)}
                />
                <span>Enable Volume Normalization</span>
              </label>
            </div>

            {volumeNormalization && (
              <div className="setting-group">
                <label>Target Volume: {(targetVolume * 100).toFixed(0)}%</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={targetVolume}
                  onChange={(e) => setTargetVolume(parseFloat(e.target.value))}
                  className="volume-slider"
                />
              </div>
            )}

            <div className="setting-group">
              <label>Background Music Volume: {(musicVolume * 100).toFixed(0)}%</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={musicVolume}
                onChange={(e) => setMusicVolume(parseFloat(e.target.value))}
                className="volume-slider"
              />
            </div>
          </div>
        )}
      </div>

      <div className="compilation-summary">
        <div className="summary-item">
          <span className="summary-label">Selected Segments:</span>
          <span className="summary-value">{selectedSegments.length}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Estimated Duration:</span>
          <span className="summary-value">{getTotalDuration()}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Transition:</span>
          <span className="summary-value">{transitionStyle}</span>
        </div>
      </div>

      <button
        className="compile-button"
        onClick={handleCompile}
        disabled={
          selectedSegments.length === 0 ||
          (currentJob && currentJob.status === 'processing')
        }
      >
        {currentJob && currentJob.status === 'processing'
          ? 'Compiling...'
          : 'Compile Video'}
      </button>

      {previousJobs.length > 0 && (
        <div className="compilation-history">
          <button
            className="history-toggle"
            onClick={() => setShowHistory(!showHistory)}
          >
            {showHistory ? '▼' : '▶'} Compilation History ({previousJobs.length})
          </button>

          {showHistory && (
            <div className="history-list">
              {previousJobs.map(job => (
                <div key={job.id} className="history-item">
                  <div className="history-info">
                    <span
                      className="history-status"
                      style={{ color: getStatusColor(job.status) }}
                    >
                      ● {job.status}
                    </span>
                    <span className="history-date">
                      {new Date(job.created_at).toLocaleString()}
                    </span>
                    <span className="history-segments">
                      {job.segment_ids.length} segments
                    </span>
                  </div>
                  {job.status === 'completed' && onDownload && (
                    <button
                      className="history-download"
                      onClick={() => onDownload(job.id)}
                    >
                      Download
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CompilationPanel;