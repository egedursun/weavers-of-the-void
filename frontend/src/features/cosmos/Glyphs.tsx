import { useId } from 'react'
import { cn } from '@/lib/utils'
import { mediaUrl } from '@/features/images/media'
import { type StarType, type TravelMethod } from './api'
import {
  CLOSED_ROUTE_DASH,
  LEGEND_LINE_MAX_WIDTH,
  METHOD_LOOK,
  STAR_LOOK,
  cssVar,
} from './model/looks'
import { svgId } from './model/svgId'

const GLYPH_WIDTH = 28
const GLYPH_HEIGHT = 10
const DISC_VIEW = 32
const DISC_RADIUS = 15
const SWATCH_WIDTH = 10
const SWATCH_HEIGHT = 12

export function MethodGlyph({
  method,
  closed = false,
}: {
  method: TravelMethod
  closed?: boolean
}) {
  const look = METHOD_LOOK[method]
  const color = cssVar(look.token)
  const dash = closed ? CLOSED_ROUTE_DASH : look.dash
  const lift = look.curve * GLYPH_WIDTH
  const middle = GLYPH_HEIGHT / 2
  const path =
    look.curve === 0
      ? `M 3 ${middle} L ${GLYPH_WIDTH - 3} ${middle}`
      : `M 3 ${middle + 2} Q ${GLYPH_WIDTH / 2} ${middle + 2 - lift} ${GLYPH_WIDTH - 3} ${middle + 2}`
  return (
    <svg
      aria-hidden='true'
      viewBox={`0 0 ${GLYPH_WIDTH} ${GLYPH_HEIGHT}`}
      className='h-icon-sm w-control-md shrink-0'
    >
      <path
        d={path}
        fill='none'
        stroke={color}
        strokeWidth={Math.min(look.width, LEGEND_LINE_MAX_WIDTH)}
        strokeDasharray={dash.length ? dash.join(' ') : undefined}
        strokeLinecap='round'
        opacity={closed ? 0.5 : look.opacity}
      />
      {look.endRings && (
        <>
          <circle cx={3} cy={middle} r={2.2} fill='none' stroke={color} />
          <circle
            cx={GLYPH_WIDTH - 3}
            cy={middle}
            r={2.2}
            fill='none'
            stroke={color}
          />
        </>
      )}
    </svg>
  )
}

export function VoyageGlyph() {
  return (
    <svg
      aria-hidden='true'
      viewBox={`0 0 ${GLYPH_WIDTH} ${GLYPH_HEIGHT}`}
      className='h-icon-sm w-control-md shrink-0'
    >
      <path
        d={`M 4 ${GLYPH_HEIGHT / 2} L ${GLYPH_WIDTH - 8} ${GLYPH_HEIGHT / 2}`}
        stroke={cssVar('--cosmos-bone')}
        strokeWidth={1.2}
        strokeDasharray='2 3'
        opacity={0.6}
      />
      <path
        d={`M ${GLYPH_WIDTH - 10} 1.5 L ${GLYPH_WIDTH - 3} ${GLYPH_HEIGHT / 2} L ${GLYPH_WIDTH - 10} ${GLYPH_HEIGHT - 1.5} Z`}
        fill={cssVar('--cosmos-bone')}
      />
    </svg>
  )
}

const COVER_WIDTH = 160

function CoverDisc({
  cover,
  size,
  muted = false,
}: {
  cover: string
  size: 'sm' | 'md'
  muted?: boolean
}) {
  return (
    <img
      src={mediaUrl(cover, COVER_WIDTH) ?? undefined}
      alt=''
      aria-hidden='true'
      loading='lazy'
      decoding='async'
      className={cn(
        'shrink-0 rounded-full border object-cover',
        size === 'sm' ? 'size-portrait-sm' : 'size-control-lg',
        muted && 'opacity-45'
      )}
    />
  )
}

export function WorldDisc({
  palette,
  size = 'md',
  muted = false,
  cover = null,
}: {
  palette: string[]
  size?: 'sm' | 'md'
  muted?: boolean
  cover?: string | null
}) {
  const id = svgId(useId())
  if (cover) return <CoverDisc cover={cover} size={size} muted={muted} />
  const stops = [palette[4], palette[3], palette[1]].map(
    (color) => color ?? cssVar('--cosmos-fog')
  )
  return (
    <svg
      aria-hidden='true'
      viewBox={`0 0 ${DISC_VIEW} ${DISC_VIEW}`}
      className={
        size === 'sm' ? 'size-icon-lg shrink-0' : 'size-control-lg shrink-0'
      }
    >
      <defs>
        <radialGradient id={id} cx='35%' cy='32%' r='75%'>
          <stop offset='0%' stopColor={stops[0]} />
          <stop offset='55%' stopColor={stops[1]} />
          <stop offset='100%' stopColor={stops[2]} />
        </radialGradient>
      </defs>
      <circle
        cx={DISC_VIEW / 2}
        cy={DISC_VIEW / 2}
        r={DISC_RADIUS}
        fill={`url(#${id})`}
        opacity={muted ? 0.45 : 1}
      />
    </svg>
  )
}

export function StarDisc({
  type,
  cover = null,
}: {
  type: StarType
  cover?: string | null
}) {
  const id = svgId(useId())
  if (cover) return <CoverDisc cover={cover} size='md' />
  const look = STAR_LOOK[type]
  return (
    <svg
      aria-hidden='true'
      viewBox={`0 0 ${DISC_VIEW} ${DISC_VIEW}`}
      className='size-control-lg shrink-0'
    >
      <defs>
        <radialGradient id={id}>
          <stop offset='0%' stopColor={cssVar(look.lightToken)} />
          <stop offset='45%' stopColor={cssVar(look.token)} />
          <stop offset='100%' stopColor={cssVar(look.edgeToken)} />
        </radialGradient>
      </defs>
      <circle
        cx={DISC_VIEW / 2}
        cy={DISC_VIEW / 2}
        r={DISC_RADIUS}
        fill={`url(#${id})`}
      />
    </svg>
  )
}

export function PaletteStrip({
  palette,
  label,
}: {
  palette: string[]
  label: string
}) {
  return (
    <svg
      role='img'
      aria-label={label}
      viewBox={`0 0 ${SWATCH_WIDTH * Math.max(palette.length, 1)} ${SWATCH_HEIGHT}`}
      preserveAspectRatio='none'
      className='h-meter-md w-full min-w-0 overflow-hidden rounded-full'
    >
      {palette.map((color, index) => (
        <rect
          key={`${color}-${index}`}
          x={index * SWATCH_WIDTH}
          y={0}
          width={SWATCH_WIDTH + 0.5}
          height={SWATCH_HEIGHT}
          fill={color}
        />
      ))}
    </svg>
  )
}
