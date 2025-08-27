import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { Terminal } from 'xterm';

// Types
export interface TerminalState {
  // Connection state
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  connectionError?: string;
  
  // Terminal instances
  terminals: Map<string, Terminal>;
  activeTerminalId: string;
  
  // Session management
  sessions: TerminalSession[];
  activeSessions: Set<string>;
  
  // Command history
  history: string[];
  historyIndex: number;
  maxHistorySize: number;
  
  // Output buffer
  outputBuffer: TerminalOutput[];
  maxBufferSize: number;
  
  // Performance metrics
  metrics: PerformanceMetrics;
  
  // Actions
  setConnected: (connected: boolean) => void;
  setConnectionStatus: (status: TerminalState['connectionStatus']) => void;
  setConnectionError: (error: string | undefined) => void;
  setTerminalInstance: (terminal: Terminal, sessionId?: string) => void;
  removeTerminalInstance: (sessionId: string) => void;
  setActiveTerminal: (sessionId: string) => void;
  addSession: (session: TerminalSession) => void;
  removeSession: (sessionId: string) => void;
  updateSession: (sessionId: string, updates: Partial<TerminalSession>) => void;
  addToHistory: (command: string) => void;
  clearHistory: () => void;
  navigateHistory: (direction: 'up' | 'down') => string | undefined;
  addOutput: (output: TerminalOutput) => void;
  clearOutput: () => void;
  updateMetrics: (metrics: Partial<PerformanceMetrics>) => void;
  resetState: () => void;
}

export interface TerminalSession {
  id: string;
  name: string;
  created: Date;
  lastActive: Date;
  status: 'active' | 'inactive' | 'closed';
  pid?: number;
  cwd: string;
  environment: Record<string, string>;
  size: { cols: number; rows: number };
  
  // Collaboration
  isShared: boolean;
  shareId?: string;
  participants: Participant[];
  
  // Recording
  isRecording: boolean;
  recordingStartTime?: Date;
  recordingData?: RecordingData;
}

export interface TerminalOutput {
  id: string;
  sessionId: string;
  type: 'stdout' | 'stderr' | 'stdin' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    command?: string;
    exitCode?: number;
    duration?: number;
  };
}

export interface Participant {
  id: string;
  name: string;
  avatar?: string;
  cursor?: { x: number; y: number };
  lastSeen: Date;
  permissions: ParticipantPermissions;
}

export interface ParticipantPermissions {
  canWrite: boolean;
  canExecute: boolean;
  canUpload: boolean;
  canShare: boolean;
}

export interface RecordingData {
  events: RecordingEvent[];
  metadata: {
    startTime: Date;
    endTime?: Date;
    terminalSize: { cols: number; rows: number };
    commands: string[];
  };
}

export interface RecordingEvent {
  timestamp: number;
  type: 'input' | 'output' | 'resize' | 'cursor';
  data: any;
}

export interface PerformanceMetrics {
  connectionLatency: number;
  renderingFps: number;
  memoryUsage: number;
  messageQueueSize: number;
  commandExecutionTime: number;
  lastUpdate: Date;
}

// Initial state
const initialState = {
  isConnected: false,
  connectionStatus: 'disconnected' as const,
  connectionError: undefined,
  terminals: new Map<string, Terminal>(),
  activeTerminalId: 'default',
  sessions: [] as TerminalSession[],
  activeSessions: new Set<string>(),
  history: [] as string[],
  historyIndex: -1,
  maxHistorySize: 1000,
  outputBuffer: [] as TerminalOutput[],
  maxBufferSize: 10000,
  metrics: {
    connectionLatency: 0,
    renderingFps: 0,
    memoryUsage: 0,
    messageQueueSize: 0,
    commandExecutionTime: 0,
    lastUpdate: new Date(),
  } as PerformanceMetrics,
};

// Store implementation
export const useTerminalStore = create<TerminalState>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      // Connection management
      setConnected: (connected: boolean) => {
        set({ isConnected: connected }, false, 'setConnected');
        
        if (connected) {
          set({ connectionStatus: 'connected', connectionError: undefined });
        }
      },

      setConnectionStatus: (status: TerminalState['connectionStatus']) => {
        set({ connectionStatus: status }, false, 'setConnectionStatus');
        
        if (status === 'connected') {
          set({ isConnected: true, connectionError: undefined });
        } else if (status === 'disconnected' || status === 'error') {
          set({ isConnected: false });
        }
      },

      setConnectionError: (error: string | undefined) => {
        set({ connectionError: error }, false, 'setConnectionError');
        
        if (error) {
          set({ connectionStatus: 'error', isConnected: false });
        }
      },

      // Terminal instance management
      setTerminalInstance: (terminal: Terminal, sessionId: string = 'default') => {
        const { terminals } = get();
        const newTerminals = new Map(terminals);
        newTerminals.set(sessionId, terminal);
        
        set({ 
          terminals: newTerminals,
          activeTerminalId: sessionId 
        }, false, 'setTerminalInstance');
      },

      removeTerminalInstance: (sessionId: string) => {
        const { terminals, activeTerminalId } = get();
        const newTerminals = new Map(terminals);
        
        // Dispose terminal if it exists
        const terminal = newTerminals.get(sessionId);
        if (terminal) {
          terminal.dispose();
          newTerminals.delete(sessionId);
        }
        
        // Update active terminal if needed
        const newActiveId = activeTerminalId === sessionId 
          ? (newTerminals.keys().next().value || 'default')
          : activeTerminalId;
        
        set({ 
          terminals: newTerminals,
          activeTerminalId: newActiveId 
        }, false, 'removeTerminalInstance');
      },

      setActiveTerminal: (sessionId: string) => {
        set({ activeTerminalId: sessionId }, false, 'setActiveTerminal');
      },

      // Session management
      addSession: (session: TerminalSession) => {
        const { sessions, activeSessions } = get();
        const newSessions = [...sessions, session];
        const newActiveSessions = new Set(activeSessions);
        newActiveSessions.add(session.id);
        
        set({ 
          sessions: newSessions,
          activeSessions: newActiveSessions 
        }, false, 'addSession');
      },

      removeSession: (sessionId: string) => {
        const { sessions, activeSessions } = get();
        const newSessions = sessions.filter(s => s.id !== sessionId);
        const newActiveSessions = new Set(activeSessions);
        newActiveSessions.delete(sessionId);
        
        set({ 
          sessions: newSessions,
          activeSessions: newActiveSessions 
        }, false, 'removeSession');
      },

      updateSession: (sessionId: string, updates: Partial<TerminalSession>) => {
        const { sessions } = get();
        const newSessions = sessions.map(session => 
          session.id === sessionId 
            ? { ...session, ...updates, lastActive: new Date() }
            : session
        );
        
        set({ sessions: newSessions }, false, 'updateSession');
      },

      // Command history
      addToHistory: (command: string) => {
        if (!command.trim()) return;
        
        const { history, maxHistorySize } = get();
        const newHistory = [command, ...history.filter(h => h !== command)]
          .slice(0, maxHistorySize);
        
        set({ 
          history: newHistory,
          historyIndex: -1 
        }, false, 'addToHistory');
      },

      clearHistory: () => {
        set({ 
          history: [],
          historyIndex: -1 
        }, false, 'clearHistory');
      },

      navigateHistory: (direction: 'up' | 'down') => {
        const { history, historyIndex } = get();
        
        if (history.length === 0) return undefined;
        
        let newIndex: number;
        if (direction === 'up') {
          newIndex = Math.min(historyIndex + 1, history.length - 1);
        } else {
          newIndex = Math.max(historyIndex - 1, -1);
        }
        
        set({ historyIndex: newIndex }, false, 'navigateHistory');
        
        return newIndex >= 0 ? history[newIndex] : undefined;
      },

      // Output buffer management
      addOutput: (output: TerminalOutput) => {
        const { outputBuffer, maxBufferSize } = get();
        const newBuffer = [output, ...outputBuffer].slice(0, maxBufferSize);
        
        set({ outputBuffer: newBuffer }, false, 'addOutput');
      },

      clearOutput: () => {
        set({ outputBuffer: [] }, false, 'clearOutput');
      },

      // Performance metrics
      updateMetrics: (metrics: Partial<PerformanceMetrics>) => {
        const { metrics: currentMetrics } = get();
        const newMetrics = {
          ...currentMetrics,
          ...metrics,
          lastUpdate: new Date(),
        };
        
        set({ metrics: newMetrics }, false, 'updateMetrics');
      },

      // Reset state
      resetState: () => {
        const { terminals } = get();
        
        // Dispose all terminal instances
        terminals.forEach(terminal => terminal.dispose());
        
        set(initialState, false, 'resetState');
      },
    })),
    {
      name: 'terminal-store',
      partialize: (state) => ({
        // Only persist non-transient state
        history: state.history,
        maxHistorySize: state.maxHistorySize,
        maxBufferSize: state.maxBufferSize,
        sessions: state.sessions.filter(s => s.status !== 'closed'),
      }),
    }
  )
);

// Selector hooks for optimized subscriptions
export const useTerminalConnection = () => 
  useTerminalStore(state => ({
    isConnected: state.isConnected,
    connectionStatus: state.connectionStatus,
    connectionError: state.connectionError,
  }));

export const useActiveTerminal = () =>
  useTerminalStore(state => ({
    terminal: state.terminals.get(state.activeTerminalId),
    sessionId: state.activeTerminalId,
  }));

export const useTerminalHistory = () =>
  useTerminalStore(state => ({
    history: state.history,
    historyIndex: state.historyIndex,
    addToHistory: state.addToHistory,
    navigateHistory: state.navigateHistory,
    clearHistory: state.clearHistory,
  }));

export const useTerminalSessions = () =>
  useTerminalStore(state => ({
    sessions: state.sessions,
    activeSessions: state.activeSessions,
    addSession: state.addSession,
    removeSession: state.removeSession,
    updateSession: state.updateSession,
  }));

export const useTerminalMetrics = () =>
  useTerminalStore(state => ({
    metrics: state.metrics,
    updateMetrics: state.updateMetrics,
  }));