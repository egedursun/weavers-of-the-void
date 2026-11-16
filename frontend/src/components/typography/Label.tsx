import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Truncatable } from './Truncatable'
import { type Truncate } from './textStyles'

type LabelProps = HTMLAttributes<HTMLElement> & {
  as?: 'span' | 'dt' | 'label' | 'div' | 'legend' | 'p'
  variant?: 'default' | 'overline' | 'gilded'
  truncate?: Truncate
  htmlFor?: string
  children: ReactNode
}

export function Label({
  as = 'span',
  variant = 'default',
  className,
  ...props
}: LabelProps) {
  return (
    <Truncatable
      as={as}
      data-typography={variant === 'default' ? 'label' : variant}
      className={cn(
        'm-0 text-muted-foreground',
        variant === 'overline' && 'text-overline font-semibold uppercase',
        variant === 'default' && 'text-caption font-medium',
        variant === 'gilded' &&
          'text-gilded font-display text-caption font-semibold',
        className
      )}
      {...props}
    />
  )
}
