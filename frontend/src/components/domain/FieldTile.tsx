import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label as FieldLabel } from '@/components/ui/label'
import { Muted } from '@/components/typography'

export function FieldTile({
  id,
  label,
  icon: Icon,
  aside,
  framed = true,
  children,
}: {
  id: string
  label: string
  icon?: LucideIcon
  aside?: string
  framed?: boolean
  children: ReactNode
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col justify-between gap-1.5',
        framed &&
          'rounded-md border surface-framed border-gild/70 bg-card p-2.5'
      )}
    >
      <div className='flex min-w-0 items-center gap-1.5'>
        {Icon && (
          <Icon
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-muted-foreground'
          />
        )}
        <FieldLabel htmlFor={id} className='min-w-0 flex-1 truncate'>
          {label}
        </FieldLabel>
        {aside && (
          <Muted as='span' variant='caption' className='shrink-0'>
            {aside}
          </Muted>
        )}
      </div>
      {children}
    </div>
  )
}
