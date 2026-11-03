import type { components } from '@/api/generated/schema'

type Part = components['schemas']['PartView']

export const FULL_LOSS = 100

export function partTone(part: Part): string {
  if (part.prosthesis) return 'fill-primary/40 stroke-primary'
  if (part.state === null) return 'fill-muted stroke-border'
  if (part.state === 'infected') return 'fill-destructive/45 stroke-destructive'
  if (part.state === 'fresh' || part.state === 'healing')
    return 'fill-warning/40 stroke-warning'
  if (part.state === 'permanent' && part.loss >= FULL_LOSS)
    return 'fill-transparent stroke-destructive'
  if (part.state === 'permanent')
    return 'fill-muted-foreground/35 stroke-muted-foreground'
  return part.loss > 0
    ? 'fill-success/30 stroke-success'
    : 'fill-muted stroke-border'
}

export function isLost(part: Part): boolean {
  return (
    !part.prosthesis && part.state === 'permanent' && part.loss >= FULL_LOSS
  )
}

export const LEGEND: { label: string; className: string; dashed?: boolean }[] =
  [
    { label: 'Unhurt', className: 'fill-muted stroke-border' },
    { label: 'Open wound', className: 'fill-warning/40 stroke-warning' },
    { label: 'Festering', className: 'fill-destructive/45 stroke-destructive' },
    { label: 'Scarred', className: 'fill-success/30 stroke-success' },
    {
      label: 'Lasting harm',
      className: 'fill-muted-foreground/35 stroke-muted-foreground',
    },
    {
      label: 'Lost',
      className: 'fill-transparent stroke-destructive',
      dashed: true,
    },
    { label: 'Prosthesis', className: 'fill-primary/40 stroke-primary' },
  ]
