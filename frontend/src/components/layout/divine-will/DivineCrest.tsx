import { type CSSProperties, useId } from 'react'
import emblemUrl from '@/assets/divine-will/emblem.webp'
import { cn } from '@/lib/utils'
import { Ornament } from '@/components/ui/ornate'

const SHIELD =
  'M0.1 0.07 Q0.3 0.1 0.5 0.025 Q0.7 0.1 0.9 0.07 Q0.98 0.07 0.98 0.15 L0.98 0.42 C0.98 0.7 0.78 0.88 0.5 1 C0.22 0.88 0.02 0.7 0.02 0.42 L0.02 0.15 Q0.02 0.07 0.1 0.07 Z'

const SIZE_CLASS = {
  fill: 'will-emblem-fill',
  md: 'will-emblem-md',
  sm: 'will-emblem-sm',
  icon: 'will-emblem-icon',
} as const

const TONE_CLASS = {
  gold: null,
  warning: 'will-emblem-warning',
  danger: 'will-emblem-danger',
} as const

export function DivineCrest({
  size = 'fill',
  tone = 'gold',
}: {
  size?: keyof typeof SIZE_CLASS
  tone?: keyof typeof TONE_CLASS
}) {
  const shape = `${useId().replaceAll(':', '')}-shield`
  const style = { '--emblem-shape': `url(#${shape})` } as CSSProperties
  return (
    <span
      aria-hidden='true'
      data-domain='divine-crest'
      className={cn('will-emblem', SIZE_CLASS[size], TONE_CLASS[tone])}
      style={style}
    >
      <svg className='will-emblem-defs' focusable='false'>
        <clipPath id={shape} clipPathUnits='objectBoundingBox'>
          <path d={SHIELD} />
        </clipPath>
      </svg>
      <Ornament src={emblemUrl} className='will-emblem-art' />
      <span className='will-emblem-sheen' />
    </span>
  )
}
