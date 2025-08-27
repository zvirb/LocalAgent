import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';

// Types
export interface CollaborationState {
  // Session state
  isCollaborating: boolean;
  sessionId?: string;
  shareId?: string;
  isHost: boolean;
  
  // Participants
  participants: Participant[];
  currentUser?: CurrentUser;
  maxParticipants: number;
  
  // Permissions
  sessionPermissions: SessionPermissions;
  userPermissions: UserPermissions;
  
  // Real-time state
  cursors: Map<string, CursorPosition>;
  selections: Map<string, SelectionRange>;
  activeTyping: Set<string>;
  
  // Communication
  messages: ChatMessage[];
  notifications: Notification[];
  
  // Operational Transform
  operationQueue: Operation[];
  lastOperationId: number;
  pendingOperations: Set<number>;
  
  // Recording
  isRecording: boolean;
  recordingPermissions: RecordingPermissions;
  
  // Actions
  startCollaboration: (config: CollaborationConfig) => Promise<boolean>;
  stopCollaboration: () => void;
  joinSession: (shareId: string, userData: UserData) => Promise<boolean>;
  leaveSession: () => void;
  addParticipant: (participant: Participant) => void;
  removeParticipant: (participantId: string) => void;
  updateParticipant: (participantId: string, updates: Partial<Participant>) => void;
  updateCursor: (userId: string, position: CursorPosition) => void;
  updateSelection: (userId: string, range: SelectionRange | null) => void;
  setTyping: (userId: string, isTyping: boolean) => void;
  sendMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  dismissNotification: (notificationId: string) => void;
  submitOperation: (operation: Omit<Operation, 'id' | 'timestamp' | 'author'>) => void;
  ackOperation: (operationId: number) => void;
  transformOperation: (operation: Operation, against: Operation) => Operation;
  updatePermissions: (permissions: Partial<SessionPermissions>) => void;
  kickParticipant: (participantId: string) => void;
  transferHost: (participantId: string) => void;
  startRecording: () => void;
  stopRecording: () => void;
  resetCollaboration: () => void;
}

export interface Participant {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  joinedAt: Date;
  lastSeen: Date;
  status: 'online' | 'away' | 'offline';
  permissions: ParticipantPermissions;
  metadata: {
    userAgent?: string;
    location?: string;
    timezone?: string;
  };
}

export interface CurrentUser extends Omit<Participant, 'permissions'> {
  isAuthenticated: boolean;
  token?: string;
}

export interface CursorPosition {
  line: number;
  column: number;
  isVisible: boolean;
}

export interface SelectionRange {
  start: { line: number; column: number };
  end: { line: number; column: number };
}

export interface ParticipantPermissions {
  canWrite: boolean;
  canExecute: boolean;
  canUpload: boolean;
  canChat: boolean;
  canInvite: boolean;
  canViewHistory: boolean;
  canDownload: boolean;
}

export interface SessionPermissions {
  allowAnonymous: boolean;
  requireApproval: boolean;
  canChangePermissions: boolean;
  maxIdleTime: number; // minutes
  sessionTimeout: number; // minutes
  allowRecording: boolean;
  allowFileOperations: boolean;
}

export interface UserPermissions extends ParticipantPermissions {
  canManageSession: boolean;
  canKickUsers: boolean;
  canTransferHost: boolean;
  canEndSession: boolean;
}

export interface ChatMessage {
  id: string;
  type: 'message' | 'system' | 'command';
  content: string;
  author: string;
  authorName: string;
  timestamp: Date;
  metadata?: {
    command?: string;
    exitCode?: number;
    isPrivate?: boolean;
  };
}

export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  duration?: number;
  actions?: NotificationAction[];
  persistent?: boolean;
}

export interface NotificationAction {
  label: string;
  action: string;
  type: 'primary' | 'secondary' | 'danger';
}

export interface Operation {
  id: number;
  type: 'insert' | 'delete' | 'retain' | 'format';
  position: { line: number; column: number };
  content?: string;
  length?: number;
  attributes?: Record<string, any>;
  timestamp: Date;
  author: string;
}

export interface CollaborationConfig {
  sessionName?: string;
  isPrivate: boolean;
  permissions: SessionPermissions;
  maxParticipants?: number;
  recordingEnabled?: boolean;
}

export interface UserData {
  name: string;
  avatar?: string;
  metadata?: Record<string, any>;
}

export interface RecordingPermissions {
  canStart: boolean;
  canStop: boolean;
  canDownload: boolean;
  requireConsent: boolean;
}

// Color palette for participants
const participantColors = [
  '#58a6ff', // Blue
  '#3fb950', // Green
  '#d29922', // Yellow
  '#bc8cff', // Purple
  '#f85149', // Red
  '#39c5cf', // Cyan
  '#ff7b72', // Light Red
  '#79c0ff', // Light Blue
  '#56d364', // Light Green
  '#d2a8ff', // Light Purple
];

// Initial state
const initialState = {
  isCollaborating: false,
  sessionId: undefined,
  shareId: undefined,
  isHost: false,
  participants: [] as Participant[],
  currentUser: undefined,
  maxParticipants: 10,
  sessionPermissions: {
    allowAnonymous: true,
    requireApproval: false,
    canChangePermissions: false,
    maxIdleTime: 30,
    sessionTimeout: 480, // 8 hours
    allowRecording: true,
    allowFileOperations: true,
  } as SessionPermissions,
  userPermissions: {
    canWrite: true,
    canExecute: true,
    canUpload: true,
    canChat: true,
    canInvite: false,
    canViewHistory: true,
    canDownload: true,
    canManageSession: false,
    canKickUsers: false,
    canTransferHost: false,
    canEndSession: false,
  } as UserPermissions,
  cursors: new Map<string, CursorPosition>(),
  selections: new Map<string, SelectionRange>(),
  activeTyping: new Set<string>(),
  messages: [] as ChatMessage[],
  notifications: [] as Notification[],
  operationQueue: [] as Operation[],
  lastOperationId: 0,
  pendingOperations: new Set<number>(),
  isRecording: false,
  recordingPermissions: {
    canStart: false,
    canStop: false,
    canDownload: false,
    requireConsent: true,
  } as RecordingPermissions,
};

// Utility functions
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function generateShareId(): string {
  return Math.random().toString(36).substr(2, 12).toUpperCase();
}

function getParticipantColor(index: number): string {
  return participantColors[index % participantColors.length];
}

// Operational Transform functions
function transformOperation(op: Operation, against: Operation): Operation {
  // Simple operational transform implementation
  // In a production system, you'd want a more sophisticated OT implementation
  
  if (op.type === 'insert' && against.type === 'insert') {
    if (against.position.line < op.position.line || 
        (against.position.line === op.position.line && against.position.column <= op.position.column)) {
      return {
        ...op,
        position: {
          line: op.position.line + (against.content?.includes('\n') ? against.content.split('\n').length - 1 : 0),
          column: against.position.line === op.position.line ? 
            op.position.column + (against.content?.length || 0) : op.position.column,
        },
      };
    }
  }
  
  if (op.type === 'delete' && against.type === 'insert') {
    if (against.position.line < op.position.line || 
        (against.position.line === op.position.line && against.position.column <= op.position.column)) {
      return {
        ...op,
        position: {
          line: op.position.line + (against.content?.includes('\n') ? against.content.split('\n').length - 1 : 0),
          column: against.position.line === op.position.line ? 
            op.position.column + (against.content?.length || 0) : op.position.column,
        },
      };
    }
  }
  
  // Add more transformation rules as needed
  return op;
}

// Store implementation
export const useCollaborationStore = create<CollaborationState>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      startCollaboration: async (config: CollaborationConfig): Promise<boolean> => {
        try {
          const sessionId = generateId();
          const shareId = generateShareId();
          
          const currentUser: CurrentUser = {
            id: generateId(),
            name: config.sessionName || 'Host',
            color: getParticipantColor(0),
            joinedAt: new Date(),
            lastSeen: new Date(),
            status: 'online',
            isAuthenticated: true,
            metadata: {
              userAgent: navigator.userAgent,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            },
          };
          
          set({
            isCollaborating: true,
            sessionId,
            shareId,
            isHost: true,
            currentUser,
            sessionPermissions: config.permissions,
            userPermissions: {
              ...initialState.userPermissions,
              canManageSession: true,
              canKickUsers: true,
              canTransferHost: true,
              canEndSession: true,
              canInvite: true,
            },
            maxParticipants: config.maxParticipants || 10,
            isRecording: config.recordingEnabled || false,
            recordingPermissions: {
              canStart: true,
              canStop: true,
              canDownload: true,
              requireConsent: config.permissions.allowRecording,
            },
          });
          
          // Add system message
          const systemMessage: ChatMessage = {
            id: generateId(),
            type: 'system',
            content: 'Collaboration session started',
            author: 'system',
            authorName: 'System',
            timestamp: new Date(),
          };
          
          set(state => ({
            messages: [systemMessage, ...state.messages],
          }));
          
          return true;
        } catch (error) {
          console.error('Failed to start collaboration:', error);
          return false;
        }
      },

      stopCollaboration: () => {
        // Clean up WebSocket connections, etc.
        set(initialState, false, 'stopCollaboration');
      },

      joinSession: async (shareId: string, userData: UserData): Promise<boolean> => {
        try {
          const currentUser: CurrentUser = {
            id: generateId(),
            name: userData.name,
            color: getParticipantColor(get().participants.length),
            joinedAt: new Date(),
            lastSeen: new Date(),
            status: 'online',
            isAuthenticated: false,
            metadata: {
              userAgent: navigator.userAgent,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
              ...userData.metadata,
            },
          };
          
          set({
            isCollaborating: true,
            shareId,
            isHost: false,
            currentUser,
          });
          
          return true;
        } catch (error) {
          console.error('Failed to join session:', error);
          return false;
        }
      },

      leaveSession: () => {
        const { currentUser } = get();
        if (currentUser) {
          // Send leave notification
          set(state => ({
            messages: [{
              id: generateId(),
              type: 'system',
              content: `${currentUser.name} left the session`,
              author: 'system',
              authorName: 'System',
              timestamp: new Date(),
            }, ...state.messages],
          }));
        }
        
        set(initialState, false, 'leaveSession');
      },

      addParticipant: (participant: Participant) => {
        set(state => {
          const newParticipant = {
            ...participant,
            color: getParticipantColor(state.participants.length),
          };
          
          const systemMessage: ChatMessage = {
            id: generateId(),
            type: 'system',
            content: `${participant.name} joined the session`,
            author: 'system',
            authorName: 'System',
            timestamp: new Date(),
          };
          
          return {
            participants: [...state.participants, newParticipant],
            messages: [systemMessage, ...state.messages],
          };
        });
      },

      removeParticipant: (participantId: string) => {
        set(state => {
          const participant = state.participants.find(p => p.id === participantId);
          const newParticipants = state.participants.filter(p => p.id !== participantId);
          
          // Clean up participant data
          const newCursors = new Map(state.cursors);
          const newSelections = new Map(state.selections);
          const newActiveTyping = new Set(state.activeTyping);
          
          newCursors.delete(participantId);
          newSelections.delete(participantId);
          newActiveTyping.delete(participantId);
          
          const updates: Partial<CollaborationState> = {
            participants: newParticipants,
            cursors: newCursors,
            selections: newSelections,
            activeTyping: newActiveTyping,
          };
          
          if (participant) {
            const systemMessage: ChatMessage = {
              id: generateId(),
              type: 'system',
              content: `${participant.name} left the session`,
              author: 'system',
              authorName: 'System',
              timestamp: new Date(),
            };
            
            updates.messages = [systemMessage, ...state.messages];
          }
          
          return updates;
        });
      },

      updateParticipant: (participantId: string, updates: Partial<Participant>) => {
        set(state => ({
          participants: state.participants.map(participant =>
            participant.id === participantId
              ? { ...participant, ...updates, lastSeen: new Date() }
              : participant
          ),
        }));
      },

      updateCursor: (userId: string, position: CursorPosition) => {
        set(state => {
          const newCursors = new Map(state.cursors);
          newCursors.set(userId, position);
          return { cursors: newCursors };
        });
      },

      updateSelection: (userId: string, range: SelectionRange | null) => {
        set(state => {
          const newSelections = new Map(state.selections);
          if (range) {
            newSelections.set(userId, range);
          } else {
            newSelections.delete(userId);
          }
          return { selections: newSelections };
        });
      },

      setTyping: (userId: string, isTyping: boolean) => {
        set(state => {
          const newActiveTyping = new Set(state.activeTyping);
          if (isTyping) {
            newActiveTyping.add(userId);
          } else {
            newActiveTyping.delete(userId);
          }
          return { activeTyping: newActiveTyping };
        });
      },

      sendMessage: (messageData: Omit<ChatMessage, 'id' | 'timestamp'>) => {
        const message: ChatMessage = {
          ...messageData,
          id: generateId(),
          timestamp: new Date(),
        };
        
        set(state => ({
          messages: [message, ...state.messages].slice(0, 1000), // Keep last 1000 messages
        }));
      },

      addNotification: (notificationData: Omit<Notification, 'id' | 'timestamp'>) => {
        const notification: Notification = {
          ...notificationData,
          id: generateId(),
          timestamp: new Date(),
        };
        
        set(state => ({
          notifications: [notification, ...state.notifications],
        }));
        
        // Auto-dismiss non-persistent notifications
        if (!notification.persistent) {
          const duration = notification.duration || 5000;
          setTimeout(() => {
            set(state => ({
              notifications: state.notifications.filter(n => n.id !== notification.id),
            }));
          }, duration);
        }
      },

      dismissNotification: (notificationId: string) => {
        set(state => ({
          notifications: state.notifications.filter(n => n.id !== notificationId),
        }));
      },

      submitOperation: (operationData: Omit<Operation, 'id' | 'timestamp' | 'author'>) => {
        const { currentUser, lastOperationId } = get();
        if (!currentUser) return;
        
        const operation: Operation = {
          ...operationData,
          id: lastOperationId + 1,
          timestamp: new Date(),
          author: currentUser.id,
        };
        
        set(state => ({
          operationQueue: [...state.operationQueue, operation],
          lastOperationId: operation.id,
          pendingOperations: new Set([...state.pendingOperations, operation.id]),
        }));
      },

      ackOperation: (operationId: number) => {
        set(state => {
          const newPendingOperations = new Set(state.pendingOperations);
          newPendingOperations.delete(operationId);
          return { pendingOperations: newPendingOperations };
        });
      },

      transformOperation,

      updatePermissions: (permissions: Partial<SessionPermissions>) => {
        set(state => ({
          sessionPermissions: { ...state.sessionPermissions, ...permissions },
        }));
      },

      kickParticipant: (participantId: string) => {
        const { userPermissions, currentUser } = get();
        if (!userPermissions.canKickUsers || !currentUser) return;
        
        get().removeParticipant(participantId);
      },

      transferHost: (participantId: string) => {
        const { userPermissions, participants } = get();
        if (!userPermissions.canTransferHost) return;
        
        const newHost = participants.find(p => p.id === participantId);
        if (!newHost) return;
        
        set({
          isHost: false,
          userPermissions: {
            ...initialState.userPermissions,
            canWrite: true,
            canExecute: true,
          },
        });
        
        // Update the new host's permissions (this would be handled by the server)
        get().updateParticipant(participantId, {
          permissions: {
            ...newHost.permissions,
            canInvite: true,
          },
        });
      },

      startRecording: () => {
        const { recordingPermissions } = get();
        if (!recordingPermissions.canStart) return;
        
        set({ isRecording: true });
        
        get().addNotification({
          type: 'info',
          title: 'Recording Started',
          message: 'This collaboration session is now being recorded.',
          persistent: true,
        });
      },

      stopRecording: () => {
        const { recordingPermissions } = get();
        if (!recordingPermissions.canStop) return;
        
        set({ isRecording: false });
        
        get().addNotification({
          type: 'success',
          title: 'Recording Stopped',
          message: 'Recording has been saved and is available for download.',
          duration: 10000,
        });
      },

      resetCollaboration: () => {
        set(initialState, false, 'resetCollaboration');
      },
    })),
    { name: 'collaboration-store' }
  )
);

// Selector hooks for optimized subscriptions
export const useCollaborationSession = () =>
  useCollaborationStore(state => ({
    isCollaborating: state.isCollaborating,
    sessionId: state.sessionId,
    shareId: state.shareId,
    isHost: state.isHost,
    isRecording: state.isRecording,
  }));

export const useCollaborationParticipants = () =>
  useCollaborationStore(state => ({
    participants: state.participants,
    currentUser: state.currentUser,
    maxParticipants: state.maxParticipants,
    cursors: state.cursors,
    selections: state.selections,
    activeTyping: state.activeTyping,
  }));

export const useCollaborationChat = () =>
  useCollaborationStore(state => ({
    messages: state.messages,
    sendMessage: state.sendMessage,
  }));

export const useCollaborationPermissions = () =>
  useCollaborationStore(state => ({
    sessionPermissions: state.sessionPermissions,
    userPermissions: state.userPermissions,
    recordingPermissions: state.recordingPermissions,
  }));

export const useCollaborationNotifications = () =>
  useCollaborationStore(state => ({
    notifications: state.notifications,
    addNotification: state.addNotification,
    dismissNotification: state.dismissNotification,
  }));