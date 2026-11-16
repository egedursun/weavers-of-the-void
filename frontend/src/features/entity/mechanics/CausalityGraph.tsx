import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { GitBranch } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { EmptyState, Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { loreKeys } from '../api/keys'
import { named } from '../environment/labels'
import { badgeVariant } from '../realm/labels'
import { INCIDENT_ROLE } from './labels'

type Graph = components['schemas']['CausalityView']
type CausalNode = components['schemas']['CausalNode']

const COLUMN = 190
const ROW = 64
const BOX_W = 160
const BOX_H = 44
const PAD = 16

export type Placed = { node: CausalNode; x: number; y: number }

export function linkedOnly(graph: Graph): Graph {
  const linked = new Set(
    graph.edges.flatMap((edge) => [edge.cause, edge.effect])
  )
  return { ...graph, nodes: graph.nodes.filter((node) => linked.has(node.id)) }
}

export function layoutCausality(graph: Graph): {
  placed: Placed[]
  width: number
  height: number
} {
  const present = new Set(graph.nodes.map((node) => node.id))
  const causeOf = new Map(
    graph.nodes.map((node) => [
      node.id,
      node.cause_incident_id !== null && present.has(node.cause_incident_id)
        ? node.cause_incident_id
        : null,
    ])
  )
  const depthOf = (id: number): number => {
    let depth = 0
    const seen = new Set<number>([id])
    let cause = causeOf.get(id) ?? null
    while (cause !== null && !seen.has(cause)) {
      seen.add(cause)
      depth += 1
      cause = causeOf.get(cause) ?? null
    }
    return depth
  }
  const ordered = [...graph.nodes].sort(
    (a, b) => a.epoch - b.epoch || a.id - b.id
  )
  const rows = new Map<number, number>()
  let columns = 1
  const placed = ordered.map((node) => {
    const at = depthOf(node.id)
    columns = Math.max(columns, at + 1)
    const row = rows.get(at) ?? 0
    rows.set(at, row + 1)
    return { node, x: PAD + at * COLUMN, y: PAD + row * ROW }
  })
  const tallest = Math.max(1, ...rows.values())
  return {
    placed,
    width: PAD * 2 + columns * COLUMN,
    height: PAD * 2 + tallest * ROW,
  }
}

function clip(text: string, size: number): string {
  return text.length > size ? `${text.slice(0, size - 1)}…` : text
}

const CAUSE_KEY = [
  { label: 'This record', className: 'border-border bg-card' },
  { label: 'Another record', className: 'border-border bg-muted' },
  { label: 'It was struck', className: 'border-destructive bg-muted' },
  { label: 'It acted', className: 'border-primary bg-muted' },
  {
    label: 'Cause across epochs',
    className:
      'h-0 border-dashed border-primary border-t-2 border-x-0 border-b-0 rounded-none',
  },
]

export function CausalityGraph({ nodeId }: { nodeId: number }) {
  const query = useQuery({
    queryKey: [...loreKeys.entity(nodeId), 'causality'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/causality', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
  const [chosen, setChosen] = useState<number | null>(null)
  const layout = useMemo(
    () => (query.data ? layoutCausality(linkedOnly(query.data)) : null),
    [query.data]
  )
  if (!query.data || !layout) return null
  if (query.data.edges.length === 0) {
    return (
      <EmptyState
        icon={GitBranch}
        title='No chains of cause yet'
        description='When something it took part in leads to something else, the chain appears here.'
      />
    )
  }
  const at = new Map(layout.placed.map((item) => [item.node.id, item]))
  const selected = chosen !== null ? at.get(chosen)?.node : undefined
  return (
    <div data-surface='CausalityGraph' className='flex min-w-0 flex-col gap-2'>
      <div className='min-w-0 overflow-x-auto rounded-md border surface-sheen border-gild/60 bg-card'>
        <svg
          role='img'
          aria-label='Causality graph'
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          width={layout.width}
          height={layout.height}
          className='block'
        >
          {query.data.edges.map((edge) => {
            const from = at.get(edge.cause)
            const to = at.get(edge.effect)
            if (!from || !to) return null
            const x1 = from.x + BOX_W
            const y1 = from.y + BOX_H / 2
            const x2 = to.x
            const y2 = to.y + BOX_H / 2
            const bend = Math.max(24, (x2 - x1) / 2)
            return (
              <path
                key={`${edge.cause}-${edge.effect}`}
                d={`M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`}
                className={cn(
                  'fill-none',
                  edge.span > 0 ? 'stroke-primary' : 'stroke-muted-foreground'
                )}
                strokeWidth={edge.span > 0 ? 2 : 1.5}
                strokeDasharray={edge.span > 0 ? '5 4' : undefined}
              />
            )
          })}
          {layout.placed.map(({ node, x, y }) => {
            const tone = node.role
              ? named(INCIDENT_ROLE, node.role).tone
              : undefined
            return (
              <g
                key={node.id}
                role='button'
                tabIndex={0}
                aria-label={node.text}
                aria-pressed={chosen === node.id}
                className='cursor-pointer outline-none'
                onClick={() => setChosen(node.id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ')
                    setChosen(node.id)
                }}
              >
                <rect
                  x={x}
                  y={y}
                  width={BOX_W}
                  height={BOX_H}
                  rx={8}
                  className={cn(
                    'stroke-border',
                    node.own ? 'fill-card' : 'fill-muted',
                    tone === 'danger' && 'stroke-destructive',
                    tone === 'success' && 'stroke-primary',
                    chosen === node.id && 'stroke-primary'
                  )}
                  strokeWidth={chosen === node.id ? 2.5 : 1}
                />
                <text
                  x={x + 8}
                  y={y + 18}
                  className='fill-foreground'
                  fontSize={11}
                >
                  {clip(node.text, 26)}
                </text>
                <text
                  x={x + 8}
                  y={y + 34}
                  className='fill-muted-foreground'
                  fontSize={11}
                >
                  {`Epoch ${node.epoch}${node.role ? ` · ${named(INCIDENT_ROLE, node.role).label.toLowerCase()}` : ''}`}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
        {CAUSE_KEY.map((entry) => (
          <span key={entry.label} className='flex items-center gap-1.5'>
            <span
              aria-hidden='true'
              className={cn(
                'h-3 w-5 shrink-0 rounded-sm border-2',
                entry.className
              )}
            />
            <Muted as='span' variant='caption'>
              {entry.label}
            </Muted>
          </span>
        ))}
      </div>
      <Muted variant='caption'>
        Each column is one more step of cause; dashed gold lines reach across
        epochs. Pick an incident to read it.
      </Muted>
      {selected && (
        <div className='flex min-w-0 items-start gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
          <Medallion
            icon={GitBranch}
            tone={selected.own ? 'gold' : 'info'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Text>{selected.text}</Text>
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <Badge size='sm' variant='outline'>
                {selected.year !== null
                  ? `Year ${selected.year} · epoch ${selected.epoch}`
                  : `Epoch ${selected.epoch}`}
              </Badge>
              {selected.role && (
                <Badge
                  size='sm'
                  variant={badgeVariant(
                    named(INCIDENT_ROLE, selected.role).tone
                  )}
                >
                  {named(INCIDENT_ROLE, selected.role).label}
                </Badge>
              )}
              <Badge
                size='sm'
                variant='warning'
              >{`Weight ${selected.magnitude}`}</Badge>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
