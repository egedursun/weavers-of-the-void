import { useId, useState } from 'react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { type KpiTone } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Muted } from '@/components/typography'
import { type FoodWeb } from './api'
import { type PlacedEdge, layoutWeb } from './foodWebLayout'
import { DIET, named } from './labels'

const FILL: Record<KpiTone, string> = {
  gold: 'fill-primary',
  verdigris: 'fill-brand-verdigris',
  info: 'fill-info',
  success: 'fill-success',
  warning: 'fill-warning',
  danger: 'fill-destructive',
  muted: 'fill-muted-foreground',
}

export function FoodWebGraph({ web }: { web: FoodWeb }) {
  const layout = layoutWeb(web)
  const marker = useId()
  const drawer = useDrawerStack()
  const [focus, setFocus] = useState<number | null>(null)
  const byId = new Map(layout.nodes.map((node) => [node.id, node]))
  const linked = (edge: PlacedEdge) =>
    focus === null || edge.from === focus || edge.to === focus
  const near = new Set(
    focus === null
      ? []
      : layout.edges
          .filter((edge) => edge.from === focus || edge.to === focus)
          .flatMap((edge) => [edge.from, edge.to])
  )
  return (
    <figure data-surface='FoodWebLinks' className='flex min-w-0 flex-col gap-2'>
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className='h-auto w-full'
        role='img'
        aria-label={`Who eats whom among ${plural(layout.nodes.length, 'kind', 'kinds')} in ${plural(layout.tiers, 'tier', 'tiers')}, ${plural(layout.edges.length, 'hunt', 'hunts')}`}
      >
        <defs>
          <marker
            id={marker}
            viewBox='0 0 10 10'
            refX='9'
            refY='5'
            markerWidth='6'
            markerHeight='6'
            orient='auto-start-reverse'
          >
            <path d='M 0 0 L 10 5 L 0 10 z' className='fill-destructive' />
          </marker>
        </defs>
        {layout.edges.map((edge) => {
          const from = byId.get(edge.from)
          const to = byId.get(edge.to)
          if (!from || !to) return null
          const dx = to.x - from.x
          const dy = to.y - from.y
          const length = Math.max(1, Math.hypot(dx, dy))
          const x2 = to.x - (dx / length) * (to.r + 3)
          const y2 = to.y - (dy / length) * (to.r + 3)
          return (
            <line
              key={`${edge.from}-${edge.to}`}
              x1={from.x}
              y1={from.y}
              x2={x2}
              y2={y2}
              markerEnd={`url(#${marker})`}
              strokeWidth={edge.pinned ? 2.5 : 1.5}
              strokeDasharray={edge.pinned ? '6 4' : undefined}
              className={cn(
                'transition-opacity',
                edge.pinned ? 'stroke-primary' : 'stroke-destructive',
                linked(edge) ? 'opacity-80' : 'opacity-15'
              )}
            >
              <title>{`${from.name} hunts ${to.name}${edge.pinned ? ' (held by you)' : ''}`}</title>
            </line>
          )
        })}
        {layout.nodes.map((node) => {
          const diet = named(DIET, node.diet)
          const dim = focus !== null && node.id !== focus && !near.has(node.id)
          return (
            <g
              key={node.id}
              role='button'
              tabIndex={0}
              aria-label={`${node.name}, ${diet.label.toLowerCase()}`}
              className={cn(
                'cursor-pointer transition-opacity outline-none',
                dim ? 'opacity-30' : 'opacity-100'
              )}
              onMouseEnter={() => setFocus(node.id)}
              onMouseLeave={() => setFocus(null)}
              onFocus={() => setFocus(node.id)}
              onBlur={() => setFocus(null)}
              onClick={() =>
                drawer.open({ kind: 'entity', id: String(node.id) })
              }
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ')
                  drawer.open({ kind: 'entity', id: String(node.id) })
              }}
            >
              <circle
                cx={node.x}
                cy={node.y}
                r={node.r}
                className={cn(FILL[diet.tone ?? 'gold'], 'stroke-background')}
                strokeWidth={2}
              />
              <text
                x={node.x}
                y={
                  node.y +
                  node.r +
                  (node.crowded && node.slot % 2 === 1 ? 28 : 14)
                }
                textAnchor='middle'
                className='fill-foreground'
                fontSize={12}
              >
                {node.name}
              </text>
            </g>
          )
        })}
      </svg>
      <figcaption className='flex min-w-0 flex-col gap-1.5'>
        <span className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
          {[...new Set(layout.nodes.map((node) => node.diet))].map((diet) => {
            const spec = named(DIET, diet)
            return (
              <span key={diet} className='flex items-center gap-1.5'>
                <svg
                  viewBox='0 0 10 10'
                  aria-hidden='true'
                  className='size-icon-xs shrink-0'
                >
                  <circle
                    cx={5}
                    cy={5}
                    r={4.5}
                    className={FILL[spec.tone ?? 'gold']}
                  />
                </svg>
                <Muted as='span' variant='caption'>
                  {spec.label}
                </Muted>
              </span>
            )
          })}
        </span>
        <Muted as='span' variant='caption'>
          Hunters stand above their prey. Bigger circles are more numerous.
          Dashed gold hunts are held by you.
        </Muted>
      </figcaption>
    </figure>
  )
}
