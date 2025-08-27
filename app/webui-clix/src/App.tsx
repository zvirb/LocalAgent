import React, { Suspense, lazy, useEffect, useState } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { Toaster } from 'react-hot-toast';
import { AnimatePresence } from 'framer-motion';

// Stores
import { useThemeStore } from './stores/themeStore';
import { useTerminalStore } from './stores/terminalStore';
import { useCollaborationStore } from './stores/collaborationStore';

// Components
import LoadingSpinner from './components/ui/LoadingSpinner';
import ErrorFallback from './components/ui/ErrorFallback';
import UpdatePrompt from './components/ui/UpdatePrompt';
import NetworkStatus from './components/ui/NetworkStatus';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';

// Lazy loaded components for code splitting
const Terminal = lazy(() => import('./components/terminal/Terminal'));
const CollaborationPanel = lazy(() => import('./components/collaboration/CollaborationPanel'));
const CommandPalette = lazy(() => import('./components/ui/CommandPalette'));
const HelpModal = lazy(() => import('./components/ui/HelpModal'));
const SettingsModal = lazy(() => import('./components/ui/SettingsModal'));

function App() {
  // Global state
  const { theme, initializeTheme } = useThemeStore();
  const { isConnected, connectionStatus } = useTerminalStore();
  const { participants, isCollaborating } = useCollaborationStore();
  
  // Local state
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Initialize theme and global event listeners
  useEffect(() => {
    initializeTheme();

    // Global keyboard shortcuts
    const handleKeyDown = (event: KeyboardEvent) => {
      // Command palette: Ctrl/Cmd + K
      if ((event.ctrlKey || event.metaKey) && event.key === 'k' && !event.shiftKey) {
        event.preventDefault();
        setShowCommandPalette(true);
      }
      
      // Help: Alt + /
      if (event.altKey && event.key === '/') {
        event.preventDefault();
        setShowHelp(true);
      }
      
      // Settings: Ctrl/Cmd + ,
      if ((event.ctrlKey || event.metaKey) && event.key === ',') {
        event.preventDefault();
        setShowSettings(true);
      }
      
      // Toggle sidebar: Ctrl/Cmd + B
      if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
        event.preventDefault();
        setSidebarOpen(!sidebarOpen);
      }
      
      // Close modals: Escape
      if (event.key === 'Escape') {
        setShowCommandPalette(false);
        setShowHelp(false);
        setShowSettings(false);
      }
    };

    // Custom event listeners
    const handleShowCommandPalette = () => setShowCommandPalette(true);
    const handleShowHelp = () => setShowHelp(true);
    const handleShowSettings = () => setShowSettings(true);

    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('show-command-palette', handleShowCommandPalette);
    window.addEventListener('show-help', handleShowHelp);
    window.addEventListener('show-settings', handleShowSettings);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('show-command-palette', handleShowCommandPalette);
      window.removeEventListener('show-help', handleShowHelp);
      window.removeEventListener('show-settings', handleShowSettings);
    };
  }, [initializeTheme, sidebarOpen]);

  // Loading fallback component
  const LoadingFallback = ({ error }: { error?: Error }) => (
    <div className="min-h-screen bg-terminal-bg flex items-center justify-center">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-surface-500">
          {error ? 'Something went wrong...' : 'Loading CLIX Terminal...'}
        </p>
        {error && (
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-accent-primary hover:text-accent-primary/80 transition-colors"
          >
            Refresh page
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div 
      className={`min-h-screen transition-colors duration-200 ${theme === 'dark' ? 'dark' : ''}`}
      data-theme={theme}
    >
      <div className="bg-terminal-bg text-terminal-fg font-sans antialiased">
        {/* Layout container */}
        <div className="flex flex-col h-screen overflow-hidden">
          
          {/* Header */}
          <Header 
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
            onShowCommandPalette={() => setShowCommandPalette(true)}
            onShowSettings={() => setShowSettings(true)}
            isConnected={isConnected}
            connectionStatus={connectionStatus}
            participantCount={participants.length}
          />

          {/* Main content area */}
          <div className="flex flex-1 overflow-hidden">
            
            {/* Sidebar */}
            <AnimatePresence>
              {sidebarOpen && (
                <Suspense fallback={<div className="w-64 bg-surface-100 border-r border-surface-300" />}>
                  <Sidebar 
                    isOpen={sidebarOpen}
                    onClose={() => setSidebarOpen(false)}
                    isCollaborating={isCollaborating}
                  />
                </Suspense>
              )}
            </AnimatePresence>

            {/* Terminal area */}
            <main className="flex-1 flex flex-col overflow-hidden">
              <ErrorBoundary FallbackComponent={ErrorFallback}>
                <Suspense fallback={<LoadingFallback />}>
                  <div className="flex-1 flex overflow-hidden">
                    {/* Main terminal */}
                    <div className="flex-1 flex flex-col">
                      <Terminal />
                    </div>

                    {/* Collaboration panel (when active) */}
                    {isCollaborating && (
                      <AnimatePresence>
                        <Suspense fallback={<div className="w-80 bg-surface-100 border-l border-surface-300" />}>
                          <CollaborationPanel />
                        </Suspense>
                      </AnimatePresence>
                    )}
                  </div>
                </Suspense>
              </ErrorBoundary>
            </main>
          </div>
        </div>

        {/* Modals and overlays */}
        <AnimatePresence>
          {/* Command palette */}
          {showCommandPalette && (
            <Suspense fallback={null}>
              <CommandPalette
                isOpen={showCommandPalette}
                onClose={() => setShowCommandPalette(false)}
              />
            </Suspense>
          )}

          {/* Help modal */}
          {showHelp && (
            <Suspense fallback={null}>
              <HelpModal
                isOpen={showHelp}
                onClose={() => setShowHelp(false)}
              />
            </Suspense>
          )}

          {/* Settings modal */}
          {showSettings && (
            <Suspense fallback={null}>
              <SettingsModal
                isOpen={showSettings}
                onClose={() => setShowSettings(false)}
              />
            </Suspense>
          )}
        </AnimatePresence>

        {/* Global UI components */}
        <NetworkStatus />
        <UpdatePrompt />

        {/* Toast notifications */}
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'rgb(33, 38, 45)',
              color: 'rgb(240, 246, 252)',
              border: '1px solid rgb(48, 54, 61)',
            },
            success: {
              iconTheme: {
                primary: 'rgb(63, 185, 80)',
                secondary: 'rgb(33, 38, 45)',
              },
            },
            error: {
              iconTheme: {
                primary: 'rgb(248, 81, 73)',
                secondary: 'rgb(33, 38, 45)',
              },
            },
          }}
        />

        {/* Development tools */}
        {import.meta.env.DEV && (
          <div className="fixed bottom-4 left-4 z-50 opacity-20 hover:opacity-100 transition-opacity">
            <div className="bg-surface-200 rounded-lg p-2 text-xs space-y-1">
              <div>Mode: {import.meta.env.MODE}</div>
              <div>Connected: {isConnected ? '✓' : '✗'}</div>
              <div>Theme: {theme}</div>
              <div>Collaborating: {isCollaborating ? '✓' : '✗'}</div>
              <div>Participants: {participants.length}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;