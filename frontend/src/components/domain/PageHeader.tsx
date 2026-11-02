import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label, Muted, PageTitle } from '@/components/typography'

type PageHeaderProps = {
  title: string
  description?: string
  eyebrow?: string
  icon?: LucideIcon
  actions?: ReactNode
  meta?: ReactNode
}

export function PageHeader({
  title,
  description,
  eyebrow,
  icon: Icon,
  actions,
  meta,
}: PageHeaderProps) {
  return (
    <header
      data-domain='page-header'
      className='grid min-w-0 grid-cols-1 gap-y-2 md:grid-cols-[minmax(0,1fr)_auto] md:gap-x-6'
    >
      {eyebrow && <Label variant='overline'>{eyebrow}</Label>}
      <div className='flex min-w-0 items-center gap-3 md:col-start-1'>
        {Icon && (
          <span className='flex size-control-lg shrink-0 items-center justify-center rounded-lg border bg-card text-primary'>
            <Icon aria-hidden='true' className='size-icon-lg' />
          </span>
        )}
        <PageTitle truncate>{title}</PageTitle>
      </div>
      {description && (
        <Muted className='max-w-reading md:col-start-1'>{description}</Muted>
      )}
      {meta && (
        <div className='flex min-w-0 flex-wrap items-center gap-2 md:col-start-1'>
          {meta}
        </div>
      )}
      {actions && (
        <div
          className={cn(
            'flex min-w-0 flex-wrap items-center gap-2 pt-2 md:col-start-2 md:justify-end md:self-center md:pt-0',
            eyebrow ? 'md:row-start-2' : 'md:row-start-1'
          )}
        >
          {actions}
        </div>
      )}
    </header>
  )
}
