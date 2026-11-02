import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Truncatable } from './Truncatable'
import { type Truncate } from './textStyles'

type SectionTitleProps = HTMLAttributes<HTMLHeadingElement> & {
  level?: 2 | 3 | 4
  truncate?: Truncate
  children: ReactNode
}

const TAG_OF = { 2: 'h2', 3: 'h3', 4: 'h4' } as const

export function SectionTitle({
  className,
  level = 2,
  truncate,
  ...props
}: SectionTitleProps) {
  return (
    <Truncatable
      as={TAG_OF[level]}
      data-typography='section-title'
      truncate={truncate}
      className={cn(
        'm-0 font-display text-title font-semibold text-foreground',
        className
      )}
      {...props}
    />
  )
}
