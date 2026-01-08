/**
 * Agent Monitor Dashboard
 * Real-time monitoring of all registered agents
 * 
 * Part of Week 3: Frontend WebSocket Integration - Phase 2
 */

import React, { useState } from 'react';
import { useCoordinatorWebSocket } from '../hooks/useWebSocket';
import AgentStatusCard from '../components/AgentStatusCard';
import './AgentMonitor.css';

interface AgentInfo {
  name: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  capabilities: string[];
  currentTask?: string;
  metrics?: {
    tasks_completed?: number;
    tasks_failed?: number;
    avg_response_time?: number;
    uptime?: number;
  };
  lastUpdate: string;
}

interface CoordinatorMetrics {
  total_agents: number;
  active_workflows: number;
  completed_workflows: number;
  failed_workflows: number;
  agents: Record<string, AgentInfo>;
}

export const AgentMonitor: React.FC = () => {
  const [agents, setAgents] = useState<Record<string, AgentInfo>>({});
  const [metrics, setMetrics] = useState<CoordinatorMetrics | null>(null);
  const [filter, setFilter] = useState<'all' | 'idle' | 'busy' | 'error' | 'offline'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const { isConnected } = useCoordinatorWebSocket((data) => {
    if (data.type === 'coordinator_metrics') {
      setMetrics(data.metrics);
      if (data.metrics.agents) {
        setAgents(data.metrics.agents);
      }
    } else if (data.type === 'agent_status') {
      // Update individual agent status
      setAgents(prev => ({
        ...prev,
        [data.agent_name]: {
          ...prev[data.agent_name],
          ...data.status,
          lastUpdate: new Date().toISOString(),
        }
      }));
    }
  });

  const filteredAgents = Object.entries(agents).filter(([name, agent]) => {
    const matchesFilter = filter === 'all' || agent.status === filter;
    const matchesSearch = name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      agent.capabilities.some(cap =>
        cap.toLowerCase().includes(searchTerm.toLowerCase())
      );
    return matchesFilter && matchesSearch;
  });

  const getStatusCount = (status: 'idle' | 'busy' | 'error' | 'offline') => {
    return Object.values(agents).filter(agent => agent.status === status).length;
  };

  return (
    <div className="agent-monitor">
      <div className="agent-monitor-header">
        <h1>Agent Monitor Dashboard</h1>
        <div className="agent-monitor-connection-status">
          {isConnected ? (
            <span className="connection-status-connected">● Connected</span>
          ) : (
            <span className="connection-status-disconnected">○ Disconnected</span>
          )}
        </div>
      </div>


      {metrics && (
        <div className="agent-monitor-metrics">
          <div className="metric-card glass-card">
            <div className="metric-value">{metrics.total_agents}</div>
            <div className="metric-label">Total Agents</div>
          </div>
          <div className="metric-card glass-card">
            <div className="metric-value">{metrics.active_workflows}</div>
            <div className="metric-label">Active Workflows</div>
          </div>
          <div className="metric-card glass-card">
            <div className="metric-value">{metrics.completed_workflows}</div>
            <div className="metric-label">Completed</div>
          </div>
          <div className="metric-card glass-card">
            <div className="metric-value">{metrics.failed_workflows}</div>
            <div className="metric-label">Failed</div>
          </div>
        </div>
      )}

      <div className="agent-monitor-controls">
        <div className="agent-monitor-filters">
          <button
            className={`filter-button glass-button ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({Object.keys(agents).length})
          </button>
          <button
            className={`filter-button glass-button ${filter === 'idle' ? 'active' : ''}`}
            onClick={() => setFilter('idle')}
          >
            Idle ({getStatusCount('idle')})
          </button>
          <button
            className={`filter-button glass-button ${filter === 'busy' ? 'active' : ''}`}
            onClick={() => setFilter('busy')}
          >
            Busy ({getStatusCount('busy')})
          </button>
          <button
            className={`filter-button glass-button ${filter === 'error' ? 'active' : ''}`}
            onClick={() => setFilter('error')}
          >
            Error ({getStatusCount('error')})
          </button>
          <button
            className={`filter-button glass-button ${filter === 'offline' ? 'active' : ''}`}
            onClick={() => setFilter('offline')}
          >
            Offline ({getStatusCount('offline')})
          </button>
        </div>

        <div className="agent-monitor-search">
          <input
            type="text"
            placeholder="Search agents or capabilities..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input glass-input"
          />
        </div>
      </div>

      <div className="agent-monitor-grid">
        {filteredAgents.length === 0 ? (
          <div className="agent-monitor-empty">
            {Object.keys(agents).length === 0 ? (
              <p>No agents registered yet. Waiting for agents to connect...</p>
            ) : (
              <p>No agents match the current filter and search criteria.</p>
            )}
          </div>
        ) : (
          filteredAgents.map(([name, agent]) => (
            <AgentStatusCard
              key={name}
              agentName={name}
              status={agent.status}
              capabilities={agent.capabilities}
              currentTask={agent.currentTask}
              metrics={agent.metrics}
              lastUpdate={agent.lastUpdate}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default AgentMonitor;