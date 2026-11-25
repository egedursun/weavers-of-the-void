import { type ReactNode, useId } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Flourish, OrnateFrame, useInsideFrame } from '@/components/ui/ornate'
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
  surface,
  level = 2,
  id,
  icon,
  tone = 'gold',
  stretch = false,
}: SectionProps) {
  const headingId = useId()
  const inside = useInsideFrame()
  const framed = surface === 'card' || (surface === undefined && !inside)
  const layout = cn('flex min-w-0 flex-col gap-4', stretch && 'h-full')
  if (framed) {
    return (
      <OrnateFrame
        aria-labelledby={headingId}
        data-domain='section'
        className={cn(layout, 'gap-5 px-5 pb-9 text-card-foreground sm:px-9')}
        footCrest
        id={id}
        role='region'
        nameplate={
          <>
            {icon && <Medallion icon={icon} tone={tone} size='sm' />}
            <SectionTitle
              id={headingId}
              level={level}
              truncate={2}
              className='text-gilded'
            >
              {title}
            </SectionTitle>
          </>
        }
      >
        {(description || actions) && (
          <div className='flex min-w-0 flex-wrap items-center justify-between gap-x-4 gap-y-2'>
            {description ? (
              <Muted className='min-w-0 flex-1 basis-60'>{description}</Muted>
            ) : (
              <span aria-hidden='true' className='flex-1' />
            )}
            {actions && (
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                {actions}
              </div>
            )}
          </div>
        )}
        {children}
      </OrnateFrame>
    )
  }
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      data-domain='section'
      className={layout}
    >
      <div className='flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-2'>
        <div className='flex min-w-0 flex-1 basis-60 items-start gap-3'>
          {icon && <Medallion icon={icon} tone={tone} />}
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <SectionTitle
              id={headingId}
              level={level}
              truncate={2}
              className='text-gilded'
            >
              {title}
            </SectionTitle>
            {level === 2 && <Flourish />}
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
