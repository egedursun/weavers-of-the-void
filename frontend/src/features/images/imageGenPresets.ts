import {
  Gem,
  type LucideIcon,
  MonitorPlay,
  RectangleHorizontal,
  RectangleVertical,
  Smartphone,
  Square,
  Tv,
  Zap,
} from 'lucide-react'

export const DIMENSION_MULTIPLE = 16

export type ResolutionKey = '480p' | '720p' | '1080p' | '2k' | '4k'
export type AspectKey = 'square' | 'portrait' | 'landscape' | 'wide' | 'tall'

export type Resolution = {
  value: ResolutionKey
  label: string
  hint: string
  icon: LucideIcon
  short: number
}

export type Aspect = {
  value: AspectKey
  label: string
  hint: string
  icon: LucideIcon
  ratio: number
}

export const RESOLUTIONS: readonly Resolution[] = [
  {
    value: '480p',
    label: '480p',
    hint: 'Quick sketches',
    icon: Zap,
    short: 480,
  },
  {
    value: '720p',
    label: '720p',
    hint: 'The studio default',
    icon: MonitorPlay,
    short: 720,
  },
  {
    value: '1080p',
    label: '1080p',
    hint: 'Full HD detail',
    icon: Tv,
    short: 1080,
  },
  { value: '2k', label: '2K', hint: 'Sharp for print', icon: Gem, short: 1440 },
  {
    value: '4k',
    label: '4K',
    hint: 'Slow, very large',
    icon: Gem,
    short: 2160,
  },
]

export const ASPECTS: readonly Aspect[] = [
  {
    value: 'square',
    label: 'Square',
    hint: '1:1 portraits and covers',
    icon: Square,
    ratio: 1,
  },
  {
    value: 'portrait',
    label: 'Portrait',
    hint: '3:4 figures',
    icon: RectangleVertical,
    ratio: 3 / 4,
  },
  {
    value: 'landscape',
    label: 'Landscape',
    hint: '4:3 places',
    icon: RectangleHorizontal,
    ratio: 4 / 3,
  },
  {
    value: 'wide',
    label: 'Wide',
    hint: '16:9 vistas',
    icon: RectangleHorizontal,
    ratio: 16 / 9,
  },
  {
    value: 'tall',
    label: 'Tall',
    hint: '9:16 towers and banners',
    icon: Smartphone,
    ratio: 9 / 16,
  },
]

function snap(value: number): number {
  return Math.max(
    DIMENSION_MULTIPLE,
    Math.round(value / DIMENSION_MULTIPLE) * DIMENSION_MULTIPLE
  )
}

export function dimensionsOf(
  resolution: Resolution,
  aspect: Aspect
): { width: number; height: number } {
  const short = snap(resolution.short)
  if (aspect.ratio >= 1)
    return { width: snap(resolution.short * aspect.ratio), height: short }
  return { width: short, height: snap(resolution.short / aspect.ratio) }
}

export function matchPreset(
  width: number,
  height: number
): { resolution: Resolution; aspect: Aspect } | null {
  for (const resolution of RESOLUTIONS)
    for (const aspect of ASPECTS) {
      const size = dimensionsOf(resolution, aspect)
      if (size.width === width && size.height === height)
        return { resolution, aspect }
    }
  return null
}

export function stepLevel(steps: number): string {
  if (steps <= 4) return 'Fast'
  if (steps <= 9) return 'Balanced'
  if (steps <= 20) return 'Detailed'
  return 'Exhaustive'
}
