/**
 * CSS-only Tabs Component
 * Replaces Radix UI Tabs to avoid React 19 compatibility issues
 */

import * as React from "react"
import { cn } from "@/lib/utils"

type TabsProps = React.HTMLAttributes<HTMLDivElement> & {
  defaultValue?: string
  value?: string
  onValueChange?: (value: string) => void
}

interface TabsContextValue {
  activeTab: string
  setActiveTab: (value: string) => void
}

const TabsContext = React.createContext<TabsContextValue | null>(null)

const useTabsContext = () => {
  const context = React.useContext(TabsContext)
  if (!context) {
    throw new Error("Tabs components must be used within Tabs")
  }
  return context
}

// Theme hook with fallback
const useThemeColors = () => {
  try {
    const { useTheme, COLORS } = require("@/hooks/useTheme")
    const { theme } = useTheme()
    return { theme, colors: COLORS[theme], isLight: theme === 'light' }
  } catch {
    return { theme: 'dark' as const, colors: { cardBg: 'rgba(15, 15, 35, 0.5)', cardBorder: 'rgba(0, 240, 255, 0.1)', textPrimary: '#e8e8f0', textSecondary: '#6b7280', accentColor: '#00f0ff' }, isLight: false }
  }
}

export const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  ({ className, defaultValue = "", value, onValueChange, children, ...props }, ref) => {
    const [internalValue, setInternalValue] = React.useState(defaultValue)
    const activeTab = value ?? internalValue

    const setActiveTab = React.useCallback((newValue: string) => {
      setInternalValue(newValue)
      onValueChange?.(newValue)
    }, [onValueChange])

    return (
      <TabsContext.Provider value={{ activeTab, setActiveTab }}>
        <div ref={ref} className={cn("space-y-4", className)} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    )
  }
)
Tabs.displayName = "Tabs"

interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {}

export const TabsList = React.forwardRef<HTMLDivElement, TabsListProps>(
  ({ className, children, ...props }, ref) => {
    const { isLight } = useThemeColors()

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 border-b transition-all duration-200",
          className
        )}
        style={{
          borderBottom: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)'}`,
          background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)',
        }}
        role="tablist"
        {...props}
      >
        {children}
      </div>
    )
  }
)
TabsList.displayName = "TabsList"

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}

export const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, children, ...props }, ref) => {
    const { activeTab, setActiveTab } = useTabsContext()
    const { isLight, colors } = useThemeColors()
    const isActive = activeTab === value

    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={isActive}
        data-state={isActive ? "active" : "inactive"}
        onClick={() => setActiveTab(value)}
        className={cn(
          "inline-flex items-center justify-center px-4 py-2 text-sm font-medium transition-all duration-200 rounded-t-lg",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "disabled:pointer-events-none disabled:opacity-50",
          className
        )}
        style={{
          color: isActive ? (isLight ? '#2563eb' : '#00f0ff') : (isLight ? '#64748b' : '#a0a0c0'),
          background: 'transparent',
          borderBottom: isActive ? '2px solid' : '2px solid transparent',
          borderBottomColor: isActive ? (isLight ? '#2563eb' : '#00f0ff') : 'transparent',
        }}
        {...props}
      >
        {children}
      </button>
    )
  }
)
TabsTrigger.displayName = "TabsTrigger"

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

export const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, children, ...props }, ref) => {
    const { activeTab } = useTabsContext()
    const { isLight } = useThemeColors()
    const isActive = activeTab === value

    if (!isActive) return null

    return (
      <div
        ref={ref}
        role="tabpanel"
        data-state={isActive ? "active" : "inactive"}
        className={cn("mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2", className)}
        style={{
          color: isLight ? '#1e293b' : '#e8e8f0',
        }}
        {...props}
      >
        {children}
      </div>
    )
  }
)
TabsContent.displayName = "TabsContent"