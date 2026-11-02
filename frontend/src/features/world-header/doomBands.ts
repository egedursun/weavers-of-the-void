export type DoomBandKey = 'calm' | 'omen' | 'warning' | 'apocalypse'

export type DoomBand = {
  key: DoomBandKey
  label: string
  from: number
  to: number | null
  tone: 'success' | 'secondary' | 'warning' | 'destructive'
  rule: string
}

type DoomInputs = {
  value: number
  threshold: number
  firstPct: number
  secondPct: number
}

const PERCENT = 100

function pointAt(threshold: number, pct: number): number {
  return Math.ceil((threshold * pct) / PERCENT)
}

export function doomBands({
  threshold,
  firstPct,
  secondPct,
}: Omit<DoomInputs, 'value'>): DoomBand[] {
  const first = pointAt(threshold, firstPct)
  const second = Math.max(pointAt(threshold, secondPct), first)
  return [
    {
      key: 'calm',
      label: 'Calm',
      from: 0,
      to: first - 1,
      tone: 'success',
      rule: 'apocalypse.warning_1_pct',
    },
    {
      key: 'omen',
      label: 'First omen',
      from: first,
      to: second - 1,
      tone: 'secondary',
      rule: 'apocalypse.warning_1_pct',
    },
    {
      key: 'warning',
      label: 'Final warning',
      from: second,
      to: threshold - 1,
      tone: 'warning',
      rule: 'apocalypse.warning_2_pct',
    },
    {
      key: 'apocalypse',
      label: 'Apocalypse',
      from: threshold,
      to: null,
      tone: 'destructive',
      rule: 'balance.apocalypse_threshold',
    },
  ]
}

export function currentBand(bands: DoomBand[], value: number): DoomBand {
  const reached = bands.filter((band) => value >= band.from)
  return reached[reached.length - 1] ?? bands[0]
}

export function bandRange(band: DoomBand): string {
  if (band.to === null) return `${band.from} and above`
  if (band.to < band.from) return 'none'
  return band.from === band.to
    ? String(band.from)
    : `${band.from} to ${band.to}`
}
