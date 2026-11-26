import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function ControlCluster({
  children,
  label,
  className,
}: {
  children: ReactNode
  label?: string
  className?: string
}) {
  return (
    <div
      data-layout='control-cluster'
      role={label ? 'group' : undefined}
      aria-label={label}
      className={cn('flex items-center gap-1 rounded-lg border p-1', className)}
    >
      {children}
    </div>
  )
}
