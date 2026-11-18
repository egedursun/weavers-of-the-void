import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label as FieldLabel } from '@/components/ui/label'
import { Muted } from '@/components/typography'

const LABEL_TEXT = 'min-w-0 flex-1 truncate text-body font-medium select-none'

export function FieldTile({
  id,
  label,
  icon: Icon,
  aside,
  framed = true,
  className,
  children,
}: {
  id?: string
  label: string
  icon?: LucideIcon
  aside?: string
  framed?: boolean
  className?: string
  children: ReactNode
}) {
  const Root = id === undefined ? 'label' : 'div'
  return (
    <Root
      data-domain='field-tile'
      className={cn(
        'flex min-w-0 flex-col justify-between gap-1.5',
        framed &&
          'rounded-md border surface-framed border-gild/70 bg-card p-2.5',
        className
      )}
    >
      <span className='flex min-w-0 items-center gap-1.5'>
        {Icon && (
          <Icon
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-muted-foreground'
          />
        )}
        {id === undefined ? (
          <span className={LABEL_TEXT}>{label}</span>
        ) : (
          <FieldLabel htmlFor={id} className='min-w-0 flex-1 truncate'>
            {label}
          </FieldLabel>
        )}
        {aside && (
          <Muted as='span' variant='caption' className='shrink-0'>
            {aside}
          </Muted>
        )}
      </span>
      {children}
    </Root>
  )
}
