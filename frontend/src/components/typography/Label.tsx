import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Truncatable } from './Truncatable'
import { type Truncate } from './textStyles'

type LabelProps = HTMLAttributes<HTMLElement> & {
  as?: 'span' | 'dt' | 'label' | 'div' | 'legend' | 'p'
  variant?: 'default' | 'overline'
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
      data-typography={variant === 'overline' ? 'overline' : 'label'}
      className={cn(
        'm-0 text-muted-foreground',
        variant === 'overline'
          ? 'text-overline font-semibold uppercase'
          : 'text-caption font-medium',
        className
      )}
      {...props}
    />
  )
}
