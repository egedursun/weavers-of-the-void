import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type PanelGridProps = {
  children: ReactNode
  columns?: 2 | 3
}

export function PanelGrid({ children, columns = 2 }: PanelGridProps) {
  return (
    <div
      data-domain='panel-grid'
      className={cn(
        'grid min-w-0 grid-cols-1 items-stretch gap-x-2 gap-y-1',
        columns === 2 &&
          'lg:grid-cols-2 lg:[&>*:last-child:nth-child(odd)]:col-span-2',
        columns === 3 &&
          'lg:grid-cols-2 xl:grid-cols-3 lg:[&>*:last-child:nth-child(odd)]:col-span-2 xl:[&>*:last-child:nth-child(odd)]:col-span-1'
      )}
    >
      {children}
    </div>
  )
}
