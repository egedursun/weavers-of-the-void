import * as React from 'react'
import { cn } from '@/lib/utils'
import {
  type ControlSize,
  controlFieldPadding,
  controlHeight,
  controlText,
} from './control-size'

const fieldSurface =
  'rounded-md border border-input bg-field shadow-xs transition-[color,box-shadow,border-color] outline-none placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20'

type InputProps = Omit<React.ComponentProps<'input'>, 'size'> & {
  size?: ControlSize
  leadingIcon?: React.ComponentType<{
    className?: string
    'aria-hidden'?: boolean
  }>
}

const LEADING_PADDING: Record<ControlSize, string> = {
  sm: 'ps-8',
  default: 'ps-9',
  lg: 'ps-10',
}

const LEADING_ICON_SIZE: Record<ControlSize, string> = {
  sm: 'size-icon-sm',
  default: 'size-icon-md',
  lg: 'size-icon-lg',
}

function Input({
  className,
  type,
  size = 'default',
  leadingIcon: LeadingIcon,
  ...props
}: InputProps) {
  if (LeadingIcon)
    return (
      <div
        data-slot='input-group'
        className={cn('relative flex w-full min-w-0 items-center', className)}
      >
        <LeadingIcon
          aria-hidden
          className={cn(
            'pointer-events-none absolute start-3 text-muted-foreground',
            LEADING_ICON_SIZE[size]
          )}
        />
        <Input
          type={type}
          size={size}
          className={LEADING_PADDING[size]}
          {...props}
        />
      </div>
    )
  return (
    <input
      type={type}
      data-slot='input'
      data-control-size={size}
      className={cn(
        'flex w-full min-w-0 py-0',
        fieldSurface,
        controlHeight[size],
        controlFieldPadding[size],
        controlText,
        'file:inline-flex file:h-full file:border-0 file:bg-transparent file:font-medium file:text-foreground',
        className
      )}
      {...props}
    />
  )
}

export { Input, fieldSurface }
export type { InputProps }
