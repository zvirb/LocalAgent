# Web Terminal Specialist - Context Package

## Agent Role and Objectives
**Primary Role:** CLIX Web Interface Development Specialist
**Mission:** Create a comprehensive web-based terminal interface that seamlessly bridges CLI functionality to browser-based interaction using modern web terminal technologies.

## Strategic Context and Requirements

### CLIX Web Interface Vision
Transform LocalAgent CLI capabilities into a modern web application that provides:
- Full terminal emulation with CLI compatibility
- Real-time synchronization with desktop CLI instances
- Progressive Web App capabilities for mobile/tablet access
- Advanced web-native features while maintaining CLI authenticity

### Research-Backed Web Terminal Patterns

**Xterm.js Integration Best Practices (2024):**
- Terminal front-end component with full ANSI support
- Used in Microsoft Visual Studio Code and Azure Cloud Shell
- GPU-accelerated rendering for smooth performance
- Unicode and emoji support with proper handling
- Custom keybinding and theme support

**React Integration Approaches:**
Multiple proven libraries available:
- `react-xtermjs`: Hook and component-based approaches
- `xterm-for-react`: Comprehensive React wrapper
- `@pablo-lion/xterm-react`: Latest xterm integration with addon support

## Current System Integration Analysis

### Existing CLI Architecture
The LocalAgent CLI provides comprehensive functionality that must be preserved:

**Core Command System:**
- Provider management (Ollama, OpenAI, Gemini, Perplexity)
- Workflow orchestration with 12-phase system
- Interactive chat sessions with history
- Configuration management and validation
- Plugin system with dynamic loading

**UI/UX Components:**
- Rich-based theming with CLAUDE_COLORS palette
- Interactive prompts and fuzzy search
- Real-time progress indicators
- Multi-format output (Rich, JSON, Markdown)
- Session persistence and management

**Security Model:**
- Credential management with keyring integration
- API key handling and validation
- Configuration encryption
- Session security and isolation

### Web Terminal Technical Requirements

**Authentication and Security (CVE-2024-WS002 Compliant):**
```javascript
// REQUIRED: Header-based authentication pattern
const websocket = new WebSocket('ws://localhost:8005/ws/terminal', [], {
  headers: {
    'Authorization': 'Bearer ' + jwtToken
  }
});

// FORBIDDEN: Query parameter authentication
// ws://localhost:8005/ws/terminal?token=jwt_token_here
```

**WebSocket Communication Architecture:**
```javascript
class CLIXWebSocketManager {
    constructor(config) {
        this.authenticationMethod = 'header-based'; // CVE-2024-WS002 compliance
        this.heartbeatInterval = 30000; // 30 seconds
        this.reconnectionStrategy = 'exponential-backoff';
        this.maxReconnectAttempts = 10;
        this.memoryManagement = {
            maxMessageHistory: 10, // Reduced from 100
            autoCleanup: true,
            memoryThreshold: '50MB'
        };
    }
    
    establishConnection(terminalId) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(`ws://localhost:8005/ws/terminal/${terminalId}`, [], {
                headers: {
                    'Authorization': `Bearer ${this.getJWTToken()}`,
                    'X-Terminal-Protocol': 'clix-1.0'
                }
            });
            
            ws.onopen = () => this.handleConnectionOpen(ws, resolve);
            ws.onmessage = (event) => this.handleMessage(event);
            ws.onclose = (event) => this.handleConnectionClose(event);
            ws.onerror = (error) => this.handleConnectionError(error, reject);
        });
    }
}
```

**Memory Management Requirements:**
```javascript
// Enhanced memory management for web terminal
const useWebSocket = (url, options = {}) => {
    const maxMessageHistory = options.maxMessageHistory || 10;
    const heartbeatInterval = options.heartbeatInterval || 30000;
    
    // Comprehensive cleanup on unmount
    useEffect(() => {
        return () => {
            clearTimeout(reconnectTimeoutRef.current);
            clearInterval(heartbeatIntervalRef.current);
            if (websocketRef.current) {
                websocketRef.current.close(1000);
            }
            setMessageHistory([]); // Clear memory
        };
    }, []);
};
```

## Technical Architecture Specifications

### Frontend Stack Requirements
```javascript
const CLIXTechnicalStack = {
    core: {
        framework: "React 18+",
        terminal: "xterm.js 5.0+",
        integration: "react-xtermjs or xterm-for-react",
        styling: "CSS-in-JS with Claude theme integration"
    },
    
    communication: {
        protocol: "WebSocket + REST API hybrid",
        authentication: "JWT with header-based auth",
        synchronization: "Real-time bidirectional",
        fallback: "HTTP polling for unreliable connections"
    },
    
    progressive: {
        pwa: "Service Worker + Manifest",
        offline: "Basic functionality without server",
        caching: "Terminal state and command history",
        installation: "Add to home screen support"
    },
    
    responsive: {
        mobile: "768px+ tablet optimized",
        desktop: "Full terminal experience",
        touch: "Virtual keyboard integration",
        gestures: "Swipe navigation support"
    }
};
```

### Component Architecture
```jsx
// Main CLIX Terminal Component
const CLIXTerminal = ({
    sessionId,
    theme = 'claude',
    syncWithDesktop = true,
    mobileOptimized = false
}) => {
    const [terminal, setTerminal] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('connecting');
    const [commandHistory, setCommandHistory] = useState([]);
    const [sharedState, setSharedState] = useState({});
    
    // Xterm.js integration with React
    const { terminalRef, fitAddon, webLinksAddon } = useXterm({
        options: {
            theme: convertClaudeThemeToXterm(theme),
            fontSize: mobileOptimized ? 14 : 12,
            fontFamily: 'Monaco, "Lucida Console", monospace',
            cursorBlink: true,
            allowTransparency: false,
            experimentalCharAtlas: 'dynamic'
        }
    });
    
    // WebSocket connection management
    const { connectionState, sendCommand, messageHistory } = useWebSocket(
        `ws://localhost:8005/ws/terminal/${sessionId}`,
        {
            authentication: 'header-jwt',
            heartbeat: true,
            reconnect: 'exponential',
            memoryManagement: true
        }
    );
    
    return (
        <div className="clix-terminal-container">
            <TerminalHeader 
                status={connectionStatus}
                sessionId={sessionId}
                syncEnabled={syncWithDesktop}
            />
            
            <XTermComponent
                ref={terminalRef}
                className="clix-terminal"
                addons={[fitAddon, webLinksAddon]}
                onCommand={handleTerminalCommand}
                onResize={handleTerminalResize}
            />
            
            {mobileOptimized && (
                <VirtualKeyboard
                    onKeyPress={handleVirtualKeyPress}
                    theme={theme}
                />
            )}
            
            <TerminalStatus
                connection={connectionState}
                performance={performanceMetrics}
            />
        </div>
    );
};
```

### CLI-Web Bridge Architecture
```python
# Server-side bridge between CLI and web terminal
class CLIXBridgeServer:
    def __init__(self, config: LocalAgentConfig):
        self.config = config
        self.active_sessions = {}
        self.websocket_manager = WebSocketManager()
        self.command_translator = CLICommandTranslator()
        self.state_synchronizer = StateSync()
    
    async def handle_web_command(self, session_id: str, command: str):
        """
        Translate web terminal commands to CLI operations
        """
        # Parse command with CLI context
        parsed_command = self.command_translator.parse(command)
        
        # Execute command in CLI context
        result = await self.execute_cli_command(parsed_command)
        
        # Format response for web terminal
        web_response = self.format_for_web_terminal(result)
        
        # Send response via WebSocket
        await self.websocket_manager.send_to_session(session_id, web_response)
        
        # Synchronize state with desktop CLI if connected
        if self.state_synchronizer.has_desktop_sync(session_id):
            await self.state_synchronizer.update_desktop_state(session_id, result)
    
    async def synchronize_with_desktop_cli(self, session_id: str):
        """
        Real-time synchronization between web and desktop CLI
        """
        desktop_session = self.find_desktop_session(session_id)
        if desktop_session:
            # Bidirectional state sync
            await self.sync_command_history(session_id, desktop_session)
            await self.sync_configuration(session_id, desktop_session)
            await self.sync_workflow_state(session_id, desktop_session)
```

## Implementation Deliverables

### Phase 1: Core Terminal Interface (Week 1)
**Primary Components:**
- React-based terminal emulator with Xterm.js
- WebSocket communication layer
- Basic authentication system
- Terminal theme integration with CLAUDE_COLORS

**Technical Specifications:**
- Canvas-based rendering with GPU acceleration
- Full ANSI escape sequence support
- Unicode and emoji handling (v9+ compatible)
- Responsive design for 768px+ screens

### Phase 2: CLI Integration Bridge (Week 1-2)
**Bridge Components:**
- Command translation layer (web ↔ CLI)
- Real-time state synchronization
- Session management and persistence
- Error handling and recovery

**Communication Protocol:**
- WebSocket for real-time commands
- REST API for session management
- JWT authentication with header-based tokens
- Heartbeat system for connection monitoring

### Phase 3: Advanced Web Features (Week 2)
**Progressive Web App Features:**
- Service Worker for offline functionality
- App manifest for installation
- Cache strategy for terminal state
- Push notifications for long-running operations

**Mobile Optimization:**
- Virtual keyboard integration
- Touch-friendly interface elements
- Responsive layout adaptation
- Gesture navigation support

## Success Criteria and Metrics

### Functional Requirements
**Command Compatibility:**
- 100% compatibility with existing CLI commands
- Real-time command execution with <100ms latency
- Proper output formatting with Rich/ANSI support
- Error handling with visual feedback

**Synchronization Accuracy:**
- Real-time state sync between CLI and web (>99% accuracy)
- Command history synchronization
- Configuration state consistency
- Workflow state preservation

### Performance Requirements
**Response Times:**
- Command execution: <100ms for local operations
- Network operations: <500ms with progress indicators
- Interface interactions: <50ms feedback
- Connection establishment: <2 seconds

**Resource Efficiency:**
- Memory usage: <100MB browser tab
- CPU usage: <5% during idle
- Network bandwidth: <1MB/hour for typical usage
- Battery impact: Minimal on mobile devices

### User Experience Goals
**Accessibility and Usability:**
- Keyboard navigation for all functions
- Screen reader compatibility
- High-contrast mode support
- Responsive design across devices

**Feature Adoption:**
- 60%+ user transition from CLI to web interface
- 25%+ mobile/tablet usage within 3 months
- 80%+ feature parity satisfaction
- 90%+ reliability score for critical operations

## Coordination and Integration Points

### Backend Integration
- **CLI Command System:** Direct integration with existing command handlers
- **Configuration Management:** Shared config with desktop CLI
- **Session Persistence:** MCP integration for cross-session continuity
- **Security Model:** Consistent authentication and authorization

### Frontend Coordination
- **Theme Consistency:** CLAUDE_COLORS integration across interfaces
- **Component Reusability:** Shared components with desktop TUI mode
- **State Management:** Consistent state handling patterns
- **Performance Optimization:** Coordinated resource usage

### Security and Compliance
- **CVE-2024-WS002 Compliance:** Header-based WebSocket authentication
- **Data Protection:** Encrypted communication and storage
- **Session Security:** Secure token management and rotation
- **Input Validation:** Comprehensive sanitization and validation

This comprehensive context package provides the Web Terminal Specialist with all necessary technical requirements, architectural guidelines, and integration specifications to successfully create the CLIX web interface while maintaining full compatibility with the existing LocalAgent CLI system.