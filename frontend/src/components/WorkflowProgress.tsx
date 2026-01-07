/**
 * Workflow Progress Component
 * Displays real-time workflow execution progress
 * 
 * Part of Week 3: Frontend WebSocket Integration - Phase 2
 */

import React from 'react';
import './WorkflowProgress.css';

export interface WorkflowProgressProps {
  workflowId: string;
  state: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0.0 to 1.0
  stage?: string;
  message?: string;
  details?: Record<string, any>;
  onCancel?: () => void;
}

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  workflowId,
  state,
  progress,
  stage,
  message,
  details,
  onCancel,
}) => {
  const percentage = Math.round(progress * 100);

  const getStateColor = () => {
    switch (state) {
      case 'completed':
        return '#10b981'; // green
      case 'failed':
        return '#ef4444'; // red
      case 'cancelled':
        return '#6b7280'; // gray
      case 'running':
        return '#3b82f6'; // blue
      default:
        return '#9ca3af'; // light gray
    }
  };

  const getStateIcon = () => {
    switch (state) {
      case 'completed':
        return '✓';
      case 'failed':
        return '✗';
      case 'cancelled':
        return '⊘';
      case 'running':
        return '⟳';
      default:
        return '○';
    }
  };

  return (
    <div className="workflow-progress">
      <div className="workflow-progress-header">
        <div className="workflow-progress-title">
          <span 
            className="workflow-progress-icon"
            style={{ color: getStateColor() }}
          >
            {getStateIcon()}
          </span>
          <span className="workflow-progress-state">{state.toUpperCase()}</span>
          {stage && <span className="workflow-progress-stage">• {stage}</span>}
        </div>
        
        {state === 'running' && onCancel && (
          <button 
            className="workflow-progress-cancel"
            onClick={onCancel}
            title="Cancel workflow"
          >
            Cancel
          </button>
        )}
      </div>

      <div className="workflow-progress-bar-container">
        <div 
          className="workflow-progress-bar"
          style={{ 
            width: `${percentage}%`,
            backgroundColor: getStateColor()
          }}
        />
      </div>

      <div className="workflow-progress-info">
        <span className="workflow-progress-percentage">{percentage}%</span>
        {message && <span className="workflow-progress-message">{message}</span>}
      </div>

      {details && Object.keys(details).length > 0 && (
        <div className="workflow-progress-details">
          {details.tasks && Array.isArray(details.tasks) && (
            <div className="workflow-progress-tasks">
              <strong>Tasks:</strong> {details.tasks.join(', ')}
            </div>
          )}
          {details.error && (
            <div className="workflow-progress-error">
              <strong>Error:</strong> {details.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WorkflowProgress;