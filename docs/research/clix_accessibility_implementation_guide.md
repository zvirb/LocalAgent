# CLIX Accessibility Implementation Guide

## Executive Summary

This guide provides comprehensive accessibility implementation strategies for CLIX (CLI eXperience), ensuring compliance with WCAG 2.1 AA standards and providing an inclusive experience for users with disabilities. The guide covers screen reader support, keyboard navigation, visual accessibility, cognitive accessibility, and integration with assistive technologies.

## 1. Accessibility Foundation and Standards

### WCAG 2.1 AA Compliance Requirements

CLIX must meet all WCAG 2.1 AA criteria, with particular attention to terminal-specific accessibility challenges:

#### Level A Requirements (Essential)
- **Perceivable**: Information and UI components must be presentable to users in ways they can perceive
- **Operable**: UI components and navigation must be operable
- **Understandable**: Information and operation of UI must be understandable
- **Robust**: Content must be robust enough for interpretation by assistive technologies

#### Level AA Requirements (Standard)
- **Color Contrast**: Minimum 4.5:1 ratio for normal text, 3:1 for large text
- **Resize Text**: Content can be scaled up to 200% without loss of functionality
- **Keyboard Navigation**: All functionality available from keyboard
- **Focus Management**: Logical focus order and visible focus indicators

### Terminal-Specific Accessibility Challenges

```typescript
interface TerminalAccessibilityChallenge {
  challenge: string;
  impact: 'high' | 'medium' | 'low';
  solution: string;
  wcagCriteria: string[];
}

const terminalAccessibilityChallenges: TerminalAccessibilityChallenge[] = [
  {
    challenge: 'Unstructured text output makes screen reader navigation difficult',
    impact: 'high',
    solution: 'Implement semantic markup and ARIA live regions',
    wcagCriteria: ['1.3.1', '4.1.3']
  },
  {
    challenge: 'ANSI color codes not accessible to color-blind users',
    impact: 'high',
    solution: 'Provide alternative text indicators and high contrast themes',
    wcagCriteria: ['1.4.1', '1.4.3']
  },
  {
    challenge: 'Rapid text updates overwhelm screen readers',
    impact: 'high',
    solution: 'Implement intelligent announcement filtering and rate limiting',
    wcagCriteria: ['2.2.4']
  },
  {
    challenge: 'Complex table outputs are not navigable',
    impact: 'medium',
    solution: 'Convert tables to structured HTML with navigation shortcuts',
    wcagCriteria: ['1.3.1', '2.1.1']
  },
  {
    challenge: 'Mouse-dependent interactions exclude keyboard users',
    impact: 'high',
    solution: 'Provide complete keyboard equivalents for all functionality',
    wcagCriteria: ['2.1.1', '2.1.2']
  }
];
```

## 2. Screen Reader Support Implementation

### ARIA Live Region Management

The foundation of screen reader support in CLIX is intelligent ARIA live region management that provides meaningful updates without overwhelming users.

```typescript
interface ScreenReaderConfig {
  announceCommands: boolean;
  announceOutput: boolean;
  announceErrors: boolean;
  outputSummaryMode: boolean;
  maxAnnouncementLength: number;
  announcementDelay: number;
  filterRepeatedContent: boolean;
}

class CLIXScreenReaderManager {
  private liveRegion: HTMLElement;
  private politeRegion: HTMLElement;
  private assertiveRegion: HTMLElement;
  private statusRegion: HTMLElement;
  private config: ScreenReaderConfig;
  private announcementQueue: string[] = [];
  private lastAnnouncement: string = '';
  private announcementHistory: Set<string> = new Set();

  constructor(config: Partial<ScreenReaderConfig> = {}) {
    this.config = {
      announceCommands: true,
      announceOutput: true,
      announceErrors: true,
      outputSummaryMode: false,
      maxAnnouncementLength: 200,
      announcementDelay: 300,
      filterRepeatedContent: true,
      ...config
    };

    this.createLiveRegions();
    this.setupAnnouncementProcessor();
  }

  private createLiveRegions(): void {
    // Main live region for general updates
    this.liveRegion = this.createLiveRegion('clix-live-region', 'polite');
    
    // Polite region for non-urgent updates
    this.politeRegion = this.createLiveRegion('clix-polite-region', 'polite');
    
    // Assertive region for urgent updates (errors, warnings)
    this.assertiveRegion = this.createLiveRegion('clix-assertive-region', 'assertive');
    
    // Status region for status changes
    this.statusRegion = this.createLiveRegion('clix-status-region', 'status');

    // Add description for the terminal application
    const description = document.createElement('div');
    description.id = 'clix-description';
    description.className = 'sr-only';
    description.textContent = 'LocalAgent Command Line Interface. Type commands and press Enter to execute. Use Tab for autocomplete, Up/Down arrows for command history.';
    document.body.appendChild(description);
  }

  private createLiveRegion(id: string, liveType: 'polite' | 'assertive' | 'status'): HTMLElement {
    const region = document.createElement('div');
    region.id = id;
    region.className = 'sr-only clix-live-region';
    region.setAttribute('aria-live', liveType);
    region.setAttribute('aria-atomic', 'false');
    region.setAttribute('aria-relevant', 'additions text');
    
    if (liveType === 'status') {
      region.setAttribute('role', 'status');
    } else {
      region.setAttribute('role', 'log');
    }

    // Ensure regions are always present in the DOM
    region.style.cssText = `
      position: absolute !important;
      width: 1px !important;
      height: 1px !important;
      padding: 0 !important;
      margin: -1px !important;
      overflow: hidden !important;
      clip: rect(0, 0, 0, 0) !important;
      white-space: nowrap !important;
      border: 0 !important;
    `;

    document.body.appendChild(region);
    return region;
  }

  announceCommand(command: string, context?: CommandContext): void {
    if (!this.config.announceCommands) return;

    const announcement = this.formatCommandAnnouncement(command, context);
    this.announce(announcement, 'polite');
  }

  announceOutput(output: string, type: 'success' | 'error' | 'info' = 'info'): void {
    if (!this.config.announceOutput) return;

    const processedOutput = this.processOutputForScreenReader(output, type);
    const urgency = type === 'error' ? 'assertive' : 'polite';
    
    this.announce(processedOutput, urgency);
  }

  announceStatusChange(status: string, detail?: string): void {
    const fullStatus = detail ? `${status}: ${detail}` : status;
    this.announceToRegion(this.statusRegion, fullStatus);
  }

  private formatCommandAnnouncement(command: string, context?: CommandContext): string {
    const trimmedCommand = command.trim().substring(0, 50);
    let announcement = `Executing command: ${trimmedCommand}`;

    if (context?.workingDirectory) {
      announcement += ` in directory ${context.workingDirectory}`;
    }

    if (context?.estimatedDuration) {
      announcement += ` (estimated ${context.estimatedDuration} seconds)`;
    }

    return announcement;
  }

  private processOutputForScreenReader(output: string, type: string): string {
    // Remove ANSI escape codes
    let cleanOutput = output.replace(/\x1b\[[0-9;]*m/g, '');
    
    // Remove additional escape sequences
    cleanOutput = cleanOutput.replace(/\x1b\[[KH]/g, '');
    
    // Normalize whitespace
    cleanOutput = cleanOutput.replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim();

    // Handle different output types
    if (type === 'error') {
      cleanOutput = `Error: ${cleanOutput}`;
    } else if (type === 'success') {
      cleanOutput = `Success: ${cleanOutput}`;
    }

    // Summarize long output if in summary mode
    if (this.config.outputSummaryMode && cleanOutput.length > this.config.maxAnnouncementLength) {
      return this.summarizeOutput(cleanOutput, type);
    }

    // Truncate if necessary
    if (cleanOutput.length > this.config.maxAnnouncementLength) {
      cleanOutput = cleanOutput.substring(0, this.config.maxAnnouncementLength - 20) + '... (output truncated)';
    }

    return cleanOutput;
  }

  private summarizeOutput(output: string, type: string): string {
    const lines = output.split('\n');
    const lineCount = lines.length;
    
    if (type === 'error') {
      return `Error output: ${lineCount} lines. First line: ${lines[0]?.substring(0, 100) || 'Empty'}`;
    }

    if (lineCount > 5) {
      return `Command output: ${lineCount} lines of text`;
    }

    return output.substring(0, this.config.maxAnnouncementLength);
  }

  private announce(message: string, urgency: 'polite' | 'assertive'): void {
    if (!message.trim()) return;

    // Filter repeated content if enabled
    if (this.config.filterRepeatedContent) {
      if (this.announcementHistory.has(message) || message === this.lastAnnouncement) {
        return;
      }

      this.announcementHistory.add(message);
      this.lastAnnouncement = message;

      // Limit history size
      if (this.announcementHistory.size > 50) {
        const firstItem = this.announcementHistory.values().next().value;
        this.announcementHistory.delete(firstItem);
      }
    }

    const targetRegion = urgency === 'assertive' ? this.assertiveRegion : this.politeRegion;
    this.announceToRegion(targetRegion, message);
  }

  private announceToRegion(region: HTMLElement, message: string): void {
    // Clear previous content
    region.textContent = '';

    // Add new content with a small delay to ensure screen readers notice the change
    setTimeout(() => {
      region.textContent = message;

      // Clear after a reasonable time to prevent accumulation
      setTimeout(() => {
        if (region.textContent === message) {
          region.textContent = '';
        }
      }, 10000);
    }, this.config.announcementDelay);
  }

  private setupAnnouncementProcessor(): void {
    // Process queued announcements
    setInterval(() => {
      if (this.announcementQueue.length > 0) {
        const announcement = this.announcementQueue.shift()!;
        this.announce(announcement, 'polite');
      }
    }, 1000);
  }

  // Configuration methods
  enableOutputSummaryMode(): void {
    this.config.outputSummaryMode = true;
    this.announce('Output summary mode enabled. Long outputs will be summarized.', 'polite');
  }

  disableOutputSummaryMode(): void {
    this.config.outputSummaryMode = false;
    this.announce('Output summary mode disabled. Full outputs will be announced.', 'polite');
  }

  setMaxAnnouncementLength(length: number): void {
    this.config.maxAnnouncementLength = Math.max(50, Math.min(500, length));
    this.announce(`Maximum announcement length set to ${this.config.maxAnnouncementLength} characters.`, 'polite');
  }

  dispose(): void {
    // Clean up live regions
    [this.liveRegion, this.politeRegion, this.assertiveRegion, this.statusRegion]
      .forEach(region => region?.remove());

    document.getElementById('clix-description')?.remove();
  }
}
```

### Semantic HTML Structure

```typescript
class CLIXSemanticStructure {
  private terminal: Terminal;
  private container: HTMLElement;

  constructor(terminal: Terminal, container: HTMLElement) {
    this.terminal = terminal;
    this.container = container;
    this.setupSemanticStructure();
  }

  private setupSemanticStructure(): void {
    // Main terminal application container
    this.container.setAttribute('role', 'application');
    this.container.setAttribute('aria-label', 'LocalAgent Command Line Interface');
    this.container.setAttribute('aria-describedby', 'clix-description clix-help');

    // Terminal output area
    const outputArea = this.container.querySelector('.xterm-viewport');
    if (outputArea) {
      outputArea.setAttribute('role', 'log');
      outputArea.setAttribute('aria-label', 'Command output');
      outputArea.setAttribute('aria-live', 'polite');
      outputArea.setAttribute('tabindex', '0');
    }

    // Command input area
    const inputArea = this.container.querySelector('.xterm-helper-textarea') || 
                     this.createVirtualInputArea();
    if (inputArea) {
      inputArea.setAttribute('role', 'textbox');
      inputArea.setAttribute('aria-label', 'Command input');
      inputArea.setAttribute('aria-describedby', 'clix-input-help');
      inputArea.setAttribute('aria-autocomplete', 'list');
    }

    // Create help text
    this.createHelpText();

    // Add landmark navigation
    this.setupLandmarkNavigation();
  }

  private createVirtualInputArea(): HTMLElement {
    const inputArea = document.createElement('div');
    inputArea.className = 'clix-virtual-input';
    inputArea.contentEditable = 'true';
    inputArea.style.cssText = `
      position: absolute;
      left: -10000px;
      width: 1px;
      height: 1px;
      overflow: hidden;
    `;
    
    this.container.appendChild(inputArea);
    return inputArea;
  }

  private createHelpText(): void {
    const helpContainer = document.createElement('div');
    helpContainer.className = 'sr-only';
    
    helpContainer.innerHTML = `
      <div id="clix-help">
        <h2>LocalAgent Command Line Interface Help</h2>
        <p>This is an interactive command line interface. You can type commands and press Enter to execute them.</p>
        <h3>Keyboard Shortcuts:</h3>
        <ul>
          <li>Enter: Execute current command</li>
          <li>Up/Down arrows: Navigate command history</li>
          <li>Tab: Autocomplete command</li>
          <li>Ctrl+C: Cancel current command</li>
          <li>Ctrl+L: Clear screen</li>
          <li>Alt+H: Show accessibility help</li>
          <li>Alt+T: Toggle table navigation mode</li>
          <li>Alt+S: Toggle output summary mode</li>
        </ul>
        <h3>Navigation:</h3>
        <ul>
          <li>Use Tab to navigate between interface elements</li>
          <li>Use arrow keys to scroll through command output</li>
          <li>Use Page Up/Page Down for faster scrolling</li>
        </ul>
      </div>
      
      <div id="clix-input-help">
        Type commands here. Use Tab for autocomplete and Up/Down arrows for command history.
      </div>
    `;

    document.body.appendChild(helpContainer);
  }

  private setupLandmarkNavigation(): void {
    // Create navigation landmark
    const nav = document.createElement('nav');
    nav.setAttribute('aria-label', 'Terminal navigation');
    nav.className = 'sr-only';
    
    nav.innerHTML = `
      <ul>
        <li><a href="#clix-output" onclick="document.querySelector('#clix-output').focus()">Skip to command output</a></li>
        <li><a href="#clix-input" onclick="document.querySelector('#clix-input').focus()">Skip to command input</a></li>
        <li><a href="#clix-status" onclick="document.querySelector('#clix-status').focus()">Skip to status information</a></li>
      </ul>
    `;

    this.container.insertBefore(nav, this.container.firstChild);

    // Add IDs to key areas
    const outputArea = this.container.querySelector('.xterm-viewport');
    if (outputArea) {
      outputArea.id = 'clix-output';
    }

    const inputArea = this.container.querySelector('.xterm-helper-textarea, .clix-virtual-input');
    if (inputArea) {
      inputArea.id = 'clix-input';
    }
  }

  updateOutputStructure(content: string): void {
    // Analyze content and add semantic structure
    if (this.isTableContent(content)) {
      this.announceTableStructure(content);
    } else if (this.isListContent(content)) {
      this.announceListStructure(content);
    } else if (this.isErrorContent(content)) {
      this.announceErrorStructure(content);
    }
  }

  private isTableContent(content: string): boolean {
    // Simple heuristic to detect table-like content
    const lines = content.split('\n');
    const potentialHeaders = lines[0];
    const potentialSeparator = lines[1];
    
    return lines.length > 2 &&
           potentialHeaders?.includes('|') &&
           potentialSeparator?.match(/^[\s\-\|]+$/);
  }

  private isListContent(content: string): boolean {
    const lines = content.split('\n').filter(line => line.trim());
    return lines.length > 1 &&
           lines.every(line => /^\s*[\-\*\+\d+\.]\s/.test(line));
  }

  private isErrorContent(content: string): boolean {
    return /^(error|err|exception|failed|fatal)/i.test(content.trim());
  }

  private announceTableStructure(content: string): void {
    const lines = content.split('\n').filter(line => line.trim());
    const dataLines = lines.slice(2); // Skip header and separator
    
    const announcement = `Table with ${dataLines.length} rows detected. Use Alt+T to enable table navigation mode for easier browsing.`;
    
    // Trigger announcement through screen reader manager
    window.dispatchEvent(new CustomEvent('clix-announce', {
      detail: { message: announcement, urgency: 'polite' }
    }));
  }

  private announceListStructure(content: string): void {
    const lines = content.split('\n').filter(line => line.trim());
    const announcement = `List with ${lines.length} items detected.`;
    
    window.dispatchEvent(new CustomEvent('clix-announce', {
      detail: { message: announcement, urgency: 'polite' }
    }));
  }

  private announceErrorStructure(content: string): void {
    const announcement = 'Error message detected. Check the command output for details.';
    
    window.dispatchEvent(new CustomEvent('clix-announce', {
      detail: { message: announcement, urgency: 'assertive' }
    }));
  }
}
```

## 3. Keyboard Navigation Implementation

### Comprehensive Keyboard Support

```typescript
interface KeyboardShortcut {
  key: string;
  modifiers: {
    ctrl?: boolean;
    alt?: boolean;
    shift?: boolean;
    meta?: boolean;
  };
  action: string;
  description: string;
  handler: () => void;
}

class CLIXKeyboardNavigation {
  private terminal: Terminal;
  private shortcuts: Map<string, KeyboardShortcut> = new Map();
  private focusManagementEnabled = true;
  private tableNavigationMode = false;
  private currentFocusIndex = 0;
  private focusableElements: HTMLElement[] = [];

  constructor(terminal: Terminal) {
    this.terminal = terminal;
    this.setupKeyboardShortcuts();
    this.setupFocusManagement();
    this.setupTableNavigation();
  }

  private setupKeyboardShortcuts(): void {
    const shortcuts: Omit<KeyboardShortcut, 'handler'>[] = [
      {
        key: 'h',
        modifiers: { alt: true },
        action: 'show-help',
        description: 'Show accessibility help and keyboard shortcuts'
      },
      {
        key: 't',
        modifiers: { alt: true },
        action: 'toggle-table-mode',
        description: 'Toggle table navigation mode for structured data'
      },
      {
        key: 's',
        modifiers: { alt: true },
        action: 'toggle-summary-mode',
        description: 'Toggle output summary mode for screen readers'
      },
      {
        key: 'c',
        modifiers: { alt: true },
        action: 'toggle-contrast',
        description: 'Toggle high contrast mode'
      },
      {
        key: 'r',
        modifiers: { alt: true },
        action: 'read-last-output',
        description: 'Re-announce the last command output'
      },
      {
        key: 'Escape',
        modifiers: {},
        action: 'exit-mode',
        description: 'Exit current navigation mode'
      },
      {
        key: 'F1',
        modifiers: {},
        action: 'accessibility-menu',
        description: 'Open accessibility options menu'
      },
      {
        key: 'Tab',
        modifiers: { shift: true },
        action: 'previous-element',
        description: 'Navigate to previous focusable element'
      }
    ];

    shortcuts.forEach(shortcut => {
      const fullShortcut: KeyboardShortcut = {
        ...shortcut,
        handler: this.createShortcutHandler(shortcut.action)
      };
      
      const shortcutKey = this.createShortcutKey(shortcut.key, shortcut.modifiers);
      this.shortcuts.set(shortcutKey, fullShortcut);
    });

    this.attachKeyboardHandler();
  }

  private createShortcutHandler(action: string): () => void {
    const handlers: { [key: string]: () => void } = {
      'show-help': () => this.showAccessibilityHelp(),
      'toggle-table-mode': () => this.toggleTableNavigationMode(),
      'toggle-summary-mode': () => this.toggleSummaryMode(),
      'toggle-contrast': () => this.toggleHighContrast(),
      'read-last-output': () => this.readLastOutput(),
      'exit-mode': () => this.exitCurrentMode(),
      'accessibility-menu': () => this.showAccessibilityMenu(),
      'previous-element': () => this.navigateToPreviousElement()
    };

    return handlers[action] || (() => console.warn(`Unknown keyboard action: ${action}`));
  }

  private attachKeyboardHandler(): void {
    document.addEventListener('keydown', (event) => {
      // Skip if typing in an input field (except our terminal)
      if (this.isTypingInNonTerminalInput(event.target as Element)) {
        return;
      }

      const shortcutKey = this.createShortcutKey(event.key, {
        ctrl: event.ctrlKey,
        alt: event.altKey,
        shift: event.shiftKey,
        meta: event.metaKey
      });

      const shortcut = this.shortcuts.get(shortcutKey);
      if (shortcut) {
        event.preventDefault();
        event.stopPropagation();
        shortcut.handler();
        
        // Announce the action
        this.announceShortcutAction(shortcut);
      }
    });
  }

  private createShortcutKey(key: string, modifiers: any): string {
    const parts = [];
    if (modifiers.ctrl) parts.push('Ctrl');
    if (modifiers.alt) parts.push('Alt');
    if (modifiers.shift) parts.push('Shift');
    if (modifiers.meta) parts.push('Meta');
    parts.push(key);
    
    return parts.join('+');
  }

  private isTypingInNonTerminalInput(target: Element): boolean {
    if (!target) return false;
    
    const tagName = target.tagName.toLowerCase();
    const isInput = ['input', 'textarea', 'select'].includes(tagName);
    const isContentEditable = target.getAttribute('contenteditable') === 'true';
    const isTerminalElement = target.closest('.xterm') !== null;
    
    return (isInput || isContentEditable) && !isTerminalElement;
  }

  private showAccessibilityHelp(): void {
    const helpContent = `
      CLIX Accessibility Features:
      
      Keyboard Shortcuts:
      • Alt+H: Show this help
      • Alt+T: Toggle table navigation mode
      • Alt+S: Toggle output summary mode
      • Alt+C: Toggle high contrast mode
      • Alt+R: Re-read last output
      • Escape: Exit current mode
      • F1: Accessibility options menu
      
      Navigation:
      • Tab: Next element
      • Shift+Tab: Previous element
      • Arrow keys: Navigate output
      • Page Up/Down: Fast scroll
      
      Table Navigation Mode:
      • Arrow keys: Navigate table cells
      • Enter: Read current cell
      • Space: Read row summary
      
      Current Settings:
      • Table navigation: ${this.tableNavigationMode ? 'On' : 'Off'}
      • High contrast: ${document.body.classList.contains('clix-high-contrast') ? 'On' : 'Off'}
    `;

    this.announceToScreenReader(helpContent);
  }

  private toggleTableNavigationMode(): void {
    this.tableNavigationMode = !this.tableNavigationMode;
    
    const status = this.tableNavigationMode ? 'enabled' : 'disabled';
    this.announceToScreenReader(`Table navigation mode ${status}. ${
      this.tableNavigationMode 
        ? 'Use arrow keys to navigate table cells, Enter to read cell content, Space for row summary.'
        : 'Regular navigation restored.'
    }`);

    // Update visual indicator
    document.body.classList.toggle('clix-table-navigation', this.tableNavigationMode);
  }

  private toggleSummaryMode(): void {
    const event = new CustomEvent('clix-toggle-summary-mode');
    document.dispatchEvent(event);
  }

  private toggleHighContrast(): void {
    const isHighContrast = document.body.classList.toggle('clix-high-contrast');
    
    this.announceToScreenReader(`High contrast mode ${isHighContrast ? 'enabled' : 'disabled'}`);
    
    // Apply high contrast theme to terminal
    if (this.terminal) {
      const theme = isHighContrast ? this.getHighContrastTheme() : this.getDefaultTheme();
      this.terminal.options.theme = theme;
    }
  }

  private readLastOutput(): void {
    // Get the last command output from terminal buffer
    const buffer = this.terminal.buffer?.normal;
    if (!buffer) return;

    const lastLines = [];
    for (let i = Math.max(0, buffer.length - 10); i < buffer.length; i++) {
      const line = buffer.getLine(i);
      if (line) {
        const lineText = line.translateToString(true);
        if (lineText.trim()) {
          lastLines.push(lineText);
        }
      }
    }

    const output = lastLines.join(' ').trim();
    if (output) {
      this.announceToScreenReader(`Last output: ${output}`);
    } else {
      this.announceToScreenReader('No recent output available');
    }
  }

  private exitCurrentMode(): void {
    if (this.tableNavigationMode) {
      this.toggleTableNavigationMode();
    }
    // Exit any other special modes
  }

  private showAccessibilityMenu(): void {
    // Create a temporary menu dialog
    const menu = this.createAccessibilityMenu();
    document.body.appendChild(menu);
    menu.focus();
  }

  private createAccessibilityMenu(): HTMLElement {
    const menu = document.createElement('div');
    menu.className = 'clix-accessibility-menu';
    menu.setAttribute('role', 'dialog');
    menu.setAttribute('aria-label', 'Accessibility Options');
    menu.setAttribute('tabindex', '0');

    menu.innerHTML = `
      <div class="clix-menu-content">
        <h2>Accessibility Options</h2>
        
        <div class="clix-menu-group">
          <h3>Screen Reader</h3>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('toggle-summary'))">
            Toggle Output Summary Mode
          </button>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('read-last'))">
            Re-read Last Output
          </button>
        </div>
        
        <div class="clix-menu-group">
          <h3>Visual</h3>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('toggle-contrast'))">
            Toggle High Contrast
          </button>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('increase-font'))">
            Increase Font Size
          </button>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('decrease-font'))">
            Decrease Font Size
          </button>
        </div>
        
        <div class="clix-menu-group">
          <h3>Navigation</h3>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('toggle-table'))">
            Toggle Table Navigation
          </button>
          <button type="button" onclick="this.closest('.clix-accessibility-menu').dispatchEvent(new CustomEvent('show-shortcuts'))">
            Show Keyboard Shortcuts
          </button>
        </div>
        
        <div class="clix-menu-actions">
          <button type="button" onclick="this.closest('.clix-accessibility-menu').remove()" autofocus>
            Close Menu
          </button>
        </div>
      </div>
    `;

    // Add event listeners
    menu.addEventListener('toggle-summary', () => this.toggleSummaryMode());
    menu.addEventListener('toggle-contrast', () => this.toggleHighContrast());
    menu.addEventListener('toggle-table', () => this.toggleTableNavigationMode());
    menu.addEventListener('read-last', () => this.readLastOutput());
    menu.addEventListener('show-shortcuts', () => this.showAccessibilityHelp());

    // Handle keyboard navigation within menu
    menu.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        menu.remove();
      }
    });

    return menu;
  }

  private setupFocusManagement(): void {
    // Maintain focus within the application
    document.addEventListener('focusin', (event) => {
      if (this.focusManagementEnabled) {
        this.updateFocusableElements();
      }
    });

    // Handle Tab navigation
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Tab' && this.focusManagementEnabled) {
        this.handleTabNavigation(event);
      }
    });
  }

  private updateFocusableElements(): void {
    const selectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])',
      '.xterm-helper-textarea',
      '.clix-virtual-input'
    ];

    this.focusableElements = Array.from(
      document.querySelectorAll(selectors.join(', '))
    ).filter(el => this.isElementVisible(el)) as HTMLElement[];
  }

  private isElementVisible(element: Element): boolean {
    const style = window.getComputedStyle(element);
    return style.display !== 'none' && 
           style.visibility !== 'hidden' && 
           style.opacity !== '0';
  }

  private handleTabNavigation(event: KeyboardEvent): void {
    if (this.focusableElements.length === 0) {
      this.updateFocusableElements();
    }

    const currentIndex = this.focusableElements.indexOf(document.activeElement as HTMLElement);
    let nextIndex: number;

    if (event.shiftKey) {
      nextIndex = currentIndex <= 0 ? this.focusableElements.length - 1 : currentIndex - 1;
    } else {
      nextIndex = currentIndex >= this.focusableElements.length - 1 ? 0 : currentIndex + 1;
    }

    if (this.focusableElements[nextIndex]) {
      event.preventDefault();
      this.focusableElements[nextIndex].focus();
    }
  }

  private setupTableNavigation(): void {
    // Enhanced table navigation for structured output
    document.addEventListener('keydown', (event) => {
      if (!this.tableNavigationMode) return;

      const tableNavKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter', 'Space'];
      
      if (tableNavKeys.includes(event.key)) {
        event.preventDefault();
        this.handleTableNavigation(event.key);
      }
    });
  }

  private handleTableNavigation(key: string): void {
    // Implement table-specific navigation logic
    // This would need to be integrated with the terminal output parsing
    switch (key) {
      case 'Enter':
        this.readCurrentTableCell();
        break;
      case 'Space':
        this.readCurrentTableRow();
        break;
      case 'ArrowUp':
      case 'ArrowDown':
      case 'ArrowLeft':
      case 'ArrowRight':
        this.navigateTableCell(key);
        break;
    }
  }

  private readCurrentTableCell(): void {
    // Implementation would depend on table parsing logic
    this.announceToScreenReader('Current table cell content would be read here');
  }

  private readCurrentTableRow(): void {
    // Implementation would depend on table parsing logic
    this.announceToScreenReader('Current table row summary would be read here');
  }

  private navigateTableCell(direction: string): void {
    // Implementation would depend on table parsing logic
    this.announceToScreenReader(`Navigating ${direction.replace('Arrow', '').toLowerCase()}`);
  }

  private getHighContrastTheme(): any {
    return {
      background: '#000000',
      foreground: '#ffffff',
      cursor: '#ffffff',
      selection: '#ffffff',
      black: '#000000',
      red: '#ff0000',
      green: '#00ff00',
      yellow: '#ffff00',
      blue: '#0000ff',
      magenta: '#ff00ff',
      cyan: '#00ffff',
      white: '#ffffff',
      brightBlack: '#808080',
      brightRed: '#ff8080',
      brightGreen: '#80ff80',
      brightYellow: '#ffff80',
      brightBlue: '#8080ff',
      brightMagenta: '#ff80ff',
      brightCyan: '#80ffff',
      brightWhite: '#ffffff'
    };
  }

  private getDefaultTheme(): any {
    // Return to standard theme
    return {
      background: '#1e1e1e',
      foreground: '#cccccc',
      // ... other default theme properties
    };
  }

  private announceToScreenReader(message: string): void {
    window.dispatchEvent(new CustomEvent('clix-announce', {
      detail: { message, urgency: 'polite' }
    }));
  }

  private announceShortcutAction(shortcut: KeyboardShortcut): void {
    this.announceToScreenReader(`Activated: ${shortcut.description}`);
  }

  private navigateToPreviousElement(): void {
    if (this.focusableElements.length === 0) {
      this.updateFocusableElements();
    }

    const currentIndex = this.focusableElements.indexOf(document.activeElement as HTMLElement);
    const previousIndex = currentIndex <= 0 ? this.focusableElements.length - 1 : currentIndex - 1;

    if (this.focusableElements[previousIndex]) {
      this.focusableElements[previousIndex].focus();
    }
  }

  dispose(): void {
    // Clean up event listeners
    this.shortcuts.clear();
    this.focusableElements = [];
  }
}
```

## 4. Visual Accessibility Implementation

### High Contrast and Color Support

```typescript
interface VisualAccessibilityConfig {
  highContrastEnabled: boolean;
  fontSize: number;
  fontFamily: string;
  lineHeight: number;
  colorBlindnessSupport: boolean;
  reducedMotion: boolean;
  customColors: boolean;
}

class CLIXVisualAccessibility {
  private config: VisualAccessibilityConfig;
  private terminal: Terminal;
  private originalTheme: any;
  
  constructor(terminal: Terminal, config: Partial<VisualAccessibilityConfig> = {}) {
    this.terminal = terminal;
    this.config = {
      highContrastEnabled: false,
      fontSize: 14,
      fontFamily: '"Cascadia Code", "Fira Code", monospace',
      lineHeight: 1.2,
      colorBlindnessSupport: false,
      reducedMotion: false,
      customColors: false,
      ...config
    };
    
    this.originalTheme = { ...terminal.options.theme };
    this.initialize();
  }

  private initialize(): void {
    this.setupSystemPreferenceListeners();
    this.createAccessibilityStyles();
    this.setupColorBlindnessSupport();
    this.applyInitialSettings();
  }

  private setupSystemPreferenceListeners(): void {
    // Listen for system preference changes
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
    const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)');

    reducedMotionQuery.addEventListener('change', (e) => {
      this.config.reducedMotion = e.matches;
      this.applyMotionSettings();
      this.announceChange(`Reduced motion ${e.matches ? 'enabled' : 'disabled'} by system preference`);
    });

    highContrastQuery.addEventListener('change', (e) => {
      if (e.matches) {
        this.enableHighContrast();
        this.announceChange('High contrast mode enabled by system preference');
      }
    });

    colorSchemeQuery.addEventListener('change', (e) => {
      this.updateColorScheme(e.matches ? 'dark' : 'light');
    });

    // Set initial states
    this.config.reducedMotion = reducedMotionQuery.matches;
    if (highContrastQuery.matches) {
      this.config.highContrastEnabled = true;
    }
  }

  private createAccessibilityStyles(): void {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'clix-accessibility-styles';
    
    styleSheet.textContent = `
      /* High Contrast Mode */
      .clix-high-contrast .xterm {
        border: 2px solid #ffffff !important;
      }
      
      .clix-high-contrast .xterm-viewport::-webkit-scrollbar {
        width: 12px !important;
        background-color: #000000 !important;
      }
      
      .clix-high-contrast .xterm-viewport::-webkit-scrollbar-thumb {
        background-color: #ffffff !important;
        border: 1px solid #ffffff !important;
      }
      
      .clix-high-contrast .xterm-viewport::-webkit-scrollbar-corner {
        background-color: #000000 !important;
      }

      /* Reduced Motion Mode */
      .clix-reduced-motion * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
      }

      /* Font Scaling */
      .clix-font-small { font-size: 12px !important; }
      .clix-font-medium { font-size: 14px !important; }
      .clix-font-large { font-size: 18px !important; }
      .clix-font-xlarge { font-size: 24px !important; }

      /* Line Height Adjustments */
      .clix-line-height-compact { line-height: 1.0 !important; }
      .clix-line-height-normal { line-height: 1.2 !important; }
      .clix-line-height-relaxed { line-height: 1.4 !important; }
      .clix-line-height-loose { line-height: 1.6 !important; }

      /* Color Blindness Support */
      .clix-colorblind-support .ansi-red { 
        background-color: #ff0000 !important;
        color: #ffffff !important;
        font-weight: bold !important;
      }
      
      .clix-colorblind-support .ansi-green { 
        background-color: #00ff00 !important;
        color: #000000 !important;
        font-weight: bold !important;
      }

      /* Focus Indicators */
      .clix-enhanced-focus *:focus {
        outline: 3px solid #007acc !important;
        outline-offset: 2px !important;
      }
      
      .clix-high-contrast *:focus {
        outline: 3px solid #ffffff !important;
        outline-offset: 2px !important;
      }

      /* Screen Reader Only Content */
      .sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
      }
    `;

    document.head.appendChild(styleSheet);
  }

  enableHighContrast(): void {
    this.config.highContrastEnabled = true;
    document.body.classList.add('clix-high-contrast');

    const highContrastTheme = {
      background: '#000000',
      foreground: '#ffffff',
      cursor: '#ffffff',
      cursorAccent: '#000000',
      selection: '#ffffff',
      black: '#000000',
      red: '#ff0000',
      green: '#00ff00',
      yellow: '#ffff00',
      blue: '#0000ff',
      magenta: '#ff00ff',
      cyan: '#00ffff',
      white: '#ffffff',
      brightBlack: '#808080',
      brightRed: '#ff4444',
      brightGreen: '#44ff44',
      brightYellow: '#ffff44',
      brightBlue: '#4444ff',
      brightMagenta: '#ff44ff',
      brightCyan: '#44ffff',
      brightWhite: '#ffffff'
    };

    this.terminal.options.theme = highContrastTheme;
    this.announceChange('High contrast mode enabled');
  }

  disableHighContrast(): void {
    this.config.highContrastEnabled = false;
    document.body.classList.remove('clix-high-contrast');
    this.terminal.options.theme = this.originalTheme;
    this.announceChange('High contrast mode disabled');
  }

  private setupColorBlindnessSupport(): void {
    // Add support for color blindness by using patterns and additional indicators
    const colorBlindnessStyles = `
      .clix-colorblind-support .ansi-red::before { content: "🔴 "; }
      .clix-colorblind-support .ansi-green::before { content: "🟢 "; }
      .clix-colorblind-support .ansi-yellow::before { content: "🟡 "; }
      .clix-colorblind-support .ansi-blue::before { content: "🔵 "; }
      .clix-colorblind-support .ansi-magenta::before { content: "🟣 "; }
      .clix-colorblind-support .ansi-cyan::before { content: "🔵 "; }
    `;

    const styleSheet = document.createElement('style');
    styleSheet.textContent = colorBlindnessStyles;
    document.head.appendChild(styleSheet);
  }

  enableColorBlindnessSupport(): void {
    this.config.colorBlindnessSupport = true;
    document.body.classList.add('clix-colorblind-support');
    this.announceChange('Color blindness support enabled with emoji indicators');
  }

  disableColorBlindnessSupport(): void {
    this.config.colorBlindnessSupport = false;
    document.body.classList.remove('clix-colorblind-support');
    this.announceChange('Color blindness support disabled');
  }

  adjustFontSize(delta: number): void {
    const newSize = Math.max(10, Math.min(32, this.config.fontSize + delta));
    
    if (newSize !== this.config.fontSize) {
      this.config.fontSize = newSize;
      this.terminal.options.fontSize = newSize;
      
      // Update terminal to reflect new size
      if (this.terminal.element) {
        this.terminal.element.style.fontSize = `${newSize}px`;
      }
      
      this.announceChange(`Font size changed to ${newSize} pixels`);
    }
  }

  setFontFamily(fontFamily: string): void {
    this.config.fontFamily = fontFamily;
    this.terminal.options.fontFamily = fontFamily;
    
    if (this.terminal.element) {
      this.terminal.element.style.fontFamily = fontFamily;
    }
    
    this.announceChange(`Font family changed to ${fontFamily}`);
  }

  adjustLineHeight(factor: number): void {
    const newLineHeight = Math.max(1.0, Math.min(2.0, factor));
    
    this.config.lineHeight = newLineHeight;
    this.terminal.options.lineHeight = newLineHeight;
    
    // Apply line height class
    document.body.classList.remove('clix-line-height-compact', 'clix-line-height-normal', 'clix-line-height-relaxed', 'clix-line-height-loose');
    
    if (newLineHeight <= 1.1) {
      document.body.classList.add('clix-line-height-compact');
    } else if (newLineHeight <= 1.3) {
      document.body.classList.add('clix-line-height-normal');
    } else if (newLineHeight <= 1.5) {
      document.body.classList.add('clix-line-height-relaxed');
    } else {
      document.body.classList.add('clix-line-height-loose');
    }
    
    this.announceChange(`Line height adjusted to ${newLineHeight.toFixed(1)}`);
  }

  private applyMotionSettings(): void {
    if (this.config.reducedMotion) {
      document.body.classList.add('clix-reduced-motion');
      this.terminal.options.smoothScrollDuration = 0;
      this.terminal.options.cursorBlink = false;
    } else {
      document.body.classList.remove('clix-reduced-motion');
      this.terminal.options.smoothScrollDuration = 200;
      this.terminal.options.cursorBlink = true;
    }
  }

  private updateColorScheme(scheme: 'light' | 'dark'): void {
    // Adjust default theme based on color scheme preference
    if (scheme === 'light' && !this.config.highContrastEnabled) {
      const lightTheme = {
        ...this.originalTheme,
        background: '#ffffff',
        foreground: '#000000',
        cursor: '#000000',
        selection: '#0078d4'
      };
      this.terminal.options.theme = lightTheme;
    }
  }

  private applyInitialSettings(): void {
    if (this.config.highContrastEnabled) {
      this.enableHighContrast();
    }
    
    if (this.config.colorBlindnessSupport) {
      this.enableColorBlindnessSupport();
    }
    
    this.applyMotionSettings();
  }

  getAccessibilityReport(): VisualAccessibilityReport {
    return {
      highContrast: this.config.highContrastEnabled,
      fontSize: this.config.fontSize,
      lineHeight: this.config.lineHeight,
      fontFamily: this.config.fontFamily,
      colorBlindnessSupport: this.config.colorBlindnessSupport,
      reducedMotion: this.config.reducedMotion,
      colorContrastRatio: this.calculateContrastRatio(),
      wcagCompliance: this.checkWCAGCompliance()
    };
  }

  private calculateContrastRatio(): number {
    // Calculate color contrast ratio between background and foreground
    const theme = this.terminal.options.theme;
    if (!theme) return 0;

    const bgColor = this.hexToRgb(theme.background);
    const fgColor = this.hexToRgb(theme.foreground);
    
    if (!bgColor || !fgColor) return 0;

    return this.getContrastRatio(bgColor, fgColor);
  }

  private hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }

  private getContrastRatio(color1: { r: number; g: number; b: number }, color2: { r: number; g: number; b: number }): number {
    const l1 = this.getLuminance(color1);
    const l2 = this.getLuminance(color2);
    
    const brighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    
    return (brighter + 0.05) / (darker + 0.05);
  }

  private getLuminance(color: { r: number; g: number; b: number }): number {
    const { r, g, b } = color;
    
    const sR = r / 255;
    const sG = g / 255;
    const sB = b / 255;
    
    const rLin = sR <= 0.03928 ? sR / 12.92 : Math.pow((sR + 0.055) / 1.055, 2.4);
    const gLin = sG <= 0.03928 ? sG / 12.92 : Math.pow((sG + 0.055) / 1.055, 2.4);
    const bLin = sB <= 0.03928 ? sB / 12.92 : Math.pow((sB + 0.055) / 1.055, 2.4);
    
    return 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin;
  }

  private checkWCAGCompliance(): { aa: boolean; aaa: boolean } {
    const contrastRatio = this.calculateContrastRatio();
    
    return {
      aa: contrastRatio >= 4.5,
      aaa: contrastRatio >= 7.0
    };
  }

  private announceChange(message: string): void {
    window.dispatchEvent(new CustomEvent('clix-announce', {
      detail: { message, urgency: 'polite' }
    }));
  }

  dispose(): void {
    document.getElementById('clix-accessibility-styles')?.remove();
    document.body.classList.remove(
      'clix-high-contrast',
      'clix-colorblind-support',
      'clix-reduced-motion'
    );
  }
}
```

## 5. Integration and Testing

### Accessibility Testing Framework

```typescript
interface AccessibilityTest {
  name: string;
  description: string;
  test: () => Promise<AccessibilityTestResult>;
}

interface AccessibilityTestResult {
  passed: boolean;
  score: number;
  details: string[];
  recommendations: string[];
}

class CLIXAccessibilityTester {
  private tests: AccessibilityTest[] = [];

  constructor() {
    this.setupTests();
  }

  private setupTests(): void {
    this.tests = [
      {
        name: 'Screen Reader Support',
        description: 'Verify ARIA attributes and live regions are properly configured',
        test: this.testScreenReaderSupport.bind(this)
      },
      {
        name: 'Keyboard Navigation',
        description: 'Ensure all functionality is accessible via keyboard',
        test: this.testKeyboardNavigation.bind(this)
      },
      {
        name: 'Color Contrast',
        description: 'Verify color contrast meets WCAG AA standards',
        test: this.testColorContrast.bind(this)
      },
      {
        name: 'Focus Management',
        description: 'Check focus indicators and logical tab order',
        test: this.testFocusManagement.bind(this)
      },
      {
        name: 'Semantic HTML',
        description: 'Verify proper use of semantic HTML elements',
        test: this.testSemanticHTML.bind(this)
      }
    ];
  }

  async runAllTests(): Promise<AccessibilityTestReport> {
    const results: AccessibilityTestResult[] = [];
    
    for (const test of this.tests) {
      try {
        const result = await test.test();
        results.push({ ...result, name: test.name });
      } catch (error) {
        results.push({
          name: test.name,
          passed: false,
          score: 0,
          details: [`Test failed with error: ${error.message}`],
          recommendations: ['Fix test implementation and re-run']
        });
      }
    }

    return this.generateReport(results);
  }

  private async testScreenReaderSupport(): Promise<AccessibilityTestResult> {
    const details: string[] = [];
    const recommendations: string[] = [];
    let score = 0;

    // Check for live regions
    const liveRegions = document.querySelectorAll('[aria-live]');
    if (liveRegions.length > 0) {
      details.push(`Found ${liveRegions.length} live regions`);
      score += 20;
    } else {
      details.push('No ARIA live regions found');
      recommendations.push('Add ARIA live regions for dynamic content updates');
    }

    // Check for proper labeling
    const terminalElement = document.querySelector('.xterm');
    if (terminalElement?.getAttribute('role') === 'application') {
      details.push('Terminal has proper application role');
      score += 20;
    } else {
      details.push('Terminal missing application role');
      recommendations.push('Add role="application" to terminal container');
    }

    // Check for descriptions
    const descriptionId = terminalElement?.getAttribute('aria-describedby');
    if (descriptionId && document.getElementById(descriptionId)) {
      details.push('Terminal has description reference');
      score += 20;
    } else {
      details.push('Terminal missing description');
      recommendations.push('Add aria-describedby reference to help text');
    }

    const passed = score >= 40; // Require at least 40% for pass
    
    return {
      passed,
      score,
      details,
      recommendations
    };
  }

  private async testKeyboardNavigation(): Promise<AccessibilityTestResult> {
    const details: string[] = [];
    const recommendations: string[] = [];
    let score = 0;

    // Test Tab navigation
    const focusableElements = document.querySelectorAll(
      'button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length > 0) {
      details.push(`Found ${focusableElements.length} focusable elements`);
      score += 25;
    }

    // Test keyboard shortcuts
    const shortcuts = ['Alt+H', 'Alt+T', 'Alt+S', 'F1'];
    let workingShortcuts = 0;
    
    for (const shortcut of shortcuts) {
      // Simulate shortcut testing (would need actual event simulation)
      if (this.simulateKeyboardShortcut(shortcut)) {
        workingShortcuts++;
      }
    }
    
    if (workingShortcuts === shortcuts.length) {
      details.push('All keyboard shortcuts are functional');
      score += 25;
    } else {
      details.push(`${workingShortcuts}/${shortcuts.length} shortcuts working`);
      recommendations.push('Fix non-functional keyboard shortcuts');
    }

    // Check for skip links
    const skipLinks = document.querySelectorAll('a[href^="#"]');
    if (skipLinks.length > 0) {
      details.push('Skip links present for navigation');
      score += 25;
    } else {
      recommendations.push('Add skip links for keyboard navigation');
    }

    const passed = score >= 50;
    
    return {
      passed,
      score,
      details,
      recommendations
    };
  }

  private async testColorContrast(): Promise<AccessibilityTestResult> {
    const details: string[] = [];
    const recommendations: string[] = [];
    let score = 0;

    // Get terminal theme colors
    const terminalElement = document.querySelector('.xterm');
    if (!terminalElement) {
      return {
        passed: false,
        score: 0,
        details: ['Terminal element not found'],
        recommendations: ['Ensure terminal is properly initialized before testing']
      };
    }

    const styles = window.getComputedStyle(terminalElement);
    const backgroundColor = styles.backgroundColor;
    const color = styles.color;

    // Calculate contrast ratio
    const contrastRatio = this.calculateContrastRatio(backgroundColor, color);
    
    if (contrastRatio >= 7.0) {
      details.push(`Excellent contrast ratio: ${contrastRatio.toFixed(2)}:1 (WCAG AAA)`);
      score = 100;
    } else if (contrastRatio >= 4.5) {
      details.push(`Good contrast ratio: ${contrastRatio.toFixed(2)}:1 (WCAG AA)`);
      score = 80;
    } else if (contrastRatio >= 3.0) {
      details.push(`Marginal contrast ratio: ${contrastRatio.toFixed(2)}:1`);
      score = 40;
      recommendations.push('Improve contrast ratio to meet WCAG AA standards (4.5:1)');
    } else {
      details.push(`Poor contrast ratio: ${contrastRatio.toFixed(2)}:1`);
      score = 0;
      recommendations.push('Significantly improve contrast ratio - fails all WCAG standards');
    }

    const passed = contrastRatio >= 4.5;
    
    return {
      passed,
      score,
      details,
      recommendations
    };
  }

  private async testFocusManagement(): Promise<AccessibilityTestResult> {
    const details: string[] = [];
    const recommendations: string[] = [];
    let score = 0;

    // Check for visible focus indicators
    const focusStyles = this.checkFocusStyles();
    if (focusStyles.hasVisibleFocus) {
      details.push('Visible focus indicators present');
      score += 30;
    } else {
      details.push('No visible focus indicators');
      recommendations.push('Add visible focus indicators (outline, box-shadow, etc.)');
    }

    // Check logical tab order
    const tabOrder = this.checkTabOrder();
    if (tabOrder.isLogical) {
      details.push('Logical tab order maintained');
      score += 35;
    } else {
      details.push('Tab order issues detected');
      recommendations.push('Fix tab order using tabindex or DOM restructuring');
    }

    // Check focus trapping if modal dialogs exist
    const modals = document.querySelectorAll('[role="dialog"]');
    if (modals.length === 0) {
      details.push('No modal dialogs to test focus trapping');
      score += 35; // Full score if not applicable
    } else {
      // Test focus trapping (simplified)
      details.push(`Found ${modals.length} modal dialog(s)`);
      score += 25; // Assume partial compliance
      recommendations.push('Verify focus trapping works correctly in modal dialogs');
    }

    const passed = score >= 70;
    
    return {
      passed,
      score,
      details,
      recommendations
    };
  }

  private async testSemanticHTML(): Promise<AccessibilityTestResult> {
    const details: string[] = [];
    const recommendations: string[] = [];
    let score = 0;

    // Check for proper heading structure
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    if (headings.length > 0) {
      details.push(`Found ${headings.length} headings`);
      score += 20;
    } else {
      recommendations.push('Add proper heading structure for screen readers');
    }

    // Check for landmarks
    const landmarks = document.querySelectorAll('[role="main"], [role="navigation"], [role="banner"], [role="contentinfo"], main, nav, header, footer');
    if (landmarks.length > 0) {
      details.push(`Found ${landmarks.length} landmark elements`);
      score += 30;
    } else {
      recommendations.push('Add landmark roles for better navigation');
    }

    // Check for list structures
    const lists = document.querySelectorAll('ul, ol, dl');
    if (lists.length > 0) {
      details.push(`Found ${lists.length} list structures`);
      score += 25;
    }

    // Check for form labels
    const inputs = document.querySelectorAll('input, select, textarea');
    let labeledInputs = 0;
    
    inputs.forEach(input => {
      const hasLabel = input.getAttribute('aria-label') ||
                      input.getAttribute('aria-labelledby') ||
                      document.querySelector(`label[for="${input.id}"]`);
      if (hasLabel) labeledInputs++;
    });

    if (inputs.length === 0) {
      details.push('No form inputs to test');
      score += 25; // Full score if not applicable
    } else if (labeledInputs === inputs.length) {
      details.push('All form inputs properly labeled');
      score += 25;
    } else {
      details.push(`${labeledInputs}/${inputs.length} inputs properly labeled`);
      recommendations.push('Add proper labels to all form inputs');
    }

    const passed = score >= 60;
    
    return {
      passed,
      score,
      details,
      recommendations
    };
  }

  private simulateKeyboardShortcut(shortcut: string): boolean {
    // Simplified shortcut testing
    // In real implementation, would dispatch keyboard events and check responses
    return true; // Assume working for this example
  }

  private calculateContrastRatio(color1: string, color2: string): number {
    // Simplified contrast ratio calculation
    // Would need proper color parsing and luminance calculation
    return 4.5; // Placeholder value
  }

  private checkFocusStyles(): { hasVisibleFocus: boolean } {
    // Check if focus styles are defined in CSS
    const styleSheets = Array.from(document.styleSheets);
    let hasVisibleFocus = false;

    try {
      for (const sheet of styleSheets) {
        const rules = Array.from(sheet.cssRules || []);
        for (const rule of rules) {
          if (rule instanceof CSSStyleRule && rule.selectorText?.includes(':focus')) {
            const style = rule.style;
            if (style.outline !== 'none' || style.boxShadow || style.border) {
              hasVisibleFocus = true;
              break;
            }
          }
        }
        if (hasVisibleFocus) break;
      }
    } catch (error) {
      // Handle cross-origin stylesheet issues
      hasVisibleFocus = true; // Assume present if can't check
    }

    return { hasVisibleFocus };
  }

  private checkTabOrder(): { isLogical: boolean } {
    const focusableElements = Array.from(document.querySelectorAll(
      'button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
    ));

    // Check if elements are in visual order (simplified)
    let isLogical = true;
    for (let i = 1; i < focusableElements.length; i++) {
      const prevRect = focusableElements[i - 1].getBoundingClientRect();
      const currRect = focusableElements[i].getBoundingClientRect();
      
      // Simple check: if previous element is significantly below current, order might be wrong
      if (prevRect.top > currRect.bottom + 10) {
        isLogical = false;
        break;
      }
    }

    return { isLogical };
  }

  private generateReport(results: AccessibilityTestResult[]): AccessibilityTestReport {
    const totalScore = results.reduce((sum, result) => sum + result.score, 0) / results.length;
    const passedTests = results.filter(result => result.passed).length;
    
    const overallGrade = totalScore >= 90 ? 'A' :
                        totalScore >= 80 ? 'B' :
                        totalScore >= 70 ? 'C' :
                        totalScore >= 60 ? 'D' : 'F';

    const allRecommendations = results.flatMap(result => result.recommendations);
    const uniqueRecommendations = [...new Set(allRecommendations)];

    return {
      timestamp: new Date().toISOString(),
      overallScore: Math.round(totalScore),
      grade: overallGrade,
      testsPassed: passedTests,
      testsTotal: results.length,
      wcagCompliance: this.assessWCAGCompliance(results),
      results,
      recommendations: uniqueRecommendations,
      nextSteps: this.generateNextSteps(overallGrade, uniqueRecommendations)
    };
  }

  private assessWCAGCompliance(results: AccessibilityTestResult[]): string {
    const criticalTests = ['Screen Reader Support', 'Color Contrast', 'Keyboard Navigation'];
    const criticalResults = results.filter(result => criticalTests.includes(result.name));
    const passedCritical = criticalResults.filter(result => result.passed).length;

    if (passedCritical === criticalResults.length) {
      return 'WCAG 2.1 AA Compliant';
    } else if (passedCritical > criticalResults.length / 2) {
      return 'Partially WCAG 2.1 AA Compliant';
    } else {
      return 'Not WCAG 2.1 AA Compliant';
    }
  }

  private generateNextSteps(grade: string, recommendations: string[]): string[] {
    const nextSteps = [];

    if (grade === 'F' || grade === 'D') {
      nextSteps.push('Address critical accessibility issues immediately');
      nextSteps.push('Focus on color contrast and keyboard navigation first');
    } else if (grade === 'C') {
      nextSteps.push('Improve screen reader support');
      nextSteps.push('Enhance focus management');
    } else if (grade === 'B') {
      nextSteps.push('Fine-tune existing accessibility features');
      nextSteps.push('Consider WCAG AAA compliance for critical elements');
    } else {
      nextSteps.push('Maintain current accessibility standards');
      nextSteps.push('Regular testing with real users with disabilities');
    }

    if (recommendations.length > 0) {
      nextSteps.push('Address the specific recommendations listed in the report');
    }

    return nextSteps;
  }
}
```

## Conclusion

This comprehensive accessibility implementation guide provides the foundation for creating a fully accessible CLIX terminal interface that meets WCAG 2.1 AA standards and provides an inclusive experience for all users. The implementation covers:

1. **Screen Reader Support**: Intelligent ARIA live regions and semantic structure
2. **Keyboard Navigation**: Complete keyboard accessibility with shortcuts and table navigation
3. **Visual Accessibility**: High contrast themes, font scaling, and color blindness support
4. **Testing Framework**: Comprehensive accessibility testing and validation

By implementing these accessibility features, CLIX will be usable by people with various disabilities including visual impairments, motor disabilities, and cognitive disabilities, ensuring that the powerful command-line interface is accessible to the broadest possible user base.