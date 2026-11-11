import { useId } from 'react'
import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'

type Schema = components['schemas']
type Ink = Schema['ArmsInk']
export type ArmsDrawing = Schema['ArmsDrawingView']

const FILLS: Record<Ink, string> = {
  gold: 'fill-tincture-gold',
  silver: 'fill-tincture-silver',
  red: 'fill-tincture-red',
  blue: 'fill-tincture-blue',
  green: 'fill-tincture-green',
  black: 'fill-tincture-black',
  purple: 'fill-tincture-purple',
  orange: 'fill-tincture-orange',
  celeste: 'fill-tincture-celeste',
  murrey: 'fill-tincture-murrey',
  rose: 'fill-tincture-rose',
  brown: 'fill-tincture-brown',
  grey: 'fill-tincture-grey',
  line: 'fill-tincture-line',
}

const STROKES: Record<Ink, string> = {
  gold: 'stroke-tincture-gold',
  silver: 'stroke-tincture-silver',
  red: 'stroke-tincture-red',
  blue: 'stroke-tincture-blue',
  green: 'stroke-tincture-green',
  black: 'stroke-tincture-black',
  purple: 'stroke-tincture-purple',
  orange: 'stroke-tincture-orange',
  celeste: 'stroke-tincture-celeste',
  murrey: 'stroke-tincture-murrey',
  rose: 'stroke-tincture-rose',
  brown: 'stroke-tincture-brown',
  grey: 'stroke-tincture-grey',
  line: 'stroke-tincture-line',
}

const SIZES = {
  sm: 'size-portrait-md',
  md: 'size-portrait-lg',
  lg: 'size-portrait-xl',
} as const

export function ArmsShield({
  drawing,
  label,
  size = 'md',
}: {
  drawing: ArmsDrawing
  label: string
  size?: keyof typeof SIZES
}) {
  const id = useId().replace(/[^a-zA-Z0-9-]/g, '')
  const outline = `${id}-outline`
  const layers = drawing.layers.map((layer, index) => ({
    ...layer,
    key: `${id}-layer-${index}`,
  }))
  return (
    <svg
      viewBox={drawing.view_box}
      role='img'
      aria-label={label}
      className={cn('shrink-0 drop-shadow-sm', SIZES[size])}
    >
      <defs>
        <clipPath id={outline}>
          <path d={drawing.outline} />
        </clipPath>
        {layers.map((layer) =>
          layer.clip === null ? null : (
            <clipPath
              key={layer.key}
              id={`${layer.key}-clip`}
              clipRule={layer.evenodd ? 'evenodd' : 'nonzero'}
            >
              <path d={layer.clip} />
            </clipPath>
          )
        )}
      </defs>
      {layers.map((layer) => (
        <g
          key={layer.key}
          clipPath={layer.clipped ? `url(#${outline})` : undefined}
        >
          <path
            d={layer.d}
            fill={layer.filled ? undefined : 'none'}
            fillRule={layer.evenodd ? 'evenodd' : 'nonzero'}
            strokeWidth={layer.filled ? undefined : layer.width}
            strokeLinecap='round'
            strokeLinejoin='round'
            opacity={layer.opacity < 1 ? layer.opacity : undefined}
            transform={layer.transform ?? undefined}
            clipPath={
              layer.clip === null ? undefined : `url(#${layer.key}-clip)`
            }
            className={layer.filled ? FILLS[layer.ink] : STROKES[layer.ink]}
          />
        </g>
      ))}
    </svg>
  )
}
