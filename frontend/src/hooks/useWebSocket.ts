/**
 * useWebSocket Hook
 * React hook for WebSocket connection management with auto-reconnection
 * 
 * Part of Week 3: Frontend WebSocket Integration - Phase 2
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  heartbeatInterval?: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  send: (message: any) => void;
  subscribe: (type: string, handler: (message: WebSocketMessage) => void) => void;
  unsubscribe: (type: string) => void;
  reconnect: () => void;
  disconnect: () => void;
  connectionAttempts: number;
}

/**
 * Custom hook for WebSocket connection management
 * 
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Message type-based subscription system
 * - Heartbeat/ping-pong for connection health
 * - Message queue for offline mode
 * - Type-safe message handling
 * 
 * @param options WebSocket configuration options
 * @returns WebSocket connection state and methods
 */
export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    onMessage,
    onError,
    onOpen,
    onClose,
    reconnect = true,
    reconnectInterval = 1000,
    reconnectAttempts = 5,
    heartbeatInterval = 30000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionAttempts, setConnectionAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const messageQueueRef = useRef<any[]>([]);
  const subscribersRef = useRef<Map<string, Set<(message: WebSocketMessage) => void>>>(
    new Map()
  );

  /**
   * Calculate reconnection delay with exponential backoff
   */
  const getReconnectDelay = useCallback((attempt: number): number => {
    return Math.min(reconnectInterval * Math.pow(2, attempt), 30000);
  }, [reconnectInterval]);

  /**
   * Send heartbeat ping
   */
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  /**
   * Start heartbeat interval
   */
  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    heartbeatIntervalRef.current = setInterval(sendHeartbeat, heartbeatInterval);
  }, [sendHeartbeat, heartbeatInterval]);

  /**
   * Stop heartbeat interval
   */
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  /**
   * Process message queue
   */
  const processMessageQueue = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && messageQueueRef.current.length > 0) {
      console.log(`[WebSocket] Processing ${messageQueueRef.current.length} queued messages`);
      
      while (messageQueueRef.current.length > 0) {
        const message = messageQueueRef.current.shift();
        wsRef.current.send(JSON.stringify(message));
      }
    }
  }, []);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    try {
      console.log(`[WebSocket] Connecting to ${url}...`);
      
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        setConnectionAttempts(0);
        
        // Start heartbeat
        startHeartbeat();
        
        // Process queued messages
        processMessageQueue();
        
        // Call user callback
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Handle pong response
          if (message.type === 'pong') {
            return;
          }
          
          // Call global message handler
          onMessage?.(message);
          
          // Call type-specific subscribers
          const subscribers = subscribersRef.current.get(message.type);
          if (subscribers) {
            subscribers.forEach(handler => handler(message));
          }
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        onError?.(error);
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        setIsConnected(false);
        stopHeartbeat();
        
        // Call user callback
        onClose?.();
        
        // Attempt reconnection
        if (reconnect && connectionAttempts < reconnectAttempts) {
          const delay = getReconnectDelay(connectionAttempts);
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${connectionAttempts + 1}/${reconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            setConnectionAttempts(prev => prev + 1);
            connect();
          }, delay);
        } else if (connectionAttempts >= reconnectAttempts) {
          console.error('[WebSocket] Max reconnection attempts reached');
        }
      };
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      onError?.(error as Event);
    }
  }, [
    url,
    onMessage,
    onError,
    onOpen,
    onClose,
    reconnect,
    reconnectAttempts,
    connectionAttempts,
    getReconnectDelay,
    startHeartbeat,
    stopHeartbeat,
    processMessageQueue,
  ]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    console.log('[WebSocket] Disconnecting...');
    
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Stop heartbeat
    stopHeartbeat();
    
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, [stopHeartbeat]);

  /**
   * Send message to WebSocket
   */
  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      // Queue message for later
      console.log('[WebSocket] Connection not open, queueing message');
      messageQueueRef.current.push(message);
    }
  }, []);

  /**
   * Subscribe to specific message type
   */
  const subscribe = useCallback((type: string, handler: (message: WebSocketMessage) => void) => {
    if (!subscribersRef.current.has(type)) {
      subscribersRef.current.set(type, new Set());
    }
    subscribersRef.current.get(type)!.add(handler);
    
    console.log(`[WebSocket] Subscribed to message type: ${type}`);
  }, []);

  /**
   * Unsubscribe from specific message type
   */
  const unsubscribe = useCallback((type: string) => {
    subscribersRef.current.delete(type);
    console.log(`[WebSocket] Unsubscribed from message type: ${type}`);
  }, []);

  /**
   * Manual reconnection
   */
  const manualReconnect = useCallback(() => {
    console.log('[WebSocket] Manual reconnection triggered');
    disconnect();
    setConnectionAttempts(0);
    connect();
  }, [disconnect, connect]);

  // Connect on mount
  useEffect(() => {
    connect();
    
    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [url]); // Only reconnect if URL changes

  return {
    isConnected,
    send,
    subscribe,
    unsubscribe,
    reconnect: manualReconnect,
    disconnect,
    connectionAttempts,
  };
}

/**
 * Hook for workflow progress WebSocket
 */
export function useWorkflowWebSocket(workflowId: string, onProgress?: (data: any) => void) {
  const url = `ws://localhost:3001/ws/workflow/${workflowId}`;
  
  return useWebSocket({
    url,
    onMessage: (message) => {
      if (message.type === 'progress' && onProgress) {
        onProgress(message);
      }
    },
    reconnect: true,
    reconnectAttempts: 5,
  });
}

/**
 * Hook for agent status WebSocket
 */
export function useAgentWebSocket(agentName: string, onStatus?: (data: any) => void) {
  const url = `ws://localhost:3001/ws/agent/${agentName}`;
  
  return useWebSocket({
    url,
    onMessage: (message) => {
      if (message.type === 'agent_status' && onStatus) {
        onStatus(message);
      }
    },
    reconnect: true,
    reconnectAttempts: 5,
  });
}

/**
 * Hook for coordinator metrics WebSocket
 */
export function useCoordinatorWebSocket(onMetrics?: (data: any) => void) {
  const url = `ws://localhost:3001/ws/coordinator`;
  
  return useWebSocket({
    url,
    onMessage: (message) => {
      if (message.type === 'coordinator_metrics' && onMetrics) {
        onMetrics(message);
      }
    },
    reconnect: true,
    reconnectAttempts: 5,
  });
}