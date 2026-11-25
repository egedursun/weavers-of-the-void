import { type ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Divider } from '@/components/ui/ornate'
import { Label, Muted, PageTitle } from '@/components/typography'
import { Medallion } from './KpiTile'

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
  icon,
  actions,
  meta,
}: PageHeaderProps) {
  return (
    <header
      data-domain='page-header'
      className='@container/page-header min-w-0'
    >
      <div className='grid min-w-0 grid-cols-1 gap-y-2 @3xl/page-header:grid-cols-[minmax(0,1fr)_auto] @3xl/page-header:gap-x-6'>
        {eyebrow && <Label variant='overline'>{eyebrow}</Label>}
        <div className='flex min-w-0 items-center gap-4 @3xl/page-header:col-start-1'>
          {icon && <Medallion icon={icon} tone='gold' />}
          <div className='flex min-w-0 flex-col gap-1'>
            <PageTitle truncate={2} className='text-gilded'>
              {title}
            </PageTitle>
            <Divider className='w-64' />
          </div>
        </div>
        {description && (
          <Muted className='max-w-reading @3xl/page-header:col-start-1'>
            {description}
          </Muted>
        )}
        {meta && (
          <div className='flex min-w-0 flex-wrap items-center gap-2 @3xl/page-header:col-start-1'>
            {meta}
          </div>
        )}
        {actions && (
          <div
            className={cn(
              'flex min-w-0 flex-wrap items-center gap-2 pt-2 @3xl/page-header:col-start-2 @3xl/page-header:justify-end @3xl/page-header:self-center @3xl/page-header:pt-0',
              eyebrow
                ? '@3xl/page-header:row-start-2'
                : '@3xl/page-header:row-start-1'
            )}
          >
            {actions}
          </div>
        )}
      </div>
    </header>
  )
}
