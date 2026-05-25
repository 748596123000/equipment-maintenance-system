import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"
import { useTheme, COLORS } from "@/hooks/useTheme"

import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, style, ...props }, ref) => {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = COLORS[theme]
  
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-lg p-1 text-sm",
        className
      )}
      style={{
        background: isLight ? '#ffffff' : colors.cardBg,
        borderBottom: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)'}`,
        ...style
      }}
      {...props}
    />
  )
})
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, style, ...props }, ref) => {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = COLORS[theme]
  
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        className
      )}
      style={{
        color: isLight ? '#64748b' : '#a0a0c0',
        background: 'transparent',
        borderBottom: '2px solid transparent',
        ...style
      }}
      onMouseEnter={(e) => {
        if (!e.currentTarget.getAttribute('data-state')?.includes('active')) {
          e.currentTarget.style.background = isLight ? 'rgba(59, 130, 246, 0.05)' : 'rgba(0, 240, 255, 0.05)'
        }
      }}
      onMouseLeave={(e) => {
        if (!e.currentTarget.getAttribute('data-state')?.includes('active')) {
          e.currentTarget.style.background = 'transparent'
        }
      }}
      {...props}
    />
  )
})
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, style, ...props }, ref) => {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className
      )}
      style={{
        color: isLight ? '#1e293b' : '#e8e8f0',
        ...style
      }}
      {...props}
    />
  )
})
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
