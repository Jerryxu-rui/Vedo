/**
 * Agent Status Card Component
 * Displays real-time agent status and metrics
 * 
 * Part of Week 3: Frontend WebSocket Integration - Phase 2
 */

import React from 'react';
import './AgentStatusCard.css';

export interface AgentStatusCardProps {
  agentName: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  capabilities?: string[];
  currentTask?: string;
  metrics?: {
    tasks_completed?: number;
    tasks_failed?: number;
    avg_response_time?: number;
    uptime?: number;
  };
  lastUpdate?: string;
}

export const AgentStatusCard: React.FC<AgentStatusCardProps> = ({
  agentName,
  status,
  capabilities = [],
  currentTask,
  metrics,
  lastUpdate,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'idle':
        return '#10b981'; // green
      case 'busy':
        return '#f59e0b'; // amber
      case 'error':
        return '#ef4444'; // red
      case 'offline':
        return '#6b7280'; // gray
      default:
        return '#9ca3af';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'idle':
        return '●';
      case 'busy':
        return '◐';
      case 'error':
        return '✗';
      case 'offline':
        return '○';
      default:
        return '?';
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatResponseTime = (ms?: number) => {
    if (!ms) return 'N/A';
    return `${ms.toFixed(0)}ms`;
  };

  return (
    <div className="agent-status-card">
      <div className="agent-status-header">
        <div className="agent-status-title">
          <span 
            className="agent-status-indicator"
            style={{ color: getStatusColor() }}
          >
            {getStatusIcon()}
          </span>
          <h3 className="agent-status-name">{agentName}</h3>
        </div>
        <span 
          className="agent-status-badge"
          style={{ 
            backgroundColor: getStatusColor(),
            color: 'white'
          }}
        >
          {status.toUpperCase()}
        </span>
      </div>

      {capabilities.length > 0 && (
        <div className="agent-status-capabilities">
          <strong>Capabilities:</strong>
          <div className="agent-status-capability-tags">
            {capabilities.map((cap, idx) => (
              <span key={idx} className="agent-status-capability-tag">
                {cap}
              </span>
            ))}
          </div>
        </div>
      )}

      {currentTask && (
        <div className="agent-status-current-task">
          <strong>Current Task:</strong>
          <p>{currentTask}</p>
        </div>
      )}

      {metrics && (
        <div className="agent-status-metrics">
          <div className="agent-status-metric">
            <span className="agent-status-metric-label">Completed:</span>
            <span className="agent-status-metric-value">
              {metrics.tasks_completed ?? 0}
            </span>
          </div>
          <div className="agent-status-metric">
            <span className="agent-status-metric-label">Failed:</span>
            <span className="agent-status-metric-value">
              {metrics.tasks_failed ?? 0}
            </span>
          </div>
          <div className="agent-status-metric">
            <span className="agent-status-metric-label">Avg Response:</span>
            <span className="agent-status-metric-value">
              {formatResponseTime(metrics.avg_response_time)}
            </span>
          </div>
          <div className="agent-status-metric">
            <span className="agent-status-metric-label">Uptime:</span>
            <span className="agent-status-metric-value">
              {formatUptime(metrics.uptime)}
            </span>
          </div>
        </div>
      )}

      {lastUpdate && (
        <div className="agent-status-footer">
          <span className="agent-status-last-update">
            Last update: {new Date(lastUpdate).toLocaleTimeString()}
          </span>
        </div>
      )}
    </div>
  );
};

export default AgentStatusCard;