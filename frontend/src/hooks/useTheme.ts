import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'dark' | 'light'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

// Shared Color Palette for all components
export const COLORS = {
  dark: {
    CYBER_CYAN: '#00f0ff',
    CYBER_BLUE: '#0066ff',
    CYBER_MAGENTA: '#ff00ff',
    CYBER_PURPLE: '#8b5cf6',
    CYBER_GREEN: '#00ff88',
    CYBER_RED: '#ff3366',
    CYBER_YELLOW: '#eab308',
    cardBg: 'rgba(15, 15, 35, 0.5)',
    cardBgSolid: '#0a0a1f',
    cardBorder: 'rgba(0, 240, 255, 0.1)',
    textPrimary: '#e8e8f0',
    textSecondary: '#6b7280',
    textMuted: '#505080',
    accentColor: '#00f0ff',
    accentGlow: 'rgba(0, 240, 255, 0.15)',
    gradientStart: '#00f0ff',
    headerBg: 'rgba(7, 7, 18, 0.9)',
    borderColor: 'rgba(0, 240, 255, 0.1)',
    inputBg: 'rgba(10, 10, 25, 0.9)',
    inputBorder: 'rgba(0, 240, 255, 0.3)',
    inputText: '#e8e8f0',
    sidebarBg: 'linear-gradient(180deg, #070712 0%, #0a0a1f 100%)',
    sidebarText: '#e8e8f0',
    sidebarTextMuted: '#505080',
    sidebarBorder: 'rgba(0, 240, 255, 0.15)',
    activeBg: 'rgba(0, 240, 255, 0.15)',
    activeText: '#00f0ff',
    navItemColor: '#6b7280',
    logoGradient: 'linear-gradient(135deg, #00f0ff 0%, #0066ff 100%)',
    badgeBg: 'rgba(0, 240, 255, 0.15)',
    statusOnline: '#00ff88',
    statusWarning: '#eab308',
    statusError: '#ff3366',
  },
  light: {
    CYBER_CYAN: '#0891b2',
    CYBER_BLUE: '#2563eb',
    CYBER_MAGENTA: '#7c3aed',
    CYBER_PURPLE: '#8b5cf6',
    CYBER_GREEN: '#059669',
    CYBER_RED: '#dc2626',
    CYBER_YELLOW: '#ca8a04',
    cardBg: '#ffffff',
    cardBgSolid: '#ffffff',
    cardBorder: '#e2e8f0',
    textPrimary: '#1e293b',
    textSecondary: '#64748b',
    textMuted: '#94a3b8',
    accentColor: '#2563eb',
    accentGlow: 'rgba(37, 99, 235, 0.15)',
    gradientStart: '#2563eb',
    headerBg: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e2e8f0',
    inputBg: '#ffffff',
    inputBorder: '#e2e8f0',
    inputText: '#1e293b',
    sidebarBg: '#ffffff',
    sidebarText: '#1e293b',
    sidebarTextMuted: '#94a3b8',
    sidebarBorder: '#e2e8f0',
    activeBg: '#eff6ff',
    activeText: '#2563eb',
    navItemColor: '#64748b',
    logoGradient: 'linear-gradient(135deg, #2563eb 0%, #0891b2 100%)',
    badgeBg: '#eff6ff',
    statusOnline: '#10b981',
    statusWarning: '#f59e0b',
    statusError: '#ef4444',
  }
}

export type Colors = typeof COLORS.dark

// Complete theme variable mappings - all CSS variables that need to change
const THEME_VARIABLES = {
  dark: {
    '--glass-bg': 'rgba(15, 15, 35, 0.7)',
    '--glass-border': 'rgba(0, 240, 255, 0.15)',
    '--glass-shadow': 'none',
    '--cyber-cyan': '#00f0ff',
    '--cyber-blue': '#0066ff',
    '--cyber-magenta': '#ff00ff',
    '--cyber-purple': '#8b5cf6',
    '--cyber-green': '#00ff88',
    '--color-background': '#050510',
    '--color-foreground': '#e8e8f0',
    '--color-card': '#0a0a1f',
    '--color-card-foreground': '#e8e8f0',
    '--color-border': '#2d2d4a',
    '--color-muted': '#1a1a2e',
    '--color-muted-foreground': '#6b7280',
    '--color-sidebar': '#070712',
    '--color-sidebar-foreground': '#a0a0c0',
    '--color-primary': '#00f0ff',
    '--color-primary-foreground': '#000000',
    '--color-secondary': '#0f0f1a',
    '--color-secondary-foreground': '#e0e0e0',
    '--color-accent': '#ff00ff',
    '--color-accent-foreground': '#ffffff',
    '--color-destructive': '#ff3366',
    '--color-destructive-foreground': '#ffffff',
    '--color-ring': '#00f0ff',
    '--color-popover': '#0d0d20',
    '--color-popover-foreground': '#f0f0f8',
    '--color-input-bg': 'rgba(10, 10, 25, 0.9)',
    '--color-input-border': 'rgba(0, 240, 255, 0.3)',
    '--color-input-text': '#e8e8f0',
    '--sidebar-bg': '#070712',
    '--sidebar-text': '#a0a0c0',
    '--sidebar-text-hover': '#e8e8f0',
    '--sidebar-active': 'rgba(0, 240, 255, 0.15)',
    '--sidebar-active-text': '#00f0ff',
    '--sidebar-border': 'rgba(0, 240, 255, 0.15)',
    '--status-online': '#00ff88',
    '--status-warning': '#eab308',
    '--status-error': '#ff3366',
    '--grid-color': 'rgba(0, 240, 255, 0.03)',
    '--shadow-card': '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 40px rgba(0, 240, 255, 0.08)',
    '--shadow-card-hover': '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 60px rgba(0, 240, 255, 0.15)',
    '--shadow-cyber': '0 0 20px rgba(0, 240, 255, 0.1)',
    '--shadow-hover': '0 20px 40px rgba(0, 0, 0, 0.6), 0 0 40px rgba(0, 240, 255, 0.2)',
  },
  light: {
    '--glass-bg': 'rgba(255, 255, 255, 0.9)',
    '--glass-border': 'rgba(59, 130, 246, 0.15)',
    '--glass-shadow': '0 4px 20px rgba(59, 130, 246, 0.08)',
    '--cyber-cyan': '#0891b2',
    '--cyber-blue': '#2563eb',
    '--cyber-magenta': '#7c3aed',
    '--cyber-purple': '#8b5cf6',
    '--cyber-green': '#059669',
    '--color-background': '#f8fafc',
    '--color-foreground': '#1e293b',
    '--color-card': '#ffffff',
    '--color-card-foreground': '#1e293b',
    '--color-border': '#e2e8f0',
    '--color-muted': '#f1f5f9',
    '--color-muted-foreground': '#64748b',
    '--color-sidebar': '#ffffff',
    '--color-sidebar-foreground': '#1e293b',
    '--color-primary': '#2563eb',
    '--color-primary-foreground': '#ffffff',
    '--color-secondary': '#f8fafc',
    '--color-secondary-foreground': '#1e293b',
    '--color-accent': '#7c3aed',
    '--color-accent-foreground': '#ffffff',
    '--color-destructive': '#dc2626',
    '--color-destructive-foreground': '#ffffff',
    '--color-ring': '#2563eb',
    '--color-popover': '#ffffff',
    '--color-popover-foreground': '#1e293b',
    '--color-input-bg': '#ffffff',
    '--color-input-border': '#e2e8f0',
    '--color-input-text': '#1e293b',
    '--sidebar-bg': '#ffffff',
    '--sidebar-text': '#475569',
    '--sidebar-text-hover': '#1e293b',
    '--sidebar-active': '#eff6ff',
    '--sidebar-active-text': '#2563eb',
    '--sidebar-border': '#e2e8f0',
    '--status-online': '#10b981',
    '--status-warning': '#f59e0b',
    '--status-error': '#ef4444',
    '--grid-color': 'rgba(59, 130, 246, 0.02)',
    '--shadow-card': '0 2px 8px rgba(59, 130, 246, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04)',
    '--shadow-card-hover': '0 15px 40px -10px rgba(59, 130, 246, 0.15), 0 0 25px rgba(59, 130, 246, 0.1)',
    '--shadow-cyber': '0 4px 20px rgba(59, 130, 246, 0.08)',
    '--shadow-hover': '0 15px 40px -10px rgba(59, 130, 246, 0.15), 0 0 30px rgba(59, 130, 246, 0.1)',
  }
}

// Apply all theme variables to document root synchronously
function applyTheme(theme: Theme) {
  const root = document.documentElement
  const variables = THEME_VARIABLES[theme]
  
  // Set theme attribute first (triggers CSS transitions)
  root.setAttribute('data-theme', theme)
  
  // Apply all CSS variables synchronously
  for (const [variable, value] of Object.entries(variables)) {
    root.style.setProperty(variable, value)
  }
  
  // Also update body styles directly
  const body = document.body
  if (theme === 'light') {
    body.style.background = 'linear-gradient(180deg, #f8fafc 0%, #f0f4f8 100%)'
    body.style.color = '#1e293b'
  } else {
    body.style.background = '#050510'
    body.style.color = '#e8e8f0'
  }
}

// Synchronous theme initialization - runs before React renders
export function initTheme() {
  // Check localStorage synchronously
  const stored = localStorage.getItem('theme-storage')
  
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      if (parsed.state?.theme) {
        applyTheme(parsed.state.theme)
        return
      }
    } catch (e) {
      console.warn('Failed to parse theme storage', e)
    }
  }
  
  // Apply default dark theme
  applyTheme('dark')
}

export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      setTheme: (theme) => {
        applyTheme(theme) // Apply immediately before state update
        set({ theme })
      },
      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark'
        applyTheme(newTheme) // Apply immediately before state update
        set({ theme: newTheme })
      },
    }),
    {
      name: 'theme-storage',
      // Custom storage handler for immediate theme application
      onRehydrateStorage: () => (state) => {
        // Apply theme immediately after hydration from localStorage
        if (state?.theme) {
          // Use requestAnimationFrame to ensure DOM is ready
          requestAnimationFrame(() => applyTheme(state.theme))
        }
      }
    }
  )
)

// Hook to get theme-aware colors
export function useColors(): Colors {
  const theme = useTheme((s) => s.theme)
  return COLORS[theme]
}

// Hook to check if light mode
export function useIsLight(): boolean {
  const theme = useTheme((s) => s.theme)
  return theme === 'light'
}

// Export for direct access if needed
export { applyTheme }