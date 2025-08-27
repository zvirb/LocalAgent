import React, { useRef, useEffect, useCallback, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebglAddon } from 'xterm-addon-webgl';
import { CanvasAddon } from 'xterm-addon-canvas';
import { SearchAddon } from 'xterm-addon-search';
import { Unicode11Addon } from 'xterm-addon-unicode11';
import { WebLinksAddon } from 'xterm-addon-web-links';
import { motion, AnimatePresence } from 'framer-motion';
import { useHotkeys } from 'react-hotkeys-hook';

// Stores and hooks
import { useTerminalStore } from '../../stores/terminalStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useFileDrop } from '../../hooks/useFileDrop';

// Components
import TerminalToolbar from './TerminalToolbar';
import SearchPanel from './SearchPanel';
import FileUploadOverlay from './FileUploadOverlay';
import ConnectionStatus from '../ui/ConnectionStatus';

// Types
interface TerminalProps {
  sessionId?: string;
  className?: string;
}

const Terminal: React.FC<TerminalProps> = ({
  sessionId = 'default',
  className = ''
}) => {
  // Refs
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const addonsRef = useRef<{
    fit?: FitAddon;
    webgl?: WebglAddon;
    canvas?: CanvasAddon;
    search?: SearchAddon;
    unicode?: Unicode11Addon;
    webLinks?: WebLinksAddon;
  }>({});

  // Store state
  const { 
    isConnected, 
    connectionStatus, 
    history,
    setTerminalInstance,
    addToHistory 
  } = useTerminalStore();
  
  const { 
    fontSize, 
    fontFamily, 
    theme: terminalTheme,
    cursorStyle,
    scrollback,
    bellSound,
    webglEnabled 
  } = useSettingsStore();

  // Local state
  const [showSearch, setShowSearch] = useState(false);
  const [isWebGLEnabled, setIsWebGLEnabled] = useState(false);
  const [renderingMode, setRenderingMode] = useState<'webgl' | 'canvas' | 'dom'>('dom');

  // WebSocket connection
  const { 
    sendMessage, 
    lastMessage, 
    connectionState,
    error: wsError 
  } = useWebSocket({
    url: `ws://localhost:8080/ws/terminal/${sessionId}`,
    options: {
      shouldReconnect: () => true,
      reconnectInterval: 1000,
      reconnectAttempts: 10,
      heartbeat: {
        message: JSON.stringify({ type: 'ping' }),
        timeout: 30000,
        interval: 25000,
      },
    },
    onMessage: handleWebSocketMessage,
  });

  // File drop functionality
  const {
    isDragging,
    uploadProgress,
    handleDrop,
    handleDragOver,
    handleDragLeave
  } = useFileDrop({
    onFileDrop: handleFileDrop,
    onUploadProgress: (progress: number) => {
      console.log('Upload progress:', progress);
    },
    maxFileSize: 100 * 1024 * 1024, // 100MB
    allowedTypes: ['*'], // Allow all file types
  });

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return;

    // Create terminal instance with optimized configuration
    const terminal = new XTerm({
      fontFamily: fontFamily || 'JetBrains Mono, Fira Code, Cascadia Code, Monaco, Consolas, monospace',
      fontSize: fontSize || 14,
      lineHeight: 1.4,
      letterSpacing: 0,
      theme: getTerminalTheme(terminalTheme),
      cursorStyle: cursorStyle || 'block',
      cursorBlink: true,
      scrollback: scrollback || 10000,
      bellStyle: bellSound ? 'sound' : 'none',
      allowProposedApi: true,
      allowTransparency: false,
      convertEol: true,
      disableStdin: false,
      fastScrollModifier: 'alt',
      macOptionIsMeta: true,
      rightClickSelectsWord: true,
      screenReaderMode: false,
      smoothScrollDuration: 120,
      windowsMode: false,
      wordSeparator: ' ()[]{}",\':;<>~!@#$%^&*|+=`?/\\',
    });

    // Store terminal reference
    xtermRef.current = terminal;
    setTerminalInstance(terminal);

    // Initialize addons
    const fit = new FitAddon();
    const search = new SearchAddon();
    const unicode = new Unicode11Addon();
    const webLinks = new WebLinksAddon();
    
    terminal.loadAddon(fit);
    terminal.loadAddon(search);
    terminal.loadAddon(unicode);
    terminal.loadAddon(webLinks);
    
    addonsRef.current = { fit, search, unicode, webLinks };

    // Try to load WebGL addon first, fallback to Canvas
    if (webglEnabled && isWebGLSupported()) {
      try {
        const webgl = new WebglAddon();
        terminal.loadAddon(webgl);
        addonsRef.current.webgl = webgl;
        setIsWebGLEnabled(true);
        setRenderingMode('webgl');
        console.log('🚀 WebGL renderer initialized');
      } catch (error) {
        console.warn('WebGL not available, falling back to Canvas:', error);
        initializeCanvasRenderer(terminal);
      }
    } else {
      initializeCanvasRenderer(terminal);
    }

    // Activate unicode support
    terminal.unicode.activeVersion = '11';

    // Open terminal in DOM
    terminal.open(terminalRef.current);

    // Fit terminal to container
    fit.fit();

    // Set up event listeners
    setupTerminalEventListeners(terminal);

    // Send initial connection message
    sendMessage(JSON.stringify({
      type: 'init',
      sessionId,
      clientInfo: {
        userAgent: navigator.userAgent,
        renderer: renderingMode,
        webglSupported: isWebGLSupported(),
        screenSize: {
          width: window.screen.width,
          height: window.screen.height,
        }
      }
    }));

    // Cleanup function
    return () => {
      if (xtermRef.current) {
        xtermRef.current.dispose();
        xtermRef.current = null;
      }
      Object.values(addonsRef.current).forEach(addon => {
        if (addon && 'dispose' in addon) {
          addon.dispose();
        }
      });
      addonsRef.current = {};
    };
  }, []);

  // Handle WebSocket messages
  function handleWebSocketMessage(event: MessageEvent) {
    try {
      const data = JSON.parse(event.data);
      const terminal = xtermRef.current;
      
      if (!terminal) return;

      switch (data.type) {
        case 'output':
          terminal.write(data.content);
          break;
          
        case 'command':
          addToHistory(data.command);
          break;
          
        case 'resize':
          if (addonsRef.current.fit) {
            addonsRef.current.fit.fit();
          }
          break;
          
        case 'clear':
          terminal.clear();
          break;
          
        case 'theme':
          terminal.options.theme = getTerminalTheme(data.theme);
          break;
          
        case 'error':
          console.error('Terminal error:', data.message);
          terminal.write(`\r\n\x1b[31mError: ${data.message}\x1b[0m\r\n`);
          break;
          
        case 'pong':
          // Heartbeat response
          break;
          
        default:
          console.log('Unknown message type:', data.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  // Initialize Canvas renderer as fallback
  function initializeCanvasRenderer(terminal: XTerm) {
    try {
      const canvas = new CanvasAddon();
      terminal.loadAddon(canvas);
      addonsRef.current.canvas = canvas;
      setRenderingMode('canvas');
      console.log('📦 Canvas renderer initialized');
    } catch (error) {
      console.warn('Canvas renderer failed, using DOM:', error);
      setRenderingMode('dom');
    }
  }

  // Check WebGL support
  function isWebGLSupported(): boolean {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
      return !!gl;
    } catch {
      return false;
    }
  }

  // Set up terminal event listeners
  function setupTerminalEventListeners(terminal: XTerm) {
    // Handle user input
    terminal.onData((data) => {
      sendMessage(JSON.stringify({
        type: 'input',
        sessionId,
        data
      }));
    });

    // Handle resize events
    terminal.onResize(({ cols, rows }) => {
      sendMessage(JSON.stringify({
        type: 'resize',
        sessionId,
        cols,
        rows
      }));
    });

    // Handle selection changes
    terminal.onSelectionChange(() => {
      const selection = terminal.getSelection();
      if (selection) {
        navigator.clipboard?.writeText(selection);
      }
    });

    // Handle title changes
    terminal.onTitleChange((title) => {
      document.title = `${title} - CLIX Terminal`;
    });
  }

  // Get terminal theme configuration
  function getTerminalTheme(theme: string) {
    const themes = {
      dark: {
        background: '#0d1117',
        foreground: '#f0f6fc',
        cursor: '#58a6ff',
        cursorAccent: '#0d1117',
        selection: '#264f78',
        black: '#484f58',
        red: '#ff7b72',
        green: '#3fb950',
        yellow: '#d29922',
        blue: '#58a6ff',
        magenta: '#bc8cff',
        cyan: '#39c5cf',
        white: '#f0f6fc',
        brightBlack: '#6e7681',
        brightRed: '#ffa198',
        brightGreen: '#56d364',
        brightYellow: '#e3b341',
        brightBlue: '#79c0ff',
        brightMagenta: '#d2a8ff',
        brightCyan: '#56d4dd',
        brightWhite: '#f0f6fc'
      },
      light: {
        background: '#ffffff',
        foreground: '#24292f',
        cursor: '#0969da',
        cursorAccent: '#ffffff',
        selection: '#0969da40',
        black: '#24292f',
        red: '#cf222e',
        green: '#116329',
        yellow: '#4d2d00',
        blue: '#0969da',
        magenta: '#8250df',
        cyan: '#1b7c83',
        white: '#6e7781',
        brightBlack: '#656d76',
        brightRed: '#a40e26',
        brightGreen: '#1a7f37',
        brightYellow: '#633c01',
        brightBlue: '#218bff',
        brightMagenta: '#a475f9',
        brightCyan: '#3192aa',
        brightWhite: '#8c959f'
      }
    };
    
    return themes[theme as keyof typeof themes] || themes.dark;
  }

  // Handle file drop
  async function handleFileDrop(files: File[]) {
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('sessionId', sessionId);

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth-token')}`
          }
        });

        if (response.ok) {
          const result = await response.json();
          const terminal = xtermRef.current;
          if (terminal) {
            terminal.write(`\r\n\x1b[32m✓ Uploaded: ${file.name} → ${result.path}\x1b[0m\r\n`);
          }
        }
      } catch (error) {
        console.error('File upload failed:', error);
        const terminal = xtermRef.current;
        if (terminal) {
          terminal.write(`\r\n\x1b[31m✗ Upload failed: ${file.name}\x1b[0m\r\n`);
        }
      }
    }
  }

  // Fit terminal to container
  const handleResize = useCallback(() => {
    if (addonsRef.current.fit) {
      addonsRef.current.fit.fit();
    }
  }, []);

  // Clear terminal
  const handleClear = useCallback(() => {
    if (xtermRef.current) {
      xtermRef.current.clear();
    }
  }, []);

  // Handle search
  const handleSearch = useCallback((query: string, options?: any) => {
    if (addonsRef.current.search && xtermRef.current) {
      return addonsRef.current.search.findNext(query, options);
    }
    return false;
  }, []);

  // Keyboard shortcuts
  useHotkeys('ctrl+shift+f, cmd+shift+f', () => setShowSearch(!showSearch));
  useHotkeys('ctrl+shift+c, cmd+shift+c', () => handleClear());
  useHotkeys('ctrl+0, cmd+0', () => handleResize());
  
  // Handle window resize
  useEffect(() => {
    const resizeObserver = new ResizeObserver(handleResize);
    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current);
    }
    
    return () => resizeObserver.disconnect();
  }, [handleResize]);

  // Handle settings changes
  useEffect(() => {
    const terminal = xtermRef.current;
    if (!terminal) return;

    terminal.options.fontSize = fontSize;
    terminal.options.fontFamily = fontFamily;
    terminal.options.cursorStyle = cursorStyle;
    terminal.options.scrollback = scrollback;
    terminal.options.bellStyle = bellSound ? 'sound' : 'none';
    terminal.options.theme = getTerminalTheme(terminalTheme);
    
    handleResize();
  }, [fontSize, fontFamily, terminalTheme, cursorStyle, scrollback, bellSound, handleResize]);

  return (
    <div className={`relative flex flex-col h-full ${className}`}>
      {/* Terminal toolbar */}
      <TerminalToolbar
        isConnected={isConnected}
        connectionStatus={connectionStatus}
        renderingMode={renderingMode}
        onClear={handleClear}
        onSearch={() => setShowSearch(!showSearch)}
        onResize={handleResize}
      />

      {/* Main terminal container */}
      <div 
        className="flex-1 relative"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {/* Connection status overlay */}
        {!isConnected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-terminal-bg/90 backdrop-blur-sm z-10 flex items-center justify-center"
          >
            <ConnectionStatus 
              status={connectionState} 
              error={wsError}
            />
          </motion.div>
        )}

        {/* Terminal element */}
        <div 
          ref={terminalRef}
          className="w-full h-full terminal-container terminal-scrollbar"
          style={{
            fontFamily: fontFamily,
            fontSize: `${fontSize}px`,
          }}
        />

        {/* Search panel */}
        <AnimatePresence>
          {showSearch && (
            <SearchPanel
              onSearch={handleSearch}
              onClose={() => setShowSearch(false)}
            />
          )}
        </AnimatePresence>

        {/* File upload overlay */}
        <AnimatePresence>
          {isDragging && (
            <FileUploadOverlay 
              progress={uploadProgress}
              isDragging={isDragging}
            />
          )}
        </AnimatePresence>

        {/* Performance indicator (development) */}
        {import.meta.env.DEV && (
          <div className="absolute top-2 right-2 text-xs text-surface-500 bg-surface-100 rounded px-2 py-1 z-20">
            {renderingMode.toUpperCase()}
            {isWebGLEnabled && ' ⚡'}
          </div>
        )}
      </div>
    </div>
  );
};

export default Terminal;