import type { components } from '@/api/generated/schema'

type Part = components['schemas']['PartView']

export const FULL_LOSS = 100

export type DrawState =
  | 'unhurt'
  | 'open'
  | 'festering'
  | 'scarred'
  | 'lasting'
  | 'lost'
  | 'prosthesis'
  | 'fatal'

export const DRAW_STATES: { state: DrawState; label: string }[] = [
  { state: 'unhurt', label: 'Unhurt' },
  { state: 'open', label: 'Open wound' },
  { state: 'festering', label: 'Festering' },
  { state: 'scarred', label: 'Scarred' },
  { state: 'lasting', label: 'Lasting harm' },
  { state: 'lost', label: 'Lost' },
  { state: 'prosthesis', label: 'Prosthesis' },
  { state: 'fatal', label: 'Fatal' },
]

export const DRAW_LABELS = Object.fromEntries(
  DRAW_STATES.map((item) => [item.state, item.label])
) as Record<DrawState, string>

export function drawState(part: Part): DrawState {
  if (part.state === 'lethal') return 'fatal'
  if (part.prosthesis) return 'prosthesis'
  if (part.state === null) return 'unhurt'
  if (part.state === 'infected') return 'festering'
  if (part.state === 'fresh' || part.state === 'healing') return 'open'
  if (part.state === 'permanent')
    return part.loss >= FULL_LOSS ? 'lost' : 'lasting'
  return 'scarred'
}

const TONES: Record<DrawState, string> = {
  unhurt: 'fill-muted stroke-border',
  open: 'fill-warning/40 stroke-warning',
  festering: 'fill-destructive/45 stroke-destructive',
  scarred: 'fill-success/30 stroke-success',
  lasting: 'fill-muted-foreground/35 stroke-muted-foreground',
  lost: 'fill-transparent stroke-destructive',
  prosthesis: 'fill-primary/40 stroke-primary',
  fatal: 'fill-destructive stroke-destructive',
}

export function partTone(part: Part): string {
  return TONES[drawState(part)]
}

export function isLost(part: Part): boolean {
  return drawState(part) === 'lost'
}

export const CALLOUT_GAP = 30
const CALLOUT_EDGE = 14

export function calloutSpots(anchors: number[], height: number): number[] {
  const spots: number[] = []
  let last = -Infinity
  for (const anchor of anchors) {
    const spot = Math.max(anchor, last + CALLOUT_GAP, CALLOUT_EDGE)
    spots.push(spot)
    last = spot
  }
  const overflow = (spots.at(-1) ?? 0) - (height - CALLOUT_EDGE)
  if (overflow <= 0) return spots
  const shifted = spots.map((spot) => spot - overflow)
  for (let index = shifted.length - 2; index >= 0; index -= 1)
    shifted[index] = Math.min(shifted[index], shifted[index + 1] - CALLOUT_GAP)
  return shifted
}
