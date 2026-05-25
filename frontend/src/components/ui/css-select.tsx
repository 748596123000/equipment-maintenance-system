/**
 * CSS-only Select Component
 * Replaces Radix UI Select to avoid React 19 compatibility issues
 */

import * as React from "react"
import { cn } from "@/lib/utils"
import { ChevronDown, Check } from "lucide-react"

interface SelectContextValue {
  value: string
  onValueChange: (value: string) => void
  open: boolean
  setOpen: (open: boolean) => void
}

const SelectContext = React.createContext<SelectContextValue | null>(null)

const useSelectContext = () => {
  const context = React.useContext(SelectContext)
  if (!context) {
    throw new Error("Select components must be used within Select")
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
    return {
      theme: 'dark' as const,
      colors: {
        cardBg: 'rgba(15, 15, 35, 0.5)',
        cardBorder: 'rgba(0, 240, 255, 0.1)',
        textPrimary: '#e8e8f0',
        textSecondary: '#6b7280',
        accentColor: '#00f0ff',
      },
      isLight: false
    }
  }
}

export const Select = ({ children, value, onValueChange, defaultValue = "", ...props }: React.HTMLAttributes<HTMLDivElement> & {
  value?: string
  onValueChange?: (value: string) => void
  defaultValue?: string
}) => {
  const [internalValue, setInternalValue] = React.useState(defaultValue)
  const [open, setOpen] = React.useState(false)
  const selectedValue = value ?? internalValue

  const handleValueChange = React.useCallback((newValue: string) => {
    setInternalValue(newValue)
    onValueChange?.(newValue)
    setOpen(false)
  }, [onValueChange])

  return (
    <SelectContext.Provider value={{ value: selectedValue, onValueChange: handleValueChange, open, setOpen }}>
      <div {...props}>{children}</div>
    </SelectContext.Provider>
  )
}

export const SelectTrigger = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ className, children, ...props }, ref) => {
    const { open, setOpen, value } = useSelectContext()
    const { colors, isLight } = useThemeColors()

    return (
      <button
        ref={ref}
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border px-3 py-2 text-sm shadow-sm",
          "focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          "[&>span]:line-clamp-1",
          className
        )}
        style={{
          background: colors.cardBg,
          borderColor: colors.cardBorder,
          color: colors.textPrimary,
        }}
        {...props}
      >
        {children || <span>{value || "请选择..."}</span>}
        <ChevronDown className="h-4 w-4 opacity-50" style={{ color: colors.textSecondary }} />
      </button>
    )
  }
)
SelectTrigger.displayName = "SelectTrigger"

export const SelectValue = ({ placeholder }: { placeholder?: string }) => {
  const { value } = useSelectContext()
  return <span>{value || placeholder || "请选择..."}</span>
}

export const SelectContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const { open, setOpen } = useSelectContext()
    const { colors, isLight } = useThemeColors()

    if (!open) return null

    // Close on click outside
    React.useEffect(() => {
      const handleClickOutside = (e: MouseEvent) => {
        const target = e.target as HTMLElement
        if (!target.closest('[role="listbox"]')) {
          setOpen(false)
        }
      }
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }, [setOpen])

    return (
      <div
        ref={ref}
        role="listbox"
        className={cn(
          "relative z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-md border shadow-md animate-in fade-in-0 zoom-in-95",
          "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
          "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
          className
        )}
        style={{
          background: colors.cardBg,
          borderColor: colors.cardBorder,
          color: colors.textPrimary,
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: '4px',
        }}
        {...props}
      >
        <div className="p-1">{children}</div>
      </div>
    )
  }
)
SelectContent.displayName = "SelectContent"

interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

export const SelectItem = React.forwardRef<HTMLDivElement, SelectItemProps>(
  ({ className, value, children, ...props }, ref) => {
    const { value: selectedValue, onValueChange } = useSelectContext()
    const { colors, isLight } = useThemeColors()
    const isSelected = selectedValue === value

    return (
      <div
        ref={ref}
        role="option"
        aria-selected={isSelected}
        onClick={() => onValueChange(value)}
        className={cn(
          "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none",
          "focus:bg-accent focus:text-accent-foreground",
          "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
          className
        )}
        style={{
          color: colors.textPrimary,
          cursor: 'pointer',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = isLight ? 'rgba(59, 130, 246, 0.08)' : 'rgba(0, 240, 255, 0.1)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
        }}
        {...props}
      >
        <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
          {isSelected && <Check className="h-4 w-4" style={{ color: colors.accentColor }} />}
        </span>
        {children}
      </div>
    )
  }
)
SelectItem.displayName = "SelectItem"

export const SelectGroup = ({ children }: { children?: React.ReactNode }) => <>{children}</>
export const SelectLabel = ({ children }: { children?: React.ReactNode }) => (
  <div className="py-1.5 pl-2 pr-8 text-sm font-semibold opacity-70">{children}</div>
)