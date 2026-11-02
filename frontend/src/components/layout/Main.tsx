import { type ReactNode } from 'react'
import { useMatches } from '@tanstack/react-router'
import { cn } from '@/lib/utils'

export function Main({ children }: { children: ReactNode }) {
  const layout = useMatches({
    select: (matches) => matches.at(-1)?.staticData.layout ?? 'page',
  })
  return (
    <div
      id='content'
      data-layout={layout}
      className={cn(
        'flex min-h-0 min-w-0 flex-1 flex-col',
        layout === 'page' && 'px-4 py-6 md:px-6 md:py-8'
      )}
    >
      <div
        className={cn(
          'flex min-w-0 flex-1 flex-col gap-8',
          layout === 'page' && 'mx-auto w-full max-w-6xl'
        )}
      >
        {children}
      </div>
    </div>
  )
}
