import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
  errorMessage?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error = false, errorMessage, id, ...props }, ref) => {
    const inputId = id || React.useId()
    const errorId = errorMessage ? `${inputId}-error` : undefined

    return (
      <div className="relative">
        <input
          type={type}
          id={inputId}
          className={cn(
            'flex h-11 w-full rounded-lg border px-4 py-2 text-sm transition-all duration-300',
            'file:border-0 file:bg-transparent file:text-sm file:font-medium',
            'placeholder:opacity-50',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-red-500 focus:ring-red-500/30',
            className
          )}
          style={{
            background: 'var(--input-bg)',
            border: `1px solid ${error ? 'var(--color-error, #ef4444)' : 'var(--input-border)'}`,
            color: 'var(--input-text)',
          }}
          ref={ref}
          aria-invalid={error}
          aria-describedby={errorId}
          {...props}
        />
        {errorMessage && (
          <p 
            id={errorId} 
            className="mt-1.5 text-sm text-red-500 dark:text-red-400"
            role="alert"
            aria-live="polite"
          >
            {errorMessage}
          </p>
        )}
      </div>
    )
  }
)
Input.displayName = 'Input'

export { Input }