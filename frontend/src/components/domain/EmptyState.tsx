import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Muted, Text } from '@/components/typography'
import { Medallion } from './KpiTile'

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
        className='flex min-w-0 flex-wrap items-center gap-3 rounded-md px-3 py-2.5 sealed-well'
      >
        <Medallion icon={Icon} tone='muted' size='sm' />
        <div className='flex min-w-0 flex-1 basis-48 flex-col'>
          <Text weight='semibold' className='text-gilded font-display'>
            {title}
          </Text>
          <Muted variant='caption'>{description}</Muted>
        </div>
        {action && <div className='flex flex-wrap gap-2'>{action}</div>}
      </div>
    )
  return (
    <div
      data-domain='empty-state'
      className={cn(
        'flex min-w-0 flex-col items-center justify-center gap-3 rounded-md text-center sealed-well',
        size === 'compact' ? 'px-4 py-6' : 'px-6 py-12'
      )}
    >
      <Medallion icon={Icon} tone='muted' />
      <div className='flex max-w-md min-w-0 flex-col gap-1'>
        <Text weight='semibold' className='text-gilded font-display'>
          {title}
        </Text>
        <Muted>{description}</Muted>
      </div>
      {action && (
        <div className='flex flex-wrap justify-center gap-2'>{action}</div>
      )}
    </div>
  )
}
