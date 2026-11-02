import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Truncatable } from './Truncatable'
import { type Truncate } from './textStyles'

type PageTitleProps = HTMLAttributes<HTMLHeadingElement> & {
  truncate?: Truncate
  children: ReactNode
}

export function PageTitle({ className, truncate, ...props }: PageTitleProps) {
  return (
    <Truncatable
      as='h1'
      data-typography='page-title'
      truncate={truncate}
      className={cn(
        'm-0 font-display text-display font-semibold text-foreground',
        className
      )}
      {...props}
    />
  )
}
