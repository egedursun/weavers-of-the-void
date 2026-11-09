import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Muted, Text } from '@/components/typography'

type EmptyStateProps = {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
  size?: 'default' | 'compact' | 'inline'
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  size = 'default',
}: EmptyStateProps) {
  if (size === 'inline')
    return (
      <div
        data-domain='empty-state'
        className='flex min-w-0 flex-wrap items-center gap-3 rounded-xl border border-dashed bg-muted/20 px-3 py-2.5'
      >
        <span className='flex size-control-sm shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground'>
          <Icon aria-hidden='true' className='size-icon-sm' />
        </span>
        <div className='flex min-w-0 flex-1 basis-48 flex-col'>
          <Text weight='semibold'>{title}</Text>
          <Muted variant='caption'>{description}</Muted>
        </div>
        {action && <div className='flex flex-wrap gap-2'>{action}</div>}
      </div>
    )
  return (
    <div
      data-domain='empty-state'
      className={cn(
        'flex min-w-0 flex-col items-center justify-center gap-3 rounded-xl border border-dashed text-center',
        size === 'compact' ? 'px-4 py-6' : 'px-6 py-12'
      )}
    >
      <span className='flex size-control-lg shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground'>
        <Icon aria-hidden='true' className='size-icon-lg' />
      </span>
      <div className='flex max-w-md min-w-0 flex-col gap-1'>
        <Text weight='semibold'>{title}</Text>
        <Muted>{description}</Muted>
      </div>
      {action && (
        <div className='flex flex-wrap justify-center gap-2'>{action}</div>
      )}
    </div>
  )
}
