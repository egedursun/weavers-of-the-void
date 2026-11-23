import type { components } from '@/api/generated/schema'
import { Muted } from '@/components/typography'
import { SEASON_WARMTH, SEASON_WATER } from './seasonLabels'

type Season = components['schemas']['SeasonView']

const SIZE = 240
const CENTER = SIZE / 2
const OUTER = 108
const INNER = 62
const FULL_TURN = Math.PI * 2
const START = -Math.PI / 2
const LABEL_RADIUS = (OUTER + INNER) / 2
const SHARE_TOTAL = 100

const WARMTH_FILL: Record<Season['warmth'], string> = {
  coldest: 'fill-info/70',
  cold: 'fill-info/45',
  cooling: 'fill-verdigris/40',
  even: 'fill-muted-foreground/25',
  warming: 'fill-success/40',
  warm: 'fill-warning/45',
  warmest: 'fill-warning/75',
}

function at(angle: number, radius: number): string {
  return `${(CENTER + Math.cos(angle) * radius).toFixed(2)},${(CENTER + Math.sin(angle) * radius).toFixed(2)}`
}

function segment(from: number, to: number): string {
  const large = to - from > Math.PI ? 1 : 0
  return [
    `M${at(from, OUTER)}`,
    `A${OUTER},${OUTER} 0 ${large} 1 ${at(to, OUTER)}`,
    `L${at(to, INNER)}`,
    `A${INNER},${INNER} 0 ${large} 0 ${at(from, INNER)}`,
    'Z',
  ].join(' ')
}

export function SeasonWheel({
  seasons,
  label,
}: {
  seasons: Season[]
  label: string
}) {
  const total =
    seasons.reduce((sum, season) => sum + season.share_pct, 0) || SHARE_TOTAL
  const arcs = seasons.reduce<{ season: Season; from: number; to: number }[]>(
    (found, season) => {
      const from = found.length === 0 ? START : found[found.length - 1].to
      const to =
        seasons.length === 1
          ? from + FULL_TURN - 0.0001
          : from + (FULL_TURN * season.share_pct) / total
      return [...found, { season, from, to }]
    },
    []
  )
  return (
    <figure
      data-domain='season-wheel'
      className='flex min-w-0 flex-col items-center gap-2'
    >
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role='img'
        aria-label={label}
        className='h-auto w-full max-w-xs'
      >
        <title>{label}</title>
        {arcs.map(({ season, from, to }) => {
          const middle = (from + to) / 2
          const [x, y] = at(middle, LABEL_RADIUS).split(',').map(Number)
          return (
            <g key={season.id}>
              <path
                d={segment(from, to)}
                className={`${WARMTH_FILL[season.warmth]} stroke-card`}
                strokeWidth={2}
              >
                <title>{`${season.name}: ${season.share_pct}% of the year, ${SEASON_WARMTH[season.warmth].label.toLowerCase()}, ${SEASON_WATER[season.water].label.toLowerCase()}`}</title>
              </path>
              <text
                x={x}
                y={y}
                textAnchor='middle'
                dominantBaseline='middle'
                fontSize={12}
                className='pointer-events-none fill-foreground'
              >
                {season.position + 1}
              </text>
            </g>
          )
        })}
      </svg>
      <Muted as='figcaption' variant='caption'>
        {label}
      </Muted>
    </figure>
  )
}
