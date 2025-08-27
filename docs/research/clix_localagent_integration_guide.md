# CLIX LocalAgent Integration Guide

## Executive Summary

This guide provides comprehensive integration recommendations for implementing CLIX (CLI eXperience) within the existing LocalAgent architecture. The integration leverages the existing React infrastructure, WebGL performance systems, authentication framework, and orchestration capabilities while providing a seamless web-based terminal experience.

## 1. Architecture Integration Overview

### Existing LocalAgent Components Analysis

Based on the codebase analysis, LocalAgent has a robust architecture with the following key components:

```typescript
interface LocalAgentArchitecture {
  // Frontend Architecture
  webui: {
    framework: 'React 18+';
    stateManagement: 'Context API + useReducer';
    styling: 'Emotion + CSS-in-JS';
    routing: 'React Router';
    authentication: 'JWT + Circuit Breaker';
    performance: 'WebGL Performance Manager';
  };
  
  // Backend Services
  services: {
    orchestration: 'Multi-agent workflow orchestration';
    llmProviders: 'Multiple LLM provider support (Ollama, OpenAI, Gemini, Perplexity)';
    monitoring: 'Comprehensive performance monitoring';
    security: 'Security validation and authentication';
  };

  // Integration Points
  integrationPoints: {
    webSocket: 'Real-time communication';
    docker: 'Container orchestration';
    mcp: 'Memory MCP servers for context management';
    redis: 'Session and coordination management';
  };
}
```

### CLIX Integration Architecture

```typescript
interface CLIXIntegrationArchitecture {
  // Core CLIX Components
  clix: {
    terminal: 'Xterm.js with WebGL rendering';
    communication: 'WebSocket integration with existing auth';
    stateManagement: 'Integrated with LocalAgent Context';
    performance: 'Leverages existing WebGL performance manager';
  };

  // Integration Points
  integration: {
    authentication: 'Uses existing JWT and auth circuit breaker';
    orchestration: 'Connects to LocalAgent workflow system';
    monitoring: 'Extends existing performance monitoring';
    theming: 'Integrates with existing theme system';
  };

  // New CLIX-Specific Services
  newServices: {
    commandProcessor: 'Command parsing and execution';
    outputFormatter: 'ANSI processing and formatting';
    historyManager: 'Command history and autocomplete';
    accessibilityManager: 'Screen reader and keyboard navigation';
  };
}
```

## 2. React Component Integration

### CLIX Component Hierarchy Integration

The CLIX components integrate seamlessly with the existing LocalAgent React architecture:

```tsx
// Integration with existing LocalAgent component structure
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import webglPerformanceManager from '../utils/webglPerformanceManager';

// Main CLIX Terminal Component
export const CLIXTerminal: React.FC<CLIXTerminalProps> = ({
  onCommandExecute,
  initialCommands = [],
  workingDirectory = '/home/user'
}) => {
  const { user, token } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [clixState, clixDispatch] = useCLIX();

  // Integration with existing performance monitoring
  useEffect(() => {
    if (webglPerformanceManager && clixState.terminal) {
      webglPerformanceManager.addTerminalMonitoring(clixState.terminal);
    }
  }, [clixState.terminal]);

  return (
    <CLIXProvider>
      <div className="clix-terminal-container">
        <CLIXHeader 
          user={user}
          workingDirectory={workingDirectory}
          onSettingsClick={() => setShowSettings(true)}
        />
        <CLIXTerminalCanvas
          theme={theme}
          performanceLevel={webglPerformanceManager.getPerformanceLevel()}
          onReady={handleTerminalReady}
        />
        <CLIXStatusBar 
          connectionStatus={clixState.websocket.status}
          performanceMetrics={clixState.performance}
        />
        {showSettings && (
          <CLIXSettings
            onClose={() => setShowSettings(false)}
            onThemeChange={toggleTheme}
          />
        )}
      </div>
    </CLIXProvider>
  );
};

// Integration with existing page structure
export const CLIXPage: React.FC = () => {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PageHeader title="Command Line Interface" />
        <CLIXTerminal
          onCommandExecute={handleCommandExecution}
          workingDirectory="/workspace"
        />
      </DashboardLayout>
    </ProtectedRoute>
  );
};
```

### State Management Integration

```tsx
// Extended Context Integration
interface ExtendedAppState extends AppState {
  clix: {
    terminal: CLIXTerminalState;
    commands: CLIXCommandState;
    accessibility: CLIXAccessibilityState;
    performance: CLIXPerformanceState;
  };
}

// Enhanced App Context Provider
export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [appState, appDispatch] = useReducer(appReducer, initialAppState);
  const [clixState, clixDispatch] = useReducer(clixReducer, initialCLIXState);

  // Combined state and dispatch
  const combinedState = {
    ...appState,
    clix: clixState
  };

  const combinedDispatch = (action: AppAction | CLIXAction) => {
    if (action.type.startsWith('CLIX_')) {
      clixDispatch(action as CLIXAction);
    } else {
      appDispatch(action as AppAction);
    }
  };

  return (
    <AppContext.Provider value={{ state: combinedState, dispatch: combinedDispatch }}>
      <AuthProvider>
        <ThemeProvider>
          <WebSocketProvider>
            {children}
          </WebSocketProvider>
        </ThemeProvider>
      </AuthProvider>
    </AppContext.Provider>
  );
};
```

### Routing Integration

```tsx
// Enhanced routing with CLIX pages
import { Routes, Route, Navigate } from 'react-router-dom';
import { CLIXPage } from '../pages/CLIXPage';
import { CLIXSettings } from '../pages/CLIXSettings';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Existing routes */}
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/agents" element={<AgentCoordinationPage />} />
      <Route path="/kanban" element={<KanbanWorkflowPage />} />
      
      {/* New CLIX routes */}
      <Route path="/cli" element={<CLIXPage />} />
      <Route path="/cli/settings" element={<CLIXSettings />} />
      <Route path="/cli/history" element={<CLIXHistoryPage />} />
      
      {/* Integration routes */}
      <Route path="/dashboard/cli" element={<DashboardWithCLIXIntegration />} />
      
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
```

## 3. Authentication and Security Integration

### JWT Token Integration

```typescript
// Enhanced WebSocket Manager with LocalAgent Auth Integration
class CLIXWebSocketManager extends CLIXWebSocketOptimizer {
  constructor(
    private authCircuitBreaker: AuthCircuitBreaker,
    private sessionManager: SessionManager
  ) {
    super({
      maxReconnectAttempts: 5,
      compressionEnabled: true,
      binaryMessageSupport: true
    });
  }

  async connect(url: string): Promise<void> {
    // Use existing auth system
    const token = this.sessionManager.getValidToken();
    if (!token) {
      throw new Error('Authentication required for CLIX terminal');
    }

    // Validate token before connection
    const isValid = await this.authCircuitBreaker.validateToken(token);
    if (!isValid) {
      // Trigger token refresh
      await this.authCircuitBreaker.refreshToken();
      const newToken = this.sessionManager.getValidToken();
      if (!newToken) {
        throw new Error('Failed to refresh authentication token');
      }
    }

    // Use validated token for WebSocket connection
    await super.connect(url, token);
  }

  protected async handleAuthenticationFailure(): Promise<void> {
    // Integration with existing auth error handling
    this.authCircuitBreaker.handleAuthFailure();
    
    // Notify user through existing notification system
    window.dispatchEvent(new CustomEvent('auth-failure', {
      detail: {
        source: 'clix-terminal',
        message: 'Terminal authentication failed. Please refresh your session.',
        action: 'refresh'
      }
    }));
  }
}

// Security validation integration
class CLIXSecurityValidator {
  constructor(private securityValidator: SecurityValidator) {}

  validateCommand(command: string, context: CommandContext): SecurityValidationResult {
    // Use existing security validation system
    const securityCheck = this.securityValidator.validateInput(command);
    
    if (!securityCheck.isValid) {
      return {
        allowed: false,
        reason: 'Security validation failed',
        details: securityCheck.violations,
        sanitizedCommand: null
      };
    }

    // CLIX-specific validations
    const clixValidations = [
      this.validateCommandLength(command),
      this.validateWorkingDirectory(context.workingDirectory),
      this.validateUserPermissions(context.user, command)
    ];

    const failedValidations = clixValidations.filter(v => !v.valid);
    
    if (failedValidations.length > 0) {
      return {
        allowed: false,
        reason: 'CLIX security validation failed',
        details: failedValidations.map(v => v.reason),
        sanitizedCommand: null
      };
    }

    return {
      allowed: true,
      reason: 'Command validated successfully',
      details: [],
      sanitizedCommand: this.sanitizeCommand(command)
    };
  }

  private sanitizeCommand(command: string): string {
    // Apply consistent sanitization with existing security system
    return this.securityValidator.sanitizeInput(command);
  }
}
```

### Permission System Integration

```typescript
// Integration with existing user permission system
interface CLIXPermissions {
  canExecuteCommands: boolean;
  canAccessFileSystem: boolean;
  canUseOrchestration: boolean;
  canViewLogs: boolean;
  allowedCommands: string[];
  restrictedDirectories: string[];
}

class CLIXPermissionManager {
  constructor(private userRole: UserRole, private permissions: UserPermissions) {}

  checkCommandPermission(command: string): PermissionResult {
    // Extract command name
    const commandName = command.trim().split(' ')[0];
    
    // Check against existing permission system
    if (!this.permissions.hasPermission('cli.execute')) {
      return {
        allowed: false,
        reason: 'User does not have CLI execution permissions'
      };
    }

    // Check command-specific permissions
    const restrictedCommands = ['rm', 'del', 'format', 'dd', 'kill'];
    if (restrictedCommands.includes(commandName)) {
      if (!this.permissions.hasPermission('cli.dangerous_commands')) {
        return {
          allowed: false,
          reason: `Command '${commandName}' requires elevated permissions`
        };
      }
    }

    // Check file system access
    if (this.isFileSystemCommand(commandName)) {
      if (!this.permissions.hasPermission('cli.filesystem')) {
        return {
          allowed: false,
          reason: 'File system access not permitted'
        };
      }
    }

    return {
      allowed: true,
      reason: 'Permission granted'
    };
  }

  private isFileSystemCommand(command: string): boolean {
    const fileSystemCommands = ['ls', 'cd', 'mkdir', 'rmdir', 'cp', 'mv', 'chmod', 'chown'];
    return fileSystemCommands.includes(command);
  }
}
```

## 4. Performance System Integration

### WebGL Performance Manager Integration

```typescript
// Enhanced WebGL Performance Manager for CLIX
class CLIXWebGLIntegration extends webglPerformanceManager {
  private clixTerminal: Terminal | null = null;
  private terminalMetrics: CLIXTerminalMetrics = {
    renderTime: 0,
    writeLatency: 0,
    scrollPerformance: 0,
    memoryUsage: 0
  };

  initializeCLIXTerminal(terminal: Terminal): void {
    this.clixTerminal = terminal;
    this.setupTerminalPerformanceMonitoring();
    this.integrateWithExistingMetrics();
  }

  private setupTerminalPerformanceMonitoring(): void {
    if (!this.clixTerminal) return;

    // Hook into terminal write operations
    const originalWrite = this.clixTerminal.write.bind(this.clixTerminal);
    this.clixTerminal.write = (data: string | Uint8Array) => {
      const startTime = performance.now();
      const result = originalWrite(data);
      const writeTime = performance.now() - startTime;
      
      this.terminalMetrics.writeLatency = this.updateRunningAverage(
        this.terminalMetrics.writeLatency, 
        writeTime, 
        0.1
      );
      
      // Report to existing performance system
      this.reportTerminalMetric('write_latency', writeTime);
      
      return result;
    };

    // Monitor scroll performance
    this.clixTerminal.onScroll(() => {
      const scrollStart = performance.now();
      requestAnimationFrame(() => {
        const scrollTime = performance.now() - scrollStart;
        this.terminalMetrics.scrollPerformance = this.updateRunningAverage(
          this.terminalMetrics.scrollPerformance,
          scrollTime,
          0.1
        );
      });
    });

    // Monitor resize performance
    this.clixTerminal.onResize(() => {
      this.adjustPerformanceForTerminalSize();
    });
  }

  private integrateWithExistingMetrics(): void {
    // Extend existing performance reporting
    const originalGetStats = this.getStats.bind(this);
    this.getStats = () => {
      const existingStats = originalGetStats();
      return {
        ...existingStats,
        terminal: this.terminalMetrics,
        clixIntegration: {
          terminalActive: !!this.clixTerminal,
          adaptivePerformance: this.isAdaptivePerformanceEnabled(),
          memoryPressure: this.getTerminalMemoryPressure()
        }
      };
    };
  }

  private adjustPerformanceForTerminalSize(): void {
    if (!this.clixTerminal) return;

    const terminalArea = this.clixTerminal.rows * this.clixTerminal.cols;
    const currentLevel = this.getPerformanceLevel();

    // Adapt based on terminal size and current performance level
    if (terminalArea > 5000 && currentLevel === 'high') {
      console.log('CLIX: Large terminal detected, adjusting performance');
      this.decreasePerformanceLevel();
    } else if (terminalArea < 2000 && currentLevel === 'low') {
      console.log('CLIX: Small terminal detected, increasing performance');
      this.increasePerformanceLevel();
    }
  }

  private reportTerminalMetric(name: string, value: number): void {
    // Report to existing monitoring system
    if (typeof this.reportExternalMetrics === 'function') {
      this.reportExternalMetrics('clix-terminal', {
        [name]: value,
        timestamp: Date.now()
      });
    }
  }

  private getTerminalMemoryPressure(): 'low' | 'medium' | 'high' {
    if (!performance.memory) return 'low';

    const memoryUsage = performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit;
    
    if (memoryUsage > 0.8) return 'high';
    if (memoryUsage > 0.6) return 'medium';
    return 'low';
  }

  // Override performance level changes to affect terminal
  protected applyPerformanceSettings(): void {
    super.applyPerformanceSettings();
    
    if (this.clixTerminal) {
      const level = this.getPerformanceLevel();
      this.applyCLIXPerformanceSettings(level);
    }
  }

  private applyCLIXPerformanceSettings(level: 'high' | 'medium' | 'low'): void {
    const settings = {
      high: {
        scrollback: 10000,
        smoothScrollDuration: 200,
        fastScrollSensitivity: 5,
        cursorBlink: true
      },
      medium: {
        scrollback: 5000,
        smoothScrollDuration: 100,
        fastScrollSensitivity: 3,
        cursorBlink: true
      },
      low: {
        scrollback: 1000,
        smoothScrollDuration: 0,
        fastScrollSensitivity: 1,
        cursorBlink: false
      }
    };

    const currentSettings = settings[level];
    
    // Apply settings to terminal
    Object.keys(currentSettings).forEach(key => {
      if (key in this.clixTerminal!.options) {
        (this.clixTerminal!.options as any)[key] = (currentSettings as any)[key];
      }
    });

    console.log(`CLIX: Applied ${level} performance settings to terminal`);
  }
}
```

### Memory Management Integration

```typescript
// Integration with existing memory management
class CLIXMemoryIntegration {
  constructor(
    private memoryManager: CLIXMemoryManager,
    private existingMonitoring: any
  ) {
    this.setupIntegration();
  }

  private setupIntegration(): void {
    // Listen for existing memory pressure events
    window.addEventListener('webgl-memory-pressure', () => {
      console.log('CLIX: Responding to WebGL memory pressure');
      this.memoryManager.performEmergencyCleanup();
    });

    // Report CLIX memory usage to existing system
    setInterval(() => {
      const clixMemoryStatus = this.memoryManager.getMemoryStatus();
      
      if (this.existingMonitoring.reportMemoryUsage) {
        this.existingMonitoring.reportMemoryUsage('clix-terminal', {
          used: clixMemoryStatus.used,
          percentage: clixMemoryStatus.percentage,
          status: clixMemoryStatus.status
        });
      }
    }, 30000); // Report every 30 seconds

    // Coordinate memory cleanup
    this.setupCoordinatedCleanup();
  }

  private setupCoordinatedCleanup(): void {
    // Listen for system-wide cleanup requests
    window.addEventListener('system-memory-cleanup', () => {
      this.memoryManager.performEmergencyCleanup();
    });

    // Trigger system cleanup when CLIX memory is critical
    this.memoryManager.on('memory-critical', () => {
      window.dispatchEvent(new CustomEvent('clix-memory-critical'));
    });
  }
}
```

## 5. Orchestration System Integration

### Agent Workflow Integration

```typescript
// Integration with LocalAgent orchestration system
class CLIXOrchestrationIntegration {
  constructor(
    private orchestrationClient: OrchestrationClient,
    private workflowManager: WorkflowManager
  ) {}

  async executeAgentCommand(command: string, context: CommandContext): Promise<CommandResult> {
    // Parse command to determine if it's an agent workflow command
    const agentCommand = this.parseAgentCommand(command);
    
    if (agentCommand) {
      return this.executeWorkflowCommand(agentCommand, context);
    }

    // Execute as regular system command
    return this.executeSystemCommand(command, context);
  }

  private parseAgentCommand(command: string): AgentCommand | null {
    const agentCommandPatterns = [
      /^agent\s+(\w+)\s+(.*)/,           // agent <agent-name> <task>
      /^workflow\s+(\w+)\s*(.*)/,       // workflow <workflow-name> [params]
      /^orchestrate\s+(.*)/,            // orchestrate <complex-task>
      /^phase\s+(\d+)\s+(.*)/           // phase <number> <description>
    ];

    for (const pattern of agentCommandPatterns) {
      const match = command.match(pattern);
      if (match) {
        return this.createAgentCommand(pattern, match);
      }
    }

    return null;
  }

  private async executeWorkflowCommand(
    agentCommand: AgentCommand, 
    context: CommandContext
  ): Promise<CommandResult> {
    try {
      // Create workflow execution context
      const workflowContext = {
        ...context,
        agentCommand,
        terminalSession: context.terminalSessionId,
        userPermissions: context.userPermissions
      };

      // Submit workflow to orchestration system
      const workflowId = await this.orchestrationClient.submitWorkflow({
        type: agentCommand.type,
        agentName: agentCommand.agentName,
        task: agentCommand.task,
        context: workflowContext
      });

      // Return immediate response
      return {
        success: true,
        output: `Workflow ${workflowId} started. Use 'workflow status ${workflowId}' to check progress.`,
        executionTime: 0,
        workflowId
      };
    } catch (error) {
      return {
        success: false,
        output: `Failed to start workflow: ${error.message}`,
        executionTime: 0,
        error: error
      };
    }
  }

  async getWorkflowStatus(workflowId: string): Promise<WorkflowStatus> {
    return this.orchestrationClient.getWorkflowStatus(workflowId);
  }

  async streamWorkflowOutput(
    workflowId: string,
    outputHandler: (chunk: string) => void
  ): Promise<void> {
    // Stream workflow output to terminal
    const stream = this.orchestrationClient.streamWorkflowOutput(workflowId);
    
    stream.on('data', (chunk) => {
      outputHandler(chunk.toString());
    });

    stream.on('end', () => {
      outputHandler('\nWorkflow execution completed.\n');
    });

    stream.on('error', (error) => {
      outputHandler(`\nWorkflow error: ${error.message}\n`);
    });
  }

  // Integration with existing todo system
  async createWorkflowTodo(command: string, description: string): Promise<void> {
    const todoManager = this.workflowManager.getTodoManager();
    
    await todoManager.addTodo({
      content: description,
      status: 'pending',
      activeForm: `Executing: ${description}`,
      source: 'clix-terminal',
      command: command,
      timestamp: new Date().toISOString()
    });
  }
}

// Enhanced command processor with orchestration
class CLIXCommandProcessor {
  constructor(
    private orchestrationIntegration: CLIXOrchestrationIntegration,
    private securityValidator: CLIXSecurityValidator
  ) {}

  async processCommand(
    command: string,
    context: CommandContext,
    outputHandler: (chunk: string) => void
  ): Promise<CommandResult> {
    // Security validation
    const securityResult = this.securityValidator.validateCommand(command, context);
    if (!securityResult.allowed) {
      return {
        success: false,
        output: `Command blocked: ${securityResult.reason}`,
        executionTime: 0,
        securityViolation: true
      };
    }

    const sanitizedCommand = securityResult.sanitizedCommand || command;

    // Check if it's an orchestration command
    const result = await this.orchestrationIntegration.executeAgentCommand(
      sanitizedCommand,
      context
    );

    // If it's a workflow command, set up streaming
    if (result.workflowId) {
      this.orchestrationIntegration.streamWorkflowOutput(
        result.workflowId,
        outputHandler
      );
    }

    return result;
  }
}
```

### MCP Integration for Context Management

```typescript
// Integration with existing MCP servers
class CLIXMCPIntegration {
  constructor(
    private memoryMCP: MemoryMCP,
    private coordinationMCP: CoordinationMCP,
    private workflowMCP: WorkflowMCP
  ) {}

  async storeCommandHistory(
    sessionId: string,
    commands: CommandHistoryEntry[]
  ): Promise<void> {
    await this.memoryMCP.storeEntity('clix-command-history', sessionId, {
      commands,
      timestamp: new Date().toISOString(),
      retention: '30 days'
    });
  }

  async getCommandHistory(sessionId: string): Promise<CommandHistoryEntry[]> {
    const entity = await this.memoryMCP.retrieveEntity('clix-command-history', sessionId);
    return entity?.commands || [];
  }

  async storeTerminalSession(
    sessionId: string,
    sessionData: TerminalSessionData
  ): Promise<void> {
    await this.memoryMCP.storeEntity('clix-terminal-session', sessionId, {
      ...sessionData,
      timestamp: new Date().toISOString(),
      retention: '7 days'
    });
  }

  async coordinateWithAgents(
    command: string,
    agentContext: AgentContext
  ): Promise<void> {
    // Use coordination MCP for agent communication
    await this.coordinationMCP.publishEvent('clix-command-executed', {
      command,
      context: agentContext,
      timestamp: new Date().toISOString()
    });
  }

  async getWorkflowContext(workflowId: string): Promise<WorkflowContext | null> {
    return this.workflowMCP.getWorkflowContext(workflowId);
  }

  async updateWorkflowContext(
    workflowId: string,
    updates: Partial<WorkflowContext>
  ): Promise<void> {
    await this.workflowMCP.updateWorkflowContext(workflowId, updates);
  }
}
```

## 6. Theme System Integration

### Enhanced Theme Integration

```tsx
// Integration with existing theme system
interface ExtendedTheme extends Theme {
  clix: {
    terminal: {
      background: string;
      foreground: string;
      cursor: string;
      selection: string;
      ansiColors: {
        black: string;
        red: string;
        green: string;
        yellow: string;
        blue: string;
        magenta: string;
        cyan: string;
        white: string;
        brightBlack: string;
        brightRed: string;
        brightGreen: string;
        brightYellow: string;
        brightBlue: string;
        brightMagenta: string;
        brightCyan: string;
        brightWhite: string;
      };
    };
    statusBar: {
      background: string;
      foreground: string;
      border: string;
    };
    commands: {
      prompt: string;
      success: string;
      error: string;
      warning: string;
    };
  };
}

// Enhanced theme provider
export const ExtendedThemeProvider: React.FC<{ children: React.ReactNode }> = ({ 
  children 
}) => {
  const [theme, setTheme] = useState<ExtendedTheme>(defaultExtendedTheme);
  const [isDarkMode, setIsDarkMode] = useState(true);

  const toggleTheme = useCallback(() => {
    setIsDarkMode(!isDarkMode);
    const newTheme = isDarkMode ? lightExtendedTheme : darkExtendedTheme;
    setTheme(newTheme);
  }, [isDarkMode]);

  const updateCLIXTheme = useCallback((clixThemeOverrides: Partial<ExtendedTheme['clix']>) => {
    setTheme(prevTheme => ({
      ...prevTheme,
      clix: {
        ...prevTheme.clix,
        ...clixThemeOverrides
      }
    }));
  }, []);

  const contextValue = {
    theme,
    isDarkMode,
    toggleTheme,
    updateCLIXTheme,
    // Existing theme methods
    setAccentColor: (color: string) => setTheme(prev => ({ ...prev, accent: color })),
    setFontSize: (size: number) => setTheme(prev => ({ ...prev, fontSize: size }))
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
};

// CLIX theme hook
export const useCLIXTheme = () => {
  const { theme, updateCLIXTheme } = useContext(ThemeContext);
  
  const getTerminalTheme = useCallback(() => {
    return theme.clix.terminal;
  }, [theme.clix.terminal]);

  const updateTerminalColors = useCallback((colors: Partial<typeof theme.clix.terminal.ansiColors>) => {
    updateCLIXTheme({
      terminal: {
        ...theme.clix.terminal,
        ansiColors: {
          ...theme.clix.terminal.ansiColors,
          ...colors
        }
      }
    });
  }, [theme.clix.terminal, updateCLIXTheme]);

  return {
    terminalTheme: theme.clix.terminal,
    statusBarTheme: theme.clix.statusBar,
    commandTheme: theme.clix.commands,
    getTerminalTheme,
    updateTerminalColors,
    isDarkMode: theme.isDarkMode
  };
};
```

## 7. Monitoring and Analytics Integration

### Performance Monitoring Integration

```typescript
// Enhanced monitoring integration
class CLIXMonitoringIntegration {
  constructor(
    private monitoringSystem: MonitoringSystem,
    private analyticsCollector: AnalyticsCollector
  ) {}

  async trackCommandExecution(
    command: string,
    executionTime: number,
    success: boolean,
    context: CommandContext
  ): Promise<void> {
    // Track command performance
    await this.monitoringSystem.recordMetric('clix.command.execution_time', executionTime, {
      command: this.hashCommand(command), // Hash for privacy
      success: success.toString(),
      user_id: context.userId,
      session_id: context.sessionId
    });

    // Track command success/failure rates
    await this.monitoringSystem.recordCounter('clix.command.executed', 1, {
      status: success ? 'success' : 'failure',
      command_type: this.classifyCommand(command)
    });
  }

  async trackUserInteraction(
    interactionType: 'command' | 'shortcut' | 'scroll' | 'resize',
    details: Record<string, any>
  ): Promise<void> {
    await this.analyticsCollector.recordEvent('clix.user_interaction', {
      type: interactionType,
      timestamp: Date.now(),
      ...details
    });
  }

  async trackAccessibilityUsage(
    feature: 'screen_reader' | 'high_contrast' | 'keyboard_nav' | 'table_mode',
    enabled: boolean
  ): Promise<void> {
    await this.analyticsCollector.recordEvent('clix.accessibility.feature_usage', {
      feature,
      enabled,
      timestamp: Date.now()
    });
  }

  async trackPerformanceMetrics(metrics: CLIXPerformanceMetrics): Promise<void> {
    const metricsToTrack = {
      'clix.performance.fps': metrics.fps,
      'clix.performance.memory_usage': metrics.memoryUsage,
      'clix.performance.render_time': metrics.renderTime,
      'clix.performance.scroll_latency': metrics.scrollLatency
    };

    for (const [metric, value] of Object.entries(metricsToTrack)) {
      await this.monitoringSystem.recordGauge(metric, value);
    }
  }

  private hashCommand(command: string): string {
    // Simple hash for privacy while maintaining analytics value
    const commandType = command.split(' ')[0];
    return btoa(commandType).substring(0, 8);
  }

  private classifyCommand(command: string): string {
    const commandName = command.trim().split(' ')[0].toLowerCase();
    
    if (['ls', 'dir', 'pwd', 'find'].includes(commandName)) return 'navigation';
    if (['cd', 'mkdir', 'rmdir'].includes(commandName)) return 'directory';
    if (['cp', 'mv', 'rm', 'del'].includes(commandName)) return 'file_operation';
    if (['git'].includes(commandName)) return 'git';
    if (['docker', 'kubectl'].includes(commandName)) return 'containerization';
    if (['agent', 'workflow', 'orchestrate'].includes(commandName)) return 'orchestration';
    
    return 'other';
  }
}
```

### Health Check Integration

```typescript
// CLIX health check integration
class CLIXHealthCheck {
  constructor(
    private terminal: Terminal,
    private websocketManager: CLIXWebSocketManager,
    private performanceManager: CLIXWebGLIntegration
  ) {}

  async performHealthCheck(): Promise<HealthCheckResult> {
    const checks = [
      this.checkTerminalHealth(),
      this.checkWebSocketHealth(),
      this.checkPerformanceHealth(),
      this.checkAccessibilityHealth(),
      this.checkIntegrationHealth()
    ];

    const results = await Promise.all(checks);
    
    return {
      overall: results.every(r => r.status === 'healthy') ? 'healthy' : 'degraded',
      timestamp: new Date().toISOString(),
      checks: results.reduce((acc, result, index) => {
        acc[result.component] = result;
        return acc;
      }, {} as Record<string, HealthCheckComponentResult>)
    };
  }

  private async checkTerminalHealth(): Promise<HealthCheckComponentResult> {
    try {
      if (!this.terminal) {
        return {
          component: 'terminal',
          status: 'unhealthy',
          message: 'Terminal not initialized',
          details: {}
        };
      }

      // Check if terminal is responsive
      const testWrite = performance.now();
      this.terminal.write('\x1b[0m'); // Reset command
      const writeLatency = performance.now() - testWrite;

      if (writeLatency > 100) {
        return {
          component: 'terminal',
          status: 'degraded',
          message: 'Terminal write latency high',
          details: { writeLatency }
        };
      }

      return {
        component: 'terminal',
        status: 'healthy',
        message: 'Terminal functioning normally',
        details: { writeLatency, rows: this.terminal.rows, cols: this.terminal.cols }
      };
    } catch (error) {
      return {
        component: 'terminal',
        status: 'unhealthy',
        message: `Terminal health check failed: ${error.message}`,
        details: { error: error.message }
      };
    }
  }

  private async checkWebSocketHealth(): Promise<HealthCheckComponentResult> {
    const connectionStatus = this.websocketManager.getConnectionStatus();
    const metrics = this.websocketManager.getPerformanceMetrics();

    if (connectionStatus !== 'connected') {
      return {
        component: 'websocket',
        status: 'unhealthy',
        message: `WebSocket ${connectionStatus}`,
        details: { status: connectionStatus }
      };
    }

    if (metrics.averageLatency > 500) {
      return {
        component: 'websocket',
        status: 'degraded',
        message: 'High WebSocket latency',
        details: metrics
      };
    }

    return {
      component: 'websocket',
      status: 'healthy',
      message: 'WebSocket connection healthy',
      details: metrics
    };
  }

  private async checkPerformanceHealth(): Promise<HealthCheckComponentResult> {
    const stats = this.performanceManager.getStats();
    
    if (stats.fps < 20) {
      return {
        component: 'performance',
        status: 'degraded',
        message: 'Low frame rate detected',
        details: stats
      };
    }

    if (stats.memory?.percentage > 90) {
      return {
        component: 'performance',
        status: 'degraded',
        message: 'High memory usage',
        details: stats
      };
    }

    return {
      component: 'performance',
      status: 'healthy',
      message: 'Performance metrics normal',
      details: stats
    };
  }

  private async checkAccessibilityHealth(): Promise<HealthCheckComponentResult> {
    const liveRegions = document.querySelectorAll('[aria-live]');
    const focusableElements = document.querySelectorAll('[tabindex]:not([tabindex="-1"])');
    
    const details = {
      liveRegions: liveRegions.length,
      focusableElements: focusableElements.length,
      highContrast: document.body.classList.contains('clix-high-contrast'),
      screenReaderMode: document.body.classList.contains('clix-screen-reader-mode')
    };

    if (liveRegions.length === 0) {
      return {
        component: 'accessibility',
        status: 'degraded',
        message: 'No ARIA live regions found',
        details
      };
    }

    return {
      component: 'accessibility',
      status: 'healthy',
      message: 'Accessibility features functional',
      details
    };
  }

  private async checkIntegrationHealth(): Promise<HealthCheckComponentResult> {
    const integrationChecks = {
      auth: !!window.authCircuitBreaker,
      theme: !!document.querySelector('[data-theme]'),
      monitoring: !!window.monitoringSystem,
      mcp: !!window.mcpConnection
    };

    const failedIntegrations = Object.entries(integrationChecks)
      .filter(([_, isHealthy]) => !isHealthy)
      .map(([name]) => name);

    if (failedIntegrations.length > 0) {
      return {
        component: 'integration',
        status: 'degraded',
        message: `Integration issues: ${failedIntegrations.join(', ')}`,
        details: integrationChecks
      };
    }

    return {
      component: 'integration',
      status: 'healthy',
      message: 'All integrations functional',
      details: integrationChecks
    };
  }
}
```

## 8. Testing Integration

### Integration Testing Framework

```typescript
// Enhanced testing integration
describe('CLIX LocalAgent Integration', () => {
  let app: TestApplication;
  let clixTerminal: CLIXTerminal;
  let authProvider: TestAuthProvider;

  beforeEach(async () => {
    // Set up test environment with existing LocalAgent infrastructure
    app = await createTestApplication({
      components: ['auth', 'theme', 'monitoring', 'orchestration'],
      plugins: ['clix-terminal']
    });

    authProvider = app.getService('auth');
    clixTerminal = app.getComponent('clix-terminal');
    
    await authProvider.login('test-user', 'test-password');
  });

  describe('Authentication Integration', () => {
    it('should use existing JWT authentication', async () => {
      const token = authProvider.getToken();
      expect(token).toBeDefined();
      
      // Verify CLIX uses the same token
      const clixConnection = await clixTerminal.connect();
      expect(clixConnection.token).toBe(token);
    });

    it('should handle auth failures gracefully', async () => {
      authProvider.expireToken();
      
      const commandResult = await clixTerminal.executeCommand('ls');
      expect(commandResult.authError).toBe(true);
      
      // Verify auth refresh was triggered
      expect(authProvider.refreshAttempts).toBe(1);
    });
  });

  describe('Theme Integration', () => {
    it('should apply LocalAgent theme to terminal', async () => {
      const themeProvider = app.getService('theme');
      
      themeProvider.setTheme('dark');
      await new Promise(resolve => setTimeout(resolve, 100)); // Allow theme to apply
      
      const terminalTheme = clixTerminal.getTheme();
      expect(terminalTheme.background).toBe('#1e1e1e');
      expect(terminalTheme.foreground).toBe('#cccccc');
    });

    it('should support high contrast mode', async () => {
      const themeProvider = app.getService('theme');
      
      themeProvider.enableHighContrast();
      
      const terminalTheme = clixTerminal.getTheme();
      expect(terminalTheme.background).toBe('#000000');
      expect(terminalTheme.foreground).toBe('#ffffff');
    });
  });

  describe('Performance Integration', () => {
    it('should report metrics to existing monitoring system', async () => {
      const monitoring = app.getService('monitoring');
      const initialMetrics = monitoring.getMetrics();
      
      // Execute some commands to generate metrics
      await clixTerminal.executeCommand('echo "test"');
      await clixTerminal.executeCommand('ls -la');
      
      const finalMetrics = monitoring.getMetrics();
      expect(finalMetrics['clix.command.executed']).toBeGreaterThan(
        initialMetrics['clix.command.executed'] || 0
      );
    });

    it('should adapt to WebGL performance changes', async () => {
      const webglManager = app.getService('webgl-performance');
      
      webglManager.setPerformanceLevel('low');
      
      const terminalSettings = clixTerminal.getPerformanceSettings();
      expect(terminalSettings.scrollback).toBeLessThan(5000);
      expect(terminalSettings.smoothScrollDuration).toBe(0);
    });
  });

  describe('Orchestration Integration', () => {
    it('should execute agent workflows through existing orchestration', async () => {
      const orchestration = app.getService('orchestration');
      
      const result = await clixTerminal.executeCommand('agent codebase-research-analyst analyze dependencies');
      
      expect(result.success).toBe(true);
      expect(result.workflowId).toBeDefined();
      
      const workflow = await orchestration.getWorkflow(result.workflowId);
      expect(workflow.agent).toBe('codebase-research-analyst');
      expect(workflow.status).toBe('running');
    });

    it('should stream workflow output to terminal', (done) => {
      const orchestration = app.getService('orchestration');
      let outputReceived = '';
      
      clixTerminal.on('output', (data) => {
        outputReceived += data;
      });
      
      clixTerminal.executeCommand('workflow test-workflow')
        .then((result) => {
          // Simulate workflow producing output
          orchestration.simulateWorkflowOutput(result.workflowId, 'Test output\n');
          
          setTimeout(() => {
            expect(outputReceived).toContain('Test output');
            done();
          }, 100);
        });
    });
  });

  afterEach(async () => {
    await clixTerminal.dispose();
    await app.dispose();
  });
});
```

## 9. Deployment Integration

### Build Process Integration

```javascript
// Enhanced Vite configuration for LocalAgent integration
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    react({
      jsxImportSource: '@emotion/react',
      babel: {
        plugins: ['@emotion/babel-plugin']
      }
    })
  ],
  
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@clix': resolve(__dirname, 'src/clix'),
      '@localagent': resolve(__dirname, 'src'), // LocalAgent components
      '@shared': resolve(__dirname, 'src/shared'), // Shared utilities
      '@components': resolve(__dirname, 'src/components'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types')
    }
  },
  
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate CLIX from core LocalAgent
          'clix-core': [
            '@xterm/xterm', 
            '@xterm/addon-webgl', 
            '@xterm/addon-canvas'
          ],
          'clix-ui': [
            'src/clix/components',
            'src/clix/hooks',
            'src/clix/utils'
          ],
          'localagent-core': [
            'src/components',
            'src/context',
            'src/utils'
          ],
          'shared-deps': [
            'react',
            'react-dom',
            '@emotion/react',
            '@emotion/styled'
          ]
        }
      }
    }
  },
  
  // Integration-specific optimizations
  optimizeDeps: {
    include: [
      '@xterm/xterm',
      '@xterm/addon-webgl',
      'motion'
    ]
  }
});
```

### Docker Integration

```dockerfile
# Enhanced Dockerfile with CLIX support
FROM node:18-alpine as builder

WORKDIR /app

# Copy LocalAgent source
COPY package*.json ./
COPY src/ ./src/
COPY public/ ./public/

# Install dependencies (includes CLIX dependencies)
RUN npm ci --only=production

# Build with CLIX integration
RUN npm run build:with-clix

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration with CLIX WebSocket support
COPY nginx-clix.conf /etc/nginx/conf.d/default.conf

# Expose ports
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# nginx-clix.conf - Enhanced nginx configuration
server {
    listen 80;
    server_name localhost;
    
    # Static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://localagent-api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # CLIX WebSocket endpoint
    location /ws/clix {
        proxy_pass http://localagent-api:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # CLIX-specific settings
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_connect_timeout 60s;
    }
    
    # Health check endpoint
    location /health/clix {
        proxy_pass http://localagent-api:8080/health/clix;
        proxy_set_header Host $host;
    }
}
```

## 10. Migration and Rollback Strategy

### Gradual Migration Plan

```typescript
// Feature flag system for gradual CLIX rollout
interface CLIXFeatureFlags {
  enabled: boolean;
  betaUsers: string[];
  features: {
    webglRenderer: boolean;
    orchestrationCommands: boolean;
    advancedAccessibility: boolean;
    performanceMonitoring: boolean;
  };
}

class CLIXFeatureManager {
  constructor(private featureFlags: CLIXFeatureFlags) {}

  isEnabled(userId?: string): boolean {
    if (!this.featureFlags.enabled) return false;
    
    if (userId && this.featureFlags.betaUsers.includes(userId)) {
      return true;
    }
    
    return this.featureFlags.enabled;
  }

  hasFeature(feature: keyof CLIXFeatureFlags['features']): boolean {
    return this.featureFlags.features[feature];
  }

  async enableForUser(userId: string): Promise<void> {
    this.featureFlags.betaUsers.push(userId);
    await this.saveFeatureFlags();
  }

  async rollback(): Promise<void> {
    this.featureFlags.enabled = false;
    await this.saveFeatureFlags();
  }

  private async saveFeatureFlags(): Promise<void> {
    // Save to configuration system
    await fetch('/api/admin/feature-flags', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.featureFlags)
    });
  }
}

// Fallback component for when CLIX is disabled
export const CLIXFallback: React.FC = () => {
  return (
    <div className="clix-fallback">
      <h2>Command Line Interface</h2>
      <p>The enhanced web terminal is currently unavailable.</p>
      <p>
        <a href="/api/terminal" target="_blank" rel="noopener noreferrer">
          Open traditional terminal interface
        </a>
      </p>
    </div>
  );
};

// Feature-flagged CLIX component
export const CLIXTerminalWithFlags: React.FC<CLIXTerminalProps> = (props) => {
  const { user } = useAuth();
  const featureManager = useFeatureManager();
  
  if (!featureManager.isEnabled(user.id)) {
    return <CLIXFallback />;
  }
  
  return <CLIXTerminal {...props} />;
};
```

## Conclusion

This comprehensive integration guide provides a roadmap for seamlessly integrating CLIX into the existing LocalAgent architecture. The integration leverages all existing systems while providing enhanced terminal capabilities:

### Key Integration Points:
1. **React Architecture**: Seamless integration with existing component structure
2. **Authentication**: Full JWT and security system integration
3. **Performance**: Enhanced WebGL performance management
4. **Orchestration**: Direct integration with agent workflow system
5. **Monitoring**: Extended performance and analytics tracking
6. **Theming**: Consistent visual design with existing system
7. **Testing**: Comprehensive integration testing framework
8. **Deployment**: Enhanced build and deployment processes

### Benefits of Integration:
- **Consistent User Experience**: Unified design and authentication
- **Enhanced Performance**: Leveraged existing optimization systems
- **Seamless Workflows**: Direct agent command execution
- **Comprehensive Monitoring**: Extended analytics and health checking
- **Gradual Rollout**: Feature flag system for safe deployment
- **Accessibility**: Full accessibility compliance integrated with existing standards

This integration approach ensures that CLIX enhances LocalAgent's capabilities while maintaining the stability and performance of the existing system.