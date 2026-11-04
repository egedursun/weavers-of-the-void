import { useEffect, useState } from 'react'
import { type ProgressTone } from '@/components/ui/progress'
import { type KpiTone } from '@/components/domain'

export const WORKING = 'Working on it.'

export const TONE_COLOR: Record<KpiTone, string> = {
  gold: 'var(--primary)',
  verdigris: 'var(--color-brand-verdigris)',
  info: 'var(--color-info)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-destructive)',
  muted: 'var(--muted-foreground)',
}

export const METER_TONE: Record<KpiTone, ProgressTone> = {
  gold: 'default',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
}

export function goodTone(value: number, high = 65, low = 35): KpiTone {
  if (value >= high) return 'success'
  if (value >= (high + low) / 2) return 'gold'
  if (value >= low) return 'warning'
  return 'danger'
}

export function badTone(value: number, high = 60, low = 30): KpiTone {
  if (value >= high) return 'danger'
  if (value >= low) return 'warning'
  if (value > 0) return 'gold'
  return 'success'
}

export const PIP_TONE: Record<KpiTone, string> = {
  gold: 'border-primary bg-primary',
  verdigris: 'border-brand-verdigris bg-brand-verdigris',
  info: 'border-info bg-info',
  success: 'border-success bg-success',
  warning: 'border-warning bg-warning',
  danger: 'border-destructive bg-destructive',
  muted: 'border-muted-foreground bg-muted-foreground',
}

export function useWidth() {
  const [node, setNode] = useState<Element | null>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (!node) return
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.round(entry.contentRect.width))
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [node])
  return [setNode, width] as const
}
