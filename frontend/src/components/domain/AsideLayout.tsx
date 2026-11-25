import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type AsideLayoutProps = {
  children: ReactNode
  aside: ReactNode
  side?: 'start' | 'end'
  ratio?: 'third' | 'quarter'
}

export function AsideLayout({
  children,
  aside,
  side = 'end',
  ratio = 'third',
}: AsideLayoutProps) {
  const quarter = ratio === 'quarter'
  return (
    <div
      data-domain='aside-layout'
      className={cn(
        'grid min-w-0 grid-cols-1 items-start gap-x-2 gap-y-4',
        quarter ? 'lg:grid-cols-4' : 'xl:grid-cols-3'
      )}
    >
      <div
        className={cn(
          'flex min-w-0 flex-col gap-4',
          quarter ? 'lg:col-span-3' : 'xl:col-span-2',
          side === 'start' && 'order-2'
        )}
      >
        {children}
      </div>
      {aside && (
        <aside
          className={cn(
            'flex min-w-0 flex-col gap-4',
            quarter ? 'lg:sticky lg:top-topbar' : 'xl:sticky xl:top-topbar',
            side === 'start' && 'order-1'
          )}
        >
          {aside}
        </aside>
      )}
    </div>
  )
}
