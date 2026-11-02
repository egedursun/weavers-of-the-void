import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type ThemeColorName } from '@/components/domain/useThemeColors'
import { type FamilyShape } from '@/features/graph/families'

const GLYPH = 14
const HALF = GLYPH / 2

function tokenVar(token: ThemeColorName): string {
  return `var(--${token})`
}

export function ColorSwatch({
  token,
  color,
}: {
  token?: ThemeColorName | null
  color?: string
}) {
  return (
    <span
      aria-hidden='true'
      className='size-icon-sm shrink-0 rounded-sm border border-foreground/20'
      style={{ background: token ? tokenVar(token) : color }}
    />
  )
}

export function HatchSwatch() {
  return (
    <svg
      aria-hidden='true'
      className='size-icon-sm shrink-0 rounded-sm border border-foreground/20'
      viewBox='0 0 12 12'
    >
      {[-6, 0, 6, 12].map((offset) => (
        <line
          key={offset}
          x1={offset}
          y1={12}
          x2={offset + 12}
          y2={0}
          style={{
            stroke: 'var(--foreground)',
            strokeWidth: 1.2,
            opacity: 0.6,
          }}
        />
      ))}
    </svg>
  )
}

export function BorderMarker() {
  return (
    <svg
      aria-hidden='true'
      className='h-icon-md w-6 shrink-0'
      viewBox='0 0 24 14'
    >
      <line
        x1={1}
        y1={7}
        x2={23}
        y2={7}
        style={{
          stroke: 'var(--background)',
          strokeWidth: 4,
          strokeLinecap: 'round',
        }}
      />
      <line
        x1={1}
        y1={7}
        x2={23}
        y2={7}
        style={{
          stroke: 'var(--foreground)',
          strokeWidth: 1.8,
          strokeLinecap: 'round',
        }}
      />
    </svg>
  )
}

export function ClusterMarker() {
  return (
    <svg
      aria-hidden='true'
      className='size-icon-lg shrink-0'
      viewBox='-12 -12 24 24'
    >
      <circle
        r={9}
        style={{
          fill: 'none',
          stroke: 'var(--chart-3)',
          strokeWidth: 2.4,
          strokeDasharray: '20 40',
        }}
      />
      <circle
        r={9}
        style={{
          fill: 'none',
          stroke: 'var(--brand-gold)',
          strokeWidth: 2.4,
          strokeDasharray: '0 20 37 0',
        }}
      />
      <circle r={6} style={{ fill: 'var(--brand-gold)' }} />
    </svg>
  )
}

export function GlowMarker() {
  return (
    <span
      aria-hidden='true'
      className='size-icon-lg shrink-0 rounded-full'
      style={{
        background:
          'radial-gradient(circle, var(--destructive) 0%, transparent 70%)',
      }}
    />
  )
}

function shapePoints(
  sides: number,
  radius: number,
  start = -Math.PI / 2
): string {
  return Array.from({ length: sides }, (_, index) => {
    const angle = start + (index * 2 * Math.PI) / sides
    return `${(radius * Math.cos(angle)).toFixed(2)},${(radius * Math.sin(angle)).toFixed(2)}`
  }).join(' ')
}

function starPoints(radius: number): string {
  return Array.from({ length: 10 }, (_, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI) / 5
    const reach = index % 2 ? radius * 0.5 : radius * 1.15
    return `${(reach * Math.cos(angle)).toFixed(2)},${(reach * Math.sin(angle)).toFixed(2)}`
  }).join(' ')
}

export function ShapeMarker({
  shape,
  token,
}: {
  shape: FamilyShape
  token: ThemeColorName
}) {
  const color = tokenVar(token)
  const radius = HALF * 0.62
  const fill = { fill: color }
  let body
  switch (shape) {
    case 'square':
      body = (
        <rect
          x={-radius}
          y={-radius}
          width={radius * 2}
          height={radius * 2}
          style={fill}
        />
      )
      break
    case 'triangle':
      body = <polygon points={shapePoints(3, radius * 1.25)} style={fill} />
      break
    case 'diamond':
      body = <polygon points={shapePoints(4, radius * 1.2)} style={fill} />
      break
    case 'hexagon':
      body = <polygon points={shapePoints(6, radius * 1.05, 0)} style={fill} />
      break
    case 'star':
      body = <polygon points={starPoints(radius)} style={fill} />
      break
    case 'plus':
      body = (
        <path
          d={`M${-radius * 0.35} ${-radius}H${radius * 0.35}V${-radius * 0.35}H${radius}V${radius * 0.35}H${radius * 0.35}V${radius}H${-radius * 0.35}V${radius * 0.35}H${-radius}V${-radius * 0.35}H${-radius * 0.35}Z`}
          style={fill}
        />
      )
      break
    case 'ring':
      body = (
        <circle
          r={radius * 0.85}
          style={{ fill: 'none', stroke: color, strokeWidth: 1.8 }}
        />
      )
      break
    default:
      body = <circle r={radius} style={fill} />
  }
  return (
    <svg
      aria-hidden='true'
      className='size-icon-md shrink-0'
      viewBox={`${-HALF} ${-HALF} ${GLYPH} ${GLYPH}`}
    >
      {body}
    </svg>
  )
}

export function RingMarker({
  token,
  dashed = false,
  double = false,
  dot = false,
}: {
  token: ThemeColorName
  dashed?: boolean
  double?: boolean
  dot?: boolean
}) {
  const stroke = tokenVar(token)
  return (
    <svg
      aria-hidden='true'
      className='size-icon-md shrink-0'
      viewBox={`${-HALF} ${-HALF} ${GLYPH} ${GLYPH}`}
    >
      <circle
        r={HALF - 1.5}
        style={{
          fill: 'none',
          stroke,
          strokeWidth: 1.5,
          strokeDasharray: dashed ? '2 2' : undefined,
        }}
      />
      {double && (
        <circle
          r={HALF - 3.5}
          style={{ fill: 'none', stroke, strokeWidth: 1.2 }}
        />
      )}
      {dot && <circle r={1.8} style={{ fill: stroke }} />}
    </svg>
  )
}

export function LineMarker({
  token,
  width,
  dash,
}: {
  token: ThemeColorName
  width: number
  dash?: string
}) {
  return (
    <svg
      aria-hidden='true'
      className='h-icon-md w-6 shrink-0'
      viewBox='0 0 24 14'
    >
      <line
        x1={1}
        y1={7}
        x2={23}
        y2={7}
        style={{
          stroke: tokenVar(token),
          strokeWidth: width,
          strokeDasharray: dash,
          strokeLinecap: 'round',
        }}
      />
    </svg>
  )
}

const TOKEN_FILL: Partial<Record<ThemeColorName, string>> = {
  'chart-2': 'bg-chart-2',
  'chart-3': 'bg-chart-3',
  'chart-4': 'bg-chart-4',
  'chart-5': 'bg-chart-5',
  'rarity-legendary': 'bg-rarity-legendary',
  'rarity-uncommon': 'bg-rarity-uncommon',
  destructive: 'bg-destructive',
  warning: 'bg-warning',
  'muted-foreground': 'bg-muted-foreground',
  'brand-gold': 'bg-brand-gold',
  primary: 'bg-primary',
}

export function IconMarker({
  icon: Icon,
  token,
}: {
  icon: LucideIcon
  token: ThemeColorName
}) {
  return (
    <span
      aria-hidden='true'
      className={cn(
        'flex size-icon-lg shrink-0 items-center justify-center rounded-full ring-1 ring-background',
        TOKEN_FILL[token] ?? 'bg-muted-foreground'
      )}
    >
      <Icon className='size-icon-xs text-background' strokeWidth={2.6} />
    </span>
  )
}
