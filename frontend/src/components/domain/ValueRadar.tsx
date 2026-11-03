import { Label, Muted } from '@/components/typography'

export type RadarAxis = {
  key: string
  label: string
  value: number
  reference?: number | null
}

type ValueRadarProps = {
  axes: RadarAxis[]
  min?: number
  max?: number
  label: string
  referenceLabel?: string | null
}

const SIZE = 320
const CENTER = SIZE / 2
const RADIUS = 104
const LABEL_RADIUS = 128
const RINGS = [0.25, 0.5, 0.75, 1]
const DOT = 3
const FULL_TURN = Math.PI * 2
const START = -Math.PI / 2
const LABEL_SHIFT = 4
const PAD = 84

function point(index: number, count: number, share: number): [number, number] {
  const angle = START + (FULL_TURN * index) / count
  return [
    CENTER + Math.cos(angle) * RADIUS * share,
    CENTER + Math.sin(angle) * RADIUS * share,
  ]
}

function share(value: number, min: number, max: number): number {
  return Math.max(0, Math.min(1, (value - min) / (max - min)))
}

function path(points: [number, number][]): string {
  return `${points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')} Z`
}

function anchor(x: number): 'start' | 'middle' | 'end' {
  if (Math.abs(x - CENTER) < LABEL_SHIFT * 2) return 'middle'
  return x > CENTER ? 'start' : 'end'
}

export function ValueRadar({
  axes,
  min = -100,
  max = 100,
  label,
  referenceLabel,
}: ValueRadarProps) {
  const count = axes.length
  if (count < 3) return null
  const own = axes.map((axis, index) =>
    point(index, count, share(axis.value, min, max))
  )
  const hasReference = axes.some(
    (axis) => axis.reference !== null && axis.reference !== undefined
  )
  const reference = axes.map((axis, index) =>
    point(index, count, share(axis.reference ?? 0, min, max))
  )
  const zero = share(0, min, max)
  return (
    <figure
      data-domain='value-radar'
      className='flex min-w-0 flex-col items-center gap-2'
    >
      <svg
        viewBox={`${-PAD} 0 ${SIZE + PAD * 2} ${SIZE}`}
        role='img'
        aria-label={label}
        className='h-auto w-full max-w-md'
      >
        <title>{label}</title>
        {RINGS.map((ring) => (
          <path
            key={ring}
            d={path(axes.map((_, index) => point(index, count, ring)))}
            className='fill-none stroke-border'
            strokeWidth={1}
          />
        ))}
        <path
          d={path(axes.map((_, index) => point(index, count, zero)))}
          className='fill-none stroke-muted-foreground/50'
          strokeDasharray='2 3'
          strokeWidth={1}
        />
        {axes.map((axis, index) => {
          const [x, y] = point(index, count, 1)
          return (
            <line
              key={axis.key}
              x1={CENTER}
              y1={CENTER}
              x2={x}
              y2={y}
              className='stroke-border'
              strokeWidth={1}
            />
          )
        })}
        {hasReference && (
          <path
            d={path(reference)}
            className='fill-muted-foreground/10 stroke-muted-foreground'
            strokeDasharray='4 3'
            strokeWidth={1.5}
          />
        )}
        <path
          d={path(own)}
          className='fill-primary/20 stroke-primary'
          strokeWidth={2}
          strokeLinejoin='round'
        />
        {own.map(([x, y], index) => (
          <circle
            key={axes[index].key}
            cx={x}
            cy={y}
            r={DOT}
            className='fill-primary'
          >
            <title>{`${axes[index].label}: ${axes[index].value}`}</title>
          </circle>
        ))}
        {axes.map((axis, index) => {
          const angle = START + (FULL_TURN * index) / count
          const x = CENTER + Math.cos(angle) * LABEL_RADIUS
          const y = CENTER + Math.sin(angle) * LABEL_RADIUS + LABEL_SHIFT
          return (
            <text
              key={axis.key}
              x={x}
              y={y}
              textAnchor={anchor(x)}
              className='fill-muted-foreground text-caption'
            >
              {axis.label}
            </text>
          )
        })}
      </svg>
      <figcaption className='flex flex-wrap items-center justify-center gap-3'>
        <span className='flex items-center gap-1.5'>
          <svg aria-hidden='true' viewBox='0 0 12 4' className='h-1 w-3'>
            <rect width='12' height='4' className='fill-primary' />
          </svg>
          <Label as='span'>{label}</Label>
        </span>
        {hasReference && referenceLabel && (
          <span className='flex items-center gap-1.5'>
            <svg aria-hidden='true' viewBox='0 0 12 4' className='h-1 w-3'>
              <rect width='12' height='4' className='fill-muted-foreground' />
            </svg>
            <Muted as='span' variant='caption'>
              {referenceLabel}
            </Muted>
          </span>
        )}
      </figcaption>
    </figure>
  )
}
