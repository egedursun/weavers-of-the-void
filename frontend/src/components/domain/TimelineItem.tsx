import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label, Text } from '@/components/typography'

const TONE_CLASS = {
  default: 'border-border bg-muted text-muted-foreground',
  primary: 'border-primary/30 bg-primary/12 text-primary',
  success: 'border-success/30 bg-success/12 text-success',
  warning: 'border-warning/30 bg-warning/12 text-warning',
  destructive: 'border-destructive/30 bg-destructive/12 text-destructive',
} as const

export type TimelineTone = keyof typeof TONE_CLASS

type TimelineProps = {
  children: ReactNode
  label?: string
}

export function Timeline({ children, label }: TimelineProps) {
  return (
    <ol
      data-domain='timeline'
      aria-label={label}
      className='flex min-w-0 flex-col'
    >
      {children}
    </ol>
  )
}

type TimelineItemProps = {
  icon: LucideIcon
  title: ReactNode
  timestamp?: ReactNode
  tone?: TimelineTone
  children?: ReactNode
  last?: boolean
  framed?: boolean
}

export function TimelineItem({
  icon: Icon,
  title,
  timestamp,
  tone = 'default',
  children,
  last = false,
  framed = false,
}: TimelineItemProps) {
  return (
    <li
      data-domain='timeline-item'
      className='grid min-w-0 grid-cols-[auto_minmax(0,1fr)] gap-x-3'
    >
      <div className='flex flex-col items-center'>
        <span
          className={cn(
            'flex size-control-sm shrink-0 items-center justify-center rounded-full border',
            TONE_CLASS[tone]
          )}
        >
          <Icon aria-hidden='true' className='size-icon-sm' />
        </span>
        {!last && <span aria-hidden='true' className='w-px flex-1 bg-border' />}
      </div>
      <div className={cn('flex min-w-0 flex-col', !last && 'pb-4')}>
        <div
          className={cn(
            'flex min-w-0 flex-col gap-1',
            framed &&
              'rounded-lg border bg-background/60 px-3 py-2 transition-colors hover:bg-accent/40'
          )}
        >
          <div className='flex min-h-control-sm min-w-0 items-center gap-2'>
            <Text as='div' weight='medium' className='min-w-0 flex-1'>
              {title}
            </Text>
            {timestamp && <Label className='shrink-0'>{timestamp}</Label>}
          </div>
          {children && (
            <div className='flex min-w-0 flex-col gap-2'>{children}</div>
          )}
        </div>
      </div>
    </li>
  )
}
