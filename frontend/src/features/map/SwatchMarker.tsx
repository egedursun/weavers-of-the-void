import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type ThemeColorName } from '@/components/domain/useThemeColors'

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
