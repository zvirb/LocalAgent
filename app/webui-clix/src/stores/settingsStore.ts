import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// Types
export type CursorStyle = 'block' | 'underline' | 'bar';
export type FontWeight = 'normal' | 'bold' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900';
export type ScrollbackMode = 'lines' | 'memory';

export interface SettingsState {
  // Terminal appearance
  fontSize: number;
  fontFamily: string;
  fontWeight: FontWeight;
  lineHeight: number;
  letterSpacing: number;
  cursorStyle: CursorStyle;
  cursorBlink: boolean;
  theme: string;
  
  // Terminal behavior
  scrollback: number;
  scrollbackMode: ScrollbackMode;
  scrollSensitivity: number;
  fastScrollModifier: 'alt' | 'shift' | 'ctrl';
  rightClickSelectsWord: boolean;
  copyOnSelect: boolean;
  pasteOnRightClick: boolean;
  
  // Audio
  bellSound: boolean;
  bellVolume: number;
  
  // WebGL and performance
  webglEnabled: boolean;
  rendererType: 'auto' | 'webgl' | 'canvas' | 'dom';
  maxFps: number;
  enableLigatures: boolean;
  
  // Keyboard
  altClickMovesCursor: boolean;
  altIsMeta: boolean;
  sendKeysToTerminal: boolean;
  
  // Mouse
  mouseWheelScrollSpeed: number;
  middleClickPaste: boolean;
  
  // Advanced
  allowProposedApi: boolean;
  screenReaderMode: boolean;
  allowTransparency: boolean;
  macOptionIsMeta: boolean;
  windowsMode: boolean;
  
  // Collaboration
  showOtherCursors: boolean;
  collaborationSound: boolean;
  participantNotifications: boolean;
  
  // Recording
  autoRecord: boolean;
  recordingFormat: 'asciinema' | 'json' | 'mp4';
  maxRecordingSize: number; // MB
  
  // File operations
  maxUploadSize: number; // MB
  allowedUploadTypes: string[];
  downloadLocation: 'default' | 'ask' | 'custom';
  customDownloadPath: string;
  
  // Accessibility
  highContrastMode: boolean;
  largeText: boolean;
  reduceAnimations: boolean;
  screenReaderSupport: boolean;
  keyboardNavigation: boolean;
  
  // Developer
  devMode: boolean;
  showPerformanceMetrics: boolean;
  debugLogging: boolean;
  enableExperimentalFeatures: boolean;
  
  // Actions
  updateSetting: <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => void;
  updateMultipleSettings: (settings: Partial<SettingsState>) => void;
  resetToDefaults: () => void;
  resetCategory: (category: 'appearance' | 'behavior' | 'performance' | 'accessibility' | 'advanced') => void;
  exportSettings: () => string;
  importSettings: (settingsJson: string) => boolean;
  getSettingsByCategory: (category: string) => Record<string, any>;
}

// Default settings
const defaultSettings: Omit<SettingsState, 'updateSetting' | 'updateMultipleSettings' | 'resetToDefaults' | 'resetCategory' | 'exportSettings' | 'importSettings' | 'getSettingsByCategory'> = {
  // Terminal appearance
  fontSize: 14,
  fontFamily: 'JetBrains Mono, Fira Code, Cascadia Code, Monaco, Consolas, monospace',
  fontWeight: 'normal',
  lineHeight: 1.4,
  letterSpacing: 0,
  cursorStyle: 'block',
  cursorBlink: true,
  theme: 'dark',
  
  // Terminal behavior
  scrollback: 10000,
  scrollbackMode: 'lines',
  scrollSensitivity: 1,
  fastScrollModifier: 'alt',
  rightClickSelectsWord: true,
  copyOnSelect: false,
  pasteOnRightClick: true,
  
  // Audio
  bellSound: false,
  bellVolume: 0.5,
  
  // WebGL and performance
  webglEnabled: true,
  rendererType: 'auto',
  maxFps: 60,
  enableLigatures: true,
  
  // Keyboard
  altClickMovesCursor: true,
  altIsMeta: false,
  sendKeysToTerminal: true,
  
  // Mouse
  mouseWheelScrollSpeed: 1,
  middleClickPaste: true,
  
  // Advanced
  allowProposedApi: true,
  screenReaderMode: false,
  allowTransparency: false,
  macOptionIsMeta: true,
  windowsMode: false,
  
  // Collaboration
  showOtherCursors: true,
  collaborationSound: true,
  participantNotifications: true,
  
  // Recording
  autoRecord: false,
  recordingFormat: 'asciinema',
  maxRecordingSize: 100,
  
  // File operations
  maxUploadSize: 100,
  allowedUploadTypes: ['*'],
  downloadLocation: 'default',
  customDownloadPath: '',
  
  // Accessibility
  highContrastMode: false,
  largeText: false,
  reduceAnimations: false,
  screenReaderSupport: false,
  keyboardNavigation: true,
  
  // Developer
  devMode: false,
  showPerformanceMetrics: false,
  debugLogging: false,
  enableExperimentalFeatures: false,
};

// Setting categories for organization
export const settingCategories = {
  appearance: [
    'fontSize', 'fontFamily', 'fontWeight', 'lineHeight', 'letterSpacing',
    'cursorStyle', 'cursorBlink', 'theme', 'enableLigatures'
  ],
  behavior: [
    'scrollback', 'scrollbackMode', 'scrollSensitivity', 'fastScrollModifier',
    'rightClickSelectsWord', 'copyOnSelect', 'pasteOnRightClick', 'altClickMovesCursor',
    'altIsMeta', 'mouseWheelScrollSpeed', 'middleClickPaste'
  ],
  performance: [
    'webglEnabled', 'rendererType', 'maxFps', 'allowProposedApi'
  ],
  accessibility: [
    'highContrastMode', 'largeText', 'reduceAnimations', 'screenReaderSupport',
    'screenReaderMode', 'keyboardNavigation'
  ],
  audio: [
    'bellSound', 'bellVolume', 'collaborationSound'
  ],
  collaboration: [
    'showOtherCursors', 'participantNotifications'
  ],
  recording: [
    'autoRecord', 'recordingFormat', 'maxRecordingSize'
  ],
  files: [
    'maxUploadSize', 'allowedUploadTypes', 'downloadLocation', 'customDownloadPath'
  ],
  advanced: [
    'allowTransparency', 'macOptionIsMeta', 'windowsMode', 'sendKeysToTerminal'
  ],
  developer: [
    'devMode', 'showPerformanceMetrics', 'debugLogging', 'enableExperimentalFeatures'
  ]
};

// Validation rules
const validationRules = {
  fontSize: { min: 8, max: 36 },
  fontWeight: ['normal', 'bold', '100', '200', '300', '400', '500', '600', '700', '800', '900'],
  lineHeight: { min: 0.5, max: 3.0 },
  letterSpacing: { min: -5, max: 5 },
  cursorStyle: ['block', 'underline', 'bar'],
  scrollback: { min: 0, max: 1000000 },
  scrollSensitivity: { min: 0.1, max: 10 },
  bellVolume: { min: 0, max: 1 },
  maxFps: { min: 10, max: 144 },
  mouseWheelScrollSpeed: { min: 0.1, max: 10 },
  maxRecordingSize: { min: 1, max: 10000 },
  maxUploadSize: { min: 1, max: 10000 }
};

// Validation function
function validateSetting<K extends keyof SettingsState>(key: K, value: SettingsState[K]): boolean {
  const rule = validationRules[key as keyof typeof validationRules];
  
  if (!rule) return true;
  
  if (Array.isArray(rule)) {
    return rule.includes(value as any);
  }
  
  if (typeof rule === 'object' && 'min' in rule && 'max' in rule) {
    const numValue = value as number;
    return numValue >= rule.min && numValue <= rule.max;
  }
  
  return true;
}

// Store implementation
export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set, get) => ({
        ...defaultSettings,

        updateSetting: <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
          // Validate setting value
          if (!validateSetting(key, value)) {
            console.warn(`Invalid value for setting ${String(key)}:`, value);
            return;
          }
          
          set({ [key]: value }, false, `updateSetting.${String(key)}`);
          
          // Trigger side effects for specific settings
          handleSettingChange(key, value);
        },

        updateMultipleSettings: (settings: Partial<SettingsState>) => {
          // Validate all settings
          const validatedSettings: Partial<SettingsState> = {};
          
          for (const [key, value] of Object.entries(settings)) {
            if (validateSetting(key as keyof SettingsState, value)) {
              validatedSettings[key as keyof SettingsState] = value;
            } else {
              console.warn(`Invalid value for setting ${key}:`, value);
            }
          }
          
          set(validatedSettings, false, 'updateMultipleSettings');
          
          // Trigger side effects
          Object.entries(validatedSettings).forEach(([key, value]) => {
            handleSettingChange(key as keyof SettingsState, value);
          });
        },

        resetToDefaults: () => {
          set(defaultSettings, false, 'resetToDefaults');
          
          // Apply defaults to document
          if (typeof document !== 'undefined') {
            document.documentElement.style.fontSize = `${defaultSettings.fontSize}px`;
          }
        },

        resetCategory: (category: keyof typeof settingCategories) => {
          const categorySettings = settingCategories[category];
          const resetValues: Partial<SettingsState> = {};
          
          categorySettings.forEach(settingKey => {
            const key = settingKey as keyof SettingsState;
            resetValues[key] = defaultSettings[key];
          });
          
          set(resetValues, false, `resetCategory.${category}`);
        },

        exportSettings: () => {
          const state = get();
          const exportableSettings = { ...state };
          
          // Remove functions from export
          delete (exportableSettings as any).updateSetting;
          delete (exportableSettings as any).updateMultipleSettings;
          delete (exportableSettings as any).resetToDefaults;
          delete (exportableSettings as any).resetCategory;
          delete (exportableSettings as any).exportSettings;
          delete (exportableSettings as any).importSettings;
          delete (exportableSettings as any).getSettingsByCategory;
          
          return JSON.stringify(exportableSettings, null, 2);
        },

        importSettings: (settingsJson: string): boolean => {
          try {
            const settings = JSON.parse(settingsJson);
            
            // Validate imported settings
            const validSettings: Partial<SettingsState> = {};
            
            for (const [key, value] of Object.entries(settings)) {
              if (key in defaultSettings && validateSetting(key as keyof SettingsState, value)) {
                validSettings[key as keyof SettingsState] = value;
              }
            }
            
            set(validSettings, false, 'importSettings');
            return true;
          } catch (error) {
            console.error('Failed to import settings:', error);
            return false;
          }
        },

        getSettingsByCategory: (category: string) => {
          const state = get();
          const categoryKeys = settingCategories[category as keyof typeof settingCategories] || [];
          const categorySettings: Record<string, any> = {};
          
          categoryKeys.forEach(key => {
            categorySettings[key] = state[key as keyof SettingsState];
          });
          
          return categorySettings;
        },
      }),
      {
        name: 'settings-store',
        version: 1,
        migrate: (persistedState: any, version: number) => {
          // Handle settings migration between versions
          if (version < 1) {
            // Migration logic for version 1
            return { ...defaultSettings, ...persistedState };
          }
          return persistedState;
        }
      }
    ),
    { name: 'settings-store' }
  )
);

// Side effect handler for setting changes
function handleSettingChange<K extends keyof SettingsState>(key: K, value: SettingsState[K]) {
  if (typeof document === 'undefined') return;
  
  switch (key) {
    case 'fontSize':
      document.documentElement.style.setProperty('--terminal-font-size', `${value}px`);
      break;
      
    case 'fontFamily':
      document.documentElement.style.setProperty('--terminal-font-family', value as string);
      break;
      
    case 'highContrastMode':
      document.documentElement.setAttribute('data-high-contrast', String(value));
      break;
      
    case 'reduceAnimations':
      document.documentElement.setAttribute('data-reduce-motion', String(value));
      break;
      
    case 'largeText':
      document.documentElement.classList.toggle('large-text', value as boolean);
      break;
      
    case 'devMode':
      document.documentElement.setAttribute('data-dev-mode', String(value));
      break;
  }
}

// Selector hooks for optimized subscriptions
export const useTerminalSettings = () =>
  useSettingsStore(state => ({
    fontSize: state.fontSize,
    fontFamily: state.fontFamily,
    fontWeight: state.fontWeight,
    lineHeight: state.lineHeight,
    letterSpacing: state.letterSpacing,
    cursorStyle: state.cursorStyle,
    cursorBlink: state.cursorBlink,
    theme: state.theme,
    scrollback: state.scrollback,
    bellSound: state.bellSound,
    webglEnabled: state.webglEnabled,
  }));

export const usePerformanceSettings = () =>
  useSettingsStore(state => ({
    webglEnabled: state.webglEnabled,
    rendererType: state.rendererType,
    maxFps: state.maxFps,
    allowProposedApi: state.allowProposedApi,
    showPerformanceMetrics: state.showPerformanceMetrics,
  }));

export const useAccessibilitySettings = () =>
  useSettingsStore(state => ({
    highContrastMode: state.highContrastMode,
    largeText: state.largeText,
    reduceAnimations: state.reduceAnimations,
    screenReaderSupport: state.screenReaderSupport,
    keyboardNavigation: state.keyboardNavigation,
    screenReaderMode: state.screenReaderMode,
  }));

export const useCollaborationSettings = () =>
  useSettingsStore(state => ({
    showOtherCursors: state.showOtherCursors,
    collaborationSound: state.collaborationSound,
    participantNotifications: state.participantNotifications,
  }));

export const useFileSettings = () =>
  useSettingsStore(state => ({
    maxUploadSize: state.maxUploadSize,
    allowedUploadTypes: state.allowedUploadTypes,
    downloadLocation: state.downloadLocation,
    customDownloadPath: state.customDownloadPath,
  }));