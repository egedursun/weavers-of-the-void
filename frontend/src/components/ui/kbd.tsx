import * as React from 'react'
import { cn } from '@/lib/utils'

function Kbd({ className, ...props }: React.ComponentProps<'kbd'>) {
  return (
    <kbd
      data-slot='kbd'
      className={cn(
        'pointer-events-none inline-flex h-badge-sm min-w-badge-sm shrink-0 items-center justify-center gap-0.5 rounded-sm border bg-muted px-1 [font-family:inherit] text-overline font-medium text-muted-foreground select-none',
        className
      )}
      {...props}
    />
  )
}

export { Kbd }
