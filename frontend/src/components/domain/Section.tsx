import { type ReactNode, useId } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Muted, SectionTitle } from '@/components/typography'
import { type KpiTone, Medallion } from './KpiTile'

type SectionProps = {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  surface?: 'plain' | 'card'
  level?: 2 | 3
  id?: string
  icon?: LucideIcon
  tone?: KpiTone
  stretch?: boolean
}

export function Section({
  title,
  description,
  actions,
  children,
  surface = 'plain',
  level = 2,
  id,
  icon,
  tone = 'gold',
  stretch = false,
}: SectionProps) {
  const headingId = useId()
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      data-domain='section'
      className={cn(
        'flex min-w-0 flex-col gap-4',
        stretch && 'h-full',
        surface === 'card' &&
          'rounded-xl border bg-card p-5 text-card-foreground shadow-xs'
      )}
    >
      <div className='flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-2'>
        <div className='flex min-w-0 flex-1 basis-60 items-start gap-3'>
          {icon && <Medallion icon={icon} tone={tone} />}
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <SectionTitle id={headingId} level={level} truncate={2}>
              {title}
            </SectionTitle>
            {description && <Muted>{description}</Muted>}
          </div>
        </div>
        {actions && (
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            {actions}
          </div>
        )}
      </div>
      {children}
    </section>
  )
}
