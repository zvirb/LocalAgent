import React from 'react';
import ReactDOM from 'react-dom/client';
import { ErrorBoundary } from 'react-error-boundary';
import App from './App';
import './index.css';
import { registerSW } from 'virtual:pwa-register';

// Global error handler
function ErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="min-h-screen bg-terminal-bg flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">⚡</div>
        <h2 className="text-xl font-semibold text-terminal-fg mb-2">
          Something went wrong
        </h2>
        <pre className="text-sm text-accent-error bg-surface-200 p-3 rounded-lg mb-4 overflow-auto">
          {error.message}
        </pre>
        <button
          onClick={resetErrorBoundary}
          className="bg-accent-primary hover:bg-accent-primary/80 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Try again
        </button>
        <div className="mt-4 text-sm text-surface-500">
          If this problem persists, please refresh the page or check the browser console.
        </div>
      </div>
    </div>
  );
}

// Service Worker registration for PWA
const updateSW = registerSW({
  onNeedRefresh() {
    // Show update available notification
    const event = new CustomEvent('sw-update-available');
    window.dispatchEvent(event);
  },
  onOfflineReady() {
    // Show offline ready notification
    const event = new CustomEvent('sw-offline-ready');
    window.dispatchEvent(event);
  },
  onRegisterError(error) {
    console.error('SW registration error:', error);
  }
});

// Make updateSW available globally for update prompts
declare global {
  interface Window {
    updateSW: typeof updateSW;
  }
}
window.updateSW = updateSW;

// Performance monitoring
const perfObserver = new PerformanceObserver((list) => {
  const entries = list.getEntries();
  entries.forEach((entry) => {
    if (entry.entryType === 'navigation') {
      console.log('Navigation timing:', {
        type: entry.name,
        start: entry.startTime,
        duration: entry.duration,
        transferSize: (entry as PerformanceNavigationTiming).transferSize,
      });
    } else if (entry.entryType === 'paint') {
      console.log('Paint timing:', {
        type: entry.name,
        start: entry.startTime,
      });
    }
  });
});

if ('PerformanceObserver' in window) {
  perfObserver.observe({ entryTypes: ['navigation', 'paint'] });
}

// Initialize React app
const root = ReactDOM.createRoot(document.getElementById('root')!);

// Render with error boundary and React strict mode for development
root.render(
  <React.StrictMode>
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={(error, errorInfo) => {
        console.error('React Error Boundary caught an error:', error, errorInfo);
        
        // Send error to monitoring service in production
        if (import.meta.env.PROD) {
          // TODO: Implement error reporting service
          console.log('Would send error to monitoring service:', { error: error.message, stack: error.stack });
        }
      }}
      onReset={() => {
        // Clear any error state and reload if needed
        window.location.reload();
      }}
    >
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);

// Hot module replacement for development
if (import.meta.hot) {
  import.meta.hot.accept();
}

// Development helpers
if (import.meta.env.DEV) {
  // Add debugging helpers to window
  Object.assign(window, {
    React,
    ReactDOM,
    // Add more debugging utilities as needed
  });
  
  console.log('🚀 CLIX Terminal started in development mode');
  console.log('Environment:', {
    mode: import.meta.env.MODE,
    dev: import.meta.env.DEV,
    prod: import.meta.env.PROD,
  });
}

// PWA installation tracking
window.addEventListener('pwa-installable', ((event: CustomEvent) => {
  console.log('PWA installation available');
  // The install prompt is stored in event.detail.prompt
}) as EventListener);

// Network status monitoring
window.addEventListener('online', () => {
  console.log('Connection restored');
  const event = new CustomEvent('network-online');
  window.dispatchEvent(event);
});

window.addEventListener('offline', () => {
  console.log('Connection lost');
  const event = new CustomEvent('network-offline');
  window.dispatchEvent(event);
});

// Keyboard shortcuts for accessibility
document.addEventListener('keydown', (event) => {
  // Alt + / for help
  if (event.altKey && event.key === '/') {
    event.preventDefault();
    const helpEvent = new CustomEvent('show-help');
    window.dispatchEvent(helpEvent);
  }
  
  // Ctrl/Cmd + K for command palette
  if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
    event.preventDefault();
    const commandEvent = new CustomEvent('show-command-palette');
    window.dispatchEvent(commandEvent);
  }
});

// Memory usage monitoring (development only)
if (import.meta.env.DEV && 'memory' in performance) {
  setInterval(() => {
    const memory = (performance as any).memory;
    if (memory.usedJSHeapSize > 100 * 1024 * 1024) { // 100MB threshold
      console.warn('High memory usage detected:', {
        used: Math.round(memory.usedJSHeapSize / 1024 / 1024) + 'MB',
        total: Math.round(memory.totalJSHeapSize / 1024 / 1024) + 'MB',
        limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024) + 'MB',
      });
    }
  }, 30000); // Check every 30 seconds
}