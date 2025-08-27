import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// Types
export type ThemeMode = 'light' | 'dark' | 'system';
export type ColorScheme = 'default' | 'high-contrast' | 'colorful' | 'minimal';
export type AccentColor = 'blue' | 'green' | 'purple' | 'orange' | 'pink';

export interface CustomTheme {
  id: string;
  name: string;
  colors: {
    background: string;
    foreground: string;
    cursor: string;
    selection: string;
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
  created: Date;
  isBuiltIn: boolean;
}

export interface ThemeState {
  // Current theme settings
  mode: ThemeMode;
  theme: 'light' | 'dark';
  colorScheme: ColorScheme;
  accentColor: AccentColor;
  
  // Custom themes
  customThemes: CustomTheme[];
  activeCustomTheme?: string;
  
  // Theme preferences
  followSystemTheme: boolean;
  automaticThemeSwitch: {
    enabled: boolean;
    lightStart: string; // HH:MM format
    darkStart: string;   // HH:MM format
  };
  
  // Accessibility
  reducedMotion: boolean;
  highContrast: boolean;
  colorBlindMode: 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia';
  
  // Actions
  setMode: (mode: ThemeMode) => void;
  setColorScheme: (scheme: ColorScheme) => void;
  setAccentColor: (color: AccentColor) => void;
  setReducedMotion: (enabled: boolean) => void;
  setHighContrast: (enabled: boolean) => void;
  setColorBlindMode: (mode: ThemeState['colorBlindMode']) => void;
  setFollowSystemTheme: (follow: boolean) => void;
  setAutomaticThemeSwitch: (config: ThemeState['automaticThemeSwitch']) => void;
  addCustomTheme: (theme: Omit<CustomTheme, 'id' | 'created' | 'isBuiltIn'>) => void;
  removeCustomTheme: (themeId: string) => void;
  setActiveCustomTheme: (themeId: string | undefined) => void;
  initializeTheme: () => void;
  toggleTheme: () => void;
  resetToDefaults: () => void;
}

// Built-in themes
const builtInThemes: CustomTheme[] = [
  {
    id: 'github-dark',
    name: 'GitHub Dark',
    colors: {
      background: '#0d1117',
      foreground: '#f0f6fc',
      cursor: '#58a6ff',
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
      brightWhite: '#f0f6fc',
    },
    created: new Date(),
    isBuiltIn: true,
  },
  {
    id: 'github-light',
    name: 'GitHub Light',
    colors: {
      background: '#ffffff',
      foreground: '#24292f',
      cursor: '#0969da',
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
      brightWhite: '#8c959f',
    },
    created: new Date(),
    isBuiltIn: true,
  },
  {
    id: 'dracula',
    name: 'Dracula',
    colors: {
      background: '#282a36',
      foreground: '#f8f8f2',
      cursor: '#f8f8f0',
      selection: '#44475a',
      black: '#000000',
      red: '#ff5555',
      green: '#50fa7b',
      yellow: '#f1fa8c',
      blue: '#bd93f9',
      magenta: '#ff79c6',
      cyan: '#8be9fd',
      white: '#bfbfbf',
      brightBlack: '#4d4d4d',
      brightRed: '#ff6e67',
      brightGreen: '#5af78e',
      brightYellow: '#f4f99d',
      brightBlue: '#caa9fa',
      brightMagenta: '#ff92d0',
      brightCyan: '#9aedfe',
      brightWhite: '#e6e6e6',
    },
    created: new Date(),
    isBuiltIn: true,
  },
  {
    id: 'one-dark',
    name: 'One Dark Pro',
    colors: {
      background: '#1e2127',
      foreground: '#abb2bf',
      cursor: '#528bff',
      selection: '#3e4451',
      black: '#1e2127',
      red: '#e06c75',
      green: '#98c379',
      yellow: '#d19a66',
      blue: '#61afef',
      magenta: '#c678dd',
      cyan: '#56b6c2',
      white: '#abb2bf',
      brightBlack: '#5c6370',
      brightRed: '#e06c75',
      brightGreen: '#98c379',
      brightYellow: '#d19a66',
      brightBlue: '#61afef',
      brightMagenta: '#c678dd',
      brightCyan: '#56b6c2',
      brightWhite: '#ffffff',
    },
    created: new Date(),
    isBuiltIn: true,
  },
];

// Accent color palettes
const accentColors = {
  blue: {
    primary: '#58a6ff',
    secondary: '#79c0ff',
    hover: '#4493f8',
  },
  green: {
    primary: '#3fb950',
    secondary: '#56d364',
    hover: '#2ea043',
  },
  purple: {
    primary: '#bc8cff',
    secondary: '#d2a8ff',
    hover: '#a475f9',
  },
  orange: {
    primary: '#f9826c',
    secondary: '#ffab70',
    hover: '#e85c42',
  },
  pink: {
    primary: '#ff79c6',
    secondary: '#ff92d0',
    hover: '#ff5bb3',
  },
};

// Initial state
const initialState = {
  mode: 'system' as ThemeMode,
  theme: 'dark' as 'light' | 'dark',
  colorScheme: 'default' as ColorScheme,
  accentColor: 'blue' as AccentColor,
  customThemes: builtInThemes,
  activeCustomTheme: undefined,
  followSystemTheme: true,
  automaticThemeSwitch: {
    enabled: false,
    lightStart: '06:00',
    darkStart: '18:00',
  },
  reducedMotion: false,
  highContrast: false,
  colorBlindMode: 'none' as ThemeState['colorBlindMode'],
};

// Helper functions
function detectSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'dark';
  
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function detectReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function detectHighContrast(): boolean {
  if (typeof window === 'undefined') return false;
  
  return window.matchMedia('(prefers-contrast: high)').matches;
}

function applyThemeToDocument(theme: 'light' | 'dark', accentColor: AccentColor) {
  if (typeof document === 'undefined') return;
  
  const root = document.documentElement;
  
  // Set theme class
  root.className = root.className.replace(/\b(light|dark)\b/g, '');
  root.classList.add(theme);
  root.setAttribute('data-theme', theme);
  
  // Apply accent color CSS variables
  const colors = accentColors[accentColor];
  root.style.setProperty('--accent-primary', colors.primary);
  root.style.setProperty('--accent-secondary', colors.secondary);
  root.style.setProperty('--accent-hover', colors.hover);
}

function getCurrentTime(): string {
  return new Date().toTimeString().slice(0, 5); // HH:MM format
}

function isTimeInRange(current: string, start: string, end: string): boolean {
  const [currentHour, currentMin] = current.split(':').map(Number);
  const [startHour, startMin] = start.split(':').map(Number);
  const [endHour, endMin] = end.split(':').map(Number);
  
  const currentTime = currentHour * 60 + currentMin;
  const startTime = startHour * 60 + startMin;
  const endTime = endHour * 60 + endMin;
  
  if (startTime <= endTime) {
    return currentTime >= startTime && currentTime < endTime;
  } else {
    // Crosses midnight
    return currentTime >= startTime || currentTime < endTime;
  }
}

// Store implementation
export const useThemeStore = create<ThemeState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        setMode: (mode: ThemeMode) => {
          set({ mode }, false, 'setMode');
          
          const state = get();
          let newTheme: 'light' | 'dark';
          
          if (mode === 'system') {
            newTheme = detectSystemTheme();
            set({ followSystemTheme: true });
          } else {
            newTheme = mode;
            set({ followSystemTheme: false });
          }
          
          set({ theme: newTheme });
          applyThemeToDocument(newTheme, state.accentColor);
        },

        setColorScheme: (scheme: ColorScheme) => {
          set({ colorScheme: scheme }, false, 'setColorScheme');
        },

        setAccentColor: (color: AccentColor) => {
          set({ accentColor: color }, false, 'setAccentColor');
          
          const { theme } = get();
          applyThemeToDocument(theme, color);
        },

        setReducedMotion: (enabled: boolean) => {
          set({ reducedMotion: enabled }, false, 'setReducedMotion');
          
          if (typeof document !== 'undefined') {
            document.documentElement.setAttribute('data-reduce-motion', enabled.toString());
          }
        },

        setHighContrast: (enabled: boolean) => {
          set({ highContrast: enabled }, false, 'setHighContrast');
          
          if (typeof document !== 'undefined') {
            document.documentElement.setAttribute('data-high-contrast', enabled.toString());
          }
        },

        setColorBlindMode: (mode: ThemeState['colorBlindMode']) => {
          set({ colorBlindMode: mode }, false, 'setColorBlindMode');
          
          if (typeof document !== 'undefined') {
            document.documentElement.setAttribute('data-colorblind-mode', mode);
          }
        },

        setFollowSystemTheme: (follow: boolean) => {
          set({ followSystemTheme: follow }, false, 'setFollowSystemTheme');
          
          if (follow) {
            const systemTheme = detectSystemTheme();
            const { accentColor } = get();
            set({ mode: 'system', theme: systemTheme });
            applyThemeToDocument(systemTheme, accentColor);
          }
        },

        setAutomaticThemeSwitch: (config: ThemeState['automaticThemeSwitch']) => {
          set({ automaticThemeSwitch: config }, false, 'setAutomaticThemeSwitch');
          
          if (config.enabled) {
            const currentTime = getCurrentTime();
            const { accentColor } = get();
            
            const isLightTime = isTimeInRange(currentTime, config.lightStart, config.darkStart);
            const newTheme = isLightTime ? 'light' : 'dark';
            
            set({ theme: newTheme, followSystemTheme: false });
            applyThemeToDocument(newTheme, accentColor);
          }
        },

        addCustomTheme: (themeData: Omit<CustomTheme, 'id' | 'created' | 'isBuiltIn'>) => {
          const newTheme: CustomTheme = {
            ...themeData,
            id: `custom-${Date.now()}`,
            created: new Date(),
            isBuiltIn: false,
          };
          
          const { customThemes } = get();
          set({ customThemes: [...customThemes, newTheme] }, false, 'addCustomTheme');
        },

        removeCustomTheme: (themeId: string) => {
          const { customThemes, activeCustomTheme } = get();
          const newCustomThemes = customThemes.filter(theme => 
            theme.id !== themeId || theme.isBuiltIn
          );
          
          const updates: Partial<ThemeState> = { customThemes: newCustomThemes };
          if (activeCustomTheme === themeId) {
            updates.activeCustomTheme = undefined;
          }
          
          set(updates, false, 'removeCustomTheme');
        },

        setActiveCustomTheme: (themeId: string | undefined) => {
          set({ activeCustomTheme: themeId }, false, 'setActiveCustomTheme');
        },

        initializeTheme: () => {
          // Detect system preferences
          const systemTheme = detectSystemTheme();
          const reducedMotion = detectReducedMotion();
          const highContrast = detectHighContrast();
          
          const state = get();
          let currentTheme = state.theme;
          
          // Apply automatic theme switching if enabled
          if (state.automaticThemeSwitch.enabled) {
            const currentTime = getCurrentTime();
            const { lightStart, darkStart } = state.automaticThemeSwitch;
            
            const isLightTime = isTimeInRange(currentTime, lightStart, darkStart);
            currentTheme = isLightTime ? 'light' : 'dark';
          } else if (state.followSystemTheme) {
            currentTheme = systemTheme;
          }
          
          // Update state with detected preferences
          set({
            theme: currentTheme,
            reducedMotion,
            highContrast,
          });
          
          // Apply theme to document
          applyThemeToDocument(currentTheme, state.accentColor);
          
          // Set up system theme listener
          if (typeof window !== 'undefined') {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const handleChange = (e: MediaQueryListEvent) => {
              const { followSystemTheme } = get();
              if (followSystemTheme) {
                const newTheme = e.matches ? 'dark' : 'light';
                const { accentColor } = get();
                set({ theme: newTheme });
                applyThemeToDocument(newTheme, accentColor);
              }
            };
            
            mediaQuery.addEventListener('change', handleChange);
            
            // Set up automatic theme switching timer
            if (state.automaticThemeSwitch.enabled) {
              const checkTime = () => {
                const { automaticThemeSwitch, accentColor } = get();
                if (automaticThemeSwitch.enabled) {
                  const currentTime = getCurrentTime();
                  const isLightTime = isTimeInRange(
                    currentTime, 
                    automaticThemeSwitch.lightStart, 
                    automaticThemeSwitch.darkStart
                  );
                  const newTheme = isLightTime ? 'light' : 'dark';
                  
                  const currentState = get();
                  if (currentState.theme !== newTheme) {
                    set({ theme: newTheme });
                    applyThemeToDocument(newTheme, accentColor);
                  }
                }
              };
              
              // Check every minute
              const interval = setInterval(checkTime, 60000);
              
              // Clean up on unmount (handled by the component)
              (window as any).__themeCheckInterval = interval;
            }
          }
        },

        toggleTheme: () => {
          const { theme, accentColor } = get();
          const newTheme = theme === 'light' ? 'dark' : 'light';
          
          set({ 
            theme: newTheme,
            mode: newTheme,
            followSystemTheme: false 
          });
          
          applyThemeToDocument(newTheme, accentColor);
        },

        resetToDefaults: () => {
          set(initialState, false, 'resetToDefaults');
          
          const systemTheme = detectSystemTheme();
          set({ theme: systemTheme });
          applyThemeToDocument(systemTheme, initialState.accentColor);
        },
      }),
      {
        name: 'theme-store',
        partialize: (state) => ({
          mode: state.mode,
          colorScheme: state.colorScheme,
          accentColor: state.accentColor,
          customThemes: state.customThemes.filter(theme => !theme.isBuiltIn),
          activeCustomTheme: state.activeCustomTheme,
          followSystemTheme: state.followSystemTheme,
          automaticThemeSwitch: state.automaticThemeSwitch,
          reducedMotion: state.reducedMotion,
          highContrast: state.highContrast,
          colorBlindMode: state.colorBlindMode,
        }),
      }
    ),
    { name: 'theme-store' }
  )
);

// Selector hooks for optimized subscriptions
export const useCurrentTheme = () =>
  useThemeStore(state => ({
    theme: state.theme,
    colorScheme: state.colorScheme,
    accentColor: state.accentColor,
    customTheme: state.customThemes.find(t => t.id === state.activeCustomTheme),
  }));

export const useThemePreferences = () =>
  useThemeStore(state => ({
    mode: state.mode,
    followSystemTheme: state.followSystemTheme,
    automaticThemeSwitch: state.automaticThemeSwitch,
    reducedMotion: state.reducedMotion,
    highContrast: state.highContrast,
    colorBlindMode: state.colorBlindMode,
  }));

export const useCustomThemes = () =>
  useThemeStore(state => ({
    themes: state.customThemes,
    activeTheme: state.activeCustomTheme,
    addTheme: state.addCustomTheme,
    removeTheme: state.removeCustomTheme,
    setActiveTheme: state.setActiveCustomTheme,
  }));