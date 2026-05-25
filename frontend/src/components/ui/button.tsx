import * as React from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  asChild?: boolean
  ripple?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ripple = true, ...props }, ref) => {
    // Ripple effect handler
    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (ripple) {
        const button = e.currentTarget
        const rect = button.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top
        
        const rippleEl = document.createElement('span')
        rippleEl.style.cssText = `
          position: absolute;
          width: 10px;
          height: 10px;
          background: rgba(255, 255, 255, 0.5);
          border-radius: 50%;
          transform: translate(-50%, -50%) scale(0);
          animation: button-ripple 0.6s ease-out forwards;
          left: ${x}px;
          top: ${y}px;
          pointer-events: none;
        `
        
        // Add keyframes if not exists
        if (!document.getElementById('button-ripple-styles')) {
          const style = document.createElement('style')
          style.id = 'button-ripple-styles'
          style.textContent = `
            @keyframes button-ripple {
              to {
                transform: translate(-50%, -50%) scale(40);
                opacity: 0;
              }
            }
          `
          document.head.appendChild(style)
        }
        
        button.style.position = 'relative'
        button.style.overflow = 'hidden'
        button.appendChild(rippleEl)
        
        setTimeout(() => rippleEl.remove(), 600)
      }
      
      // Call original onClick if provided
      props.onClick?.(e)
    }

    return (
      <button
        className={cn(
          'inline-flex items-center justify-center gap-2 whitespace-nowrap transition-all duration-300',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          '[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
          // Base styles
          'font-medium rounded-lg relative overflow-hidden',
          // Variant styles
          getButtonStyles(variant),
          // Size styles
          getButtonSizeStyles(size),
          className
        )}
        ref={ref}
        onClick={handleClick}
        {...props}
      />
    )
  }
)

function getButtonStyles(variant: string): string {
  switch (variant) {
    case 'default':
      return 'bg-gradient-to-r from-[var(--cyber-cyan)] to-[var(--cyber-blue)] text-black shadow-lg hover:shadow-[0_0_30px_rgba(0,240,255,0.3)] dark:text-black light:text-white'
    case 'destructive':
      return 'bg-[var(--color-error,#ef4444)] text-white hover:opacity-90'
    case 'outline':
      return 'border border-[var(--cyber-cyan)]/40 bg-transparent text-[var(--cyber-cyan)] hover:bg-[var(--cyber-cyan)]/10 hover:border-[var(--cyber-cyan)]'
    case 'secondary':
      return 'bg-[var(--color-surface,#ffffff)] text-[var(--color-text,#1e293b)] border border-[var(--color-border,#e2e8f0)] hover:bg-[var(--color-surface-hover,#f8fafc)] dark:bg-[rgba(15,15,35,0.8)] dark:text-[#e8e8f0] dark:border-[rgba(0,240,255,0.15)] dark:hover:bg-[rgba(20,20,50,0.9)]'
    case 'ghost':
      return 'text-[var(--color-text-secondary,#64748b)] hover:text-[var(--color-text,#1e293b)] hover:bg-[var(--color-surface-hover,#f8fafc)] dark:text-[#a0a0c0] dark:hover:text-[#e8e8f0] dark:hover:bg-[rgba(0,240,255,0.08)]'
    case 'link':
      return 'text-[var(--cyber-cyan)] underline-offset-4 hover:underline'
    default:
      return ''
  }
}

function getButtonSizeStyles(size: string): string {
  switch (size) {
    case 'sm':
      return 'h-9 px-4 py-1.5 rounded-md text-xs font-medium'
    case 'lg':
      return 'h-12 px-8 py-3 rounded-lg text-base font-semibold'
    case 'icon':
      return 'h-10 w-10 rounded-lg'
    default:
      return 'h-11 px-6 py-2 rounded-lg text-sm font-semibold'
  }
}

Button.displayName = 'Button'

export { Button }