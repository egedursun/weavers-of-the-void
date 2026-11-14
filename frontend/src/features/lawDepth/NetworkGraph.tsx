import { plural } from '@/lib/units'
import { Label, Muted } from '@/components/typography'
import { type AgentMotiveView, type CellView, type NodeLawView } from './api'
import { MOTIVES } from './labels'

const SIZE = 240
const CENTER = SIZE / 2
const CELL_RING = 70
const AGENT_RING = 28
const FLAT_RING = 90
const NODE_R = 12
const CELL_R = 8
const AGENT_R = 5

const MOTIVE_FILL: Record<AgentMotiveView['motive'], string> = {
  money: 'fill-warning stroke-warning',
  ideology: 'fill-success stroke-success',
  compromise: 'fill-destructive stroke-destructive',
  ego: 'fill-info stroke-info',
}

type Point = { x: number; y: number }

function around(
  center: Point,
  radius: number,
  index: number,
  count: number
): Point {
  const angle = (index / Math.max(1, count)) * Math.PI * 2 - Math.PI / 2
  return {
    x: center.x + Math.cos(angle) * radius,
    y: center.y + Math.sin(angle) * radius,
  }
}

function Graph({
  network,
  cells,
  agents,
}: {
  network: NodeLawView['networks'][number]
  cells: CellView[]
  agents: AgentMotiveView[]
}) {
  const hub = { x: CENTER, y: CENTER }
  const cellAt = new Map(
    cells.map((cell, index) => [
      cell.id,
      around(hub, CELL_RING, index, cells.length),
    ])
  )
  const loose = agents.filter(
    (agent) => agent.cell_id === null || !cellAt.has(agent.cell_id)
  )
  const owner = network.owner?.name ?? 'A spymaster'
  const target = network.target?.name ?? 'a target'
  return (
    <figure className='flex min-w-0 flex-col items-center gap-1'>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role='img'
        aria-label={`${owner} spying on ${target}: ${plural(cells.length, 'cell', 'cells')} and ${plural(agents.length, 'agent', 'agents')}`}
        className='block h-auto w-full max-w-xs'
      >
        {cells.map((cell) => {
          const at = cellAt.get(cell.id) ?? hub
          return (
            <line
              key={`link-${cell.id}`}
              x1={hub.x}
              y1={hub.y}
              x2={at.x}
              y2={at.y}
              className='stroke-border'
              strokeWidth={1.5}
            />
          )
        })}
        {agents.map((agent, index) => {
          const base =
            agent.cell_id !== null ? cellAt.get(agent.cell_id) : undefined
          const mates = base
            ? agents.filter((item) => item.cell_id === agent.cell_id)
            : loose
          const at = base
            ? around(base, AGENT_RING, mates.indexOf(agent), mates.length)
            : around(hub, FLAT_RING, loose.indexOf(agent), loose.length)
          const from = base ?? hub
          return (
            <g key={`agent-${agent.agent_id}-${index}`}>
              <line
                x1={from.x}
                y1={from.y}
                x2={at.x}
                y2={at.y}
                className='stroke-border'
                strokeWidth={1}
              />
              <circle
                cx={at.x}
                cy={at.y}
                r={AGENT_R}
                className={MOTIVE_FILL[agent.motive]}
              >
                <title>{`${agent.mortal?.name ?? 'An agent'}: ${MOTIVES[agent.motive].label.toLowerCase()}, loyalty ${agent.loyalty}`}</title>
              </circle>
            </g>
          )
        })}
        {cells.map((cell) => {
          const at = cellAt.get(cell.id) ?? hub
          return (
            <circle
              key={`cell-${cell.id}`}
              cx={at.x}
              cy={at.y}
              r={CELL_R}
              className='fill-muted stroke-foreground'
              strokeWidth={1.5}
            >
              <title>{`Cell ${cell.id}: ${cell.dead_drops} dead drops`}</title>
            </circle>
          )
        })}
        <circle
          cx={hub.x}
          cy={hub.y}
          r={NODE_R}
          className='fill-primary stroke-primary'
        >
          <title>{`${owner} in ${target}`}</title>
        </circle>
      </svg>
      <figcaption>
        <Muted variant='caption'>{`${owner} in ${target}`}</Muted>
      </figcaption>
    </figure>
  )
}

export function NetworkGraph({ data }: { data: NodeLawView }) {
  const networks = data.networks.filter((network) =>
    data.agents.some((agent) => agent.network_id === network.id)
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Spy networks</Label>
      {networks.length === 0 ? (
        <Muted variant='caption'>No spy network with agents works here.</Muted>
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            {networks.map((network) => (
              <Graph
                key={network.id}
                network={network}
                cells={data.cells.filter(
                  (cell) => cell.network_id === network.id
                )}
                agents={data.agents.filter(
                  (agent) => agent.network_id === network.id
                )}
              />
            ))}
          </div>
          <div className='flex min-w-0 flex-wrap gap-3'>
            {Object.entries(MOTIVES).map(([key, spec]) => {
              const Icon = spec.icon
              return (
                <Muted
                  key={key}
                  as='span'
                  variant='caption'
                  className='flex items-center gap-1'
                >
                  <Icon aria-hidden='true' className='size-icon-xs' />
                  {spec.label}
                </Muted>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
