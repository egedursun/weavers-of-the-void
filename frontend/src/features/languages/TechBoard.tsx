import { type KeyboardEvent, useMemo } from 'react'
import { type KnowledgeView } from '@/features/entity/api/types'
import { BRANCH_ICON, tierNumeral } from './languageIcons'
import { TECH_NODE, clip, curve, layoutTech } from './treeLayout'

const NAME_LIMIT = 20
const BADGE_RADIUS = 16
const ICON_SIZE = 16
const BAR_INSET = 12
const BAR_HEIGHT = 4
const PERCENT = 100

function activate(event: KeyboardEvent, run: () => void) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    run()
  }
}

export function TechBoard({
  items,
  selected,
  onSelect,
}: {
  items: KnowledgeView[]
  selected: number | null
  onSelect: (id: number) => void
}) {
  const layout = useMemo(() => layoutTech(items), [items])
  const near = useMemo(() => {
    const ids = new Set<number>()
    for (const { from, to } of layout.links)
      if (
        from.item.knowledge.id === selected ||
        to.item.knowledge.id === selected
      ) {
        ids.add(from.item.knowledge.id)
        ids.add(to.item.knowledge.id)
      }
    return ids
  }, [layout.links, selected])
  const middle = TECH_NODE.height / 2
  return (
    <div className='max-h-200 min-w-0 overflow-auto rounded-md border surface-well border-gild/45 bg-muted/70'>
      <svg
        role='group'
        aria-label='Knowledge tree'
        width={layout.width}
        height={layout.height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className='block'
      >
        {layout.tiers.map(({ tier, x }) => (
          <g key={tier}>
            <rect
              x={x - TECH_NODE.column / 4}
              y={0}
              width={TECH_NODE.width + TECH_NODE.column / 2}
              height={layout.height}
              className='fill-background/60'
            />
            <text
              x={x + TECH_NODE.width / 2}
              y={TECH_NODE.header - 12}
              textAnchor='middle'
              fontSize={13}
              fontWeight={700}
              letterSpacing={2}
              className='fill-primary font-display'
            >
              {`TIER ${tierNumeral(tier)}`}
            </text>
          </g>
        ))}
        {layout.links.map(({ from, to }) => {
          const lit =
            selected !== null &&
            (from.item.knowledge.id === selected ||
              to.item.knowledge.id === selected)
          return (
            <path
              key={`${from.item.knowledge.id}-${to.item.knowledge.id}`}
              d={curve(
                { x: from.x + TECH_NODE.width, y: from.y + middle },
                { x: to.x, y: to.y + middle }
              )}
              fill='none'
              strokeWidth={lit ? 2.5 : 1.25}
              strokeLinecap='round'
              className={lit ? 'stroke-primary' : 'stroke-border'}
            />
          )
        })}
        {layout.nodes.map((placed) => {
          const item = placed.item
          const id = item.knowledge.id
          const active = id === selected
          const lost = item.knowers.length === 0
          const Icon = item.branch ? BRANCH_ICON[item.branch] : null
          const spread = Math.max(0, Math.min(PERCENT, item.spread ?? 0))
          const barWidth = TECH_NODE.width - BAR_INSET * 2
          return (
            <g
              key={id}
              transform={`translate(${placed.x} ${placed.y})`}
              role='button'
              tabIndex={0}
              aria-pressed={active}
              aria-label={`${item.knowledge.name}, tier ${placed.tier}`}
              className='cursor-pointer'
              opacity={selected !== null && !active && !near.has(id) ? 0.78 : 1}
              onClick={() => onSelect(id)}
              onKeyDown={(event) => activate(event, () => onSelect(id))}
            >
              <title>{item.knowledge.name}</title>
              <rect
                width={TECH_NODE.width}
                height={TECH_NODE.height}
                rx={12}
                strokeWidth={active ? 2 : 1}
                strokeDasharray={lost ? '4 3' : undefined}
                className={
                  active
                    ? 'fill-primary/12 stroke-primary'
                    : lost
                      ? 'fill-muted stroke-muted-foreground/50'
                      : 'fill-card stroke-border hover:stroke-primary/60'
                }
              />
              <circle
                cx={10 + BADGE_RADIUS}
                cy={middle - 6}
                r={BADGE_RADIUS}
                className={
                  lost
                    ? 'fill-muted stroke-border'
                    : 'fill-primary/12 stroke-primary/30'
                }
              />
              {Icon && (
                <Icon
                  x={10 + BADGE_RADIUS - ICON_SIZE / 2}
                  y={middle - 6 - ICON_SIZE / 2}
                  width={ICON_SIZE}
                  height={ICON_SIZE}
                  className={lost ? 'text-muted-foreground' : 'text-primary'}
                />
              )}
              <text
                x={18 + BADGE_RADIUS * 2}
                y={middle - 10}
                fontSize={13.5}
                fontWeight={600}
                className={
                  lost
                    ? 'fill-muted-foreground font-display'
                    : 'fill-foreground font-display'
                }
              >
                {clip(item.knowledge.name, NAME_LIMIT)}
              </text>
              <text
                x={18 + BADGE_RADIUS * 2}
                y={middle + 7}
                fontSize={11}
                className='fill-muted-foreground'
              >
                {lost
                  ? 'Forgotten'
                  : `${item.knowers.length} ${item.knowers.length === 1 ? 'keeper' : 'keepers'}`}
              </text>
              <rect
                x={BAR_INSET}
                y={TECH_NODE.height - BAR_INSET - BAR_HEIGHT / 2}
                width={barWidth}
                height={BAR_HEIGHT}
                rx={BAR_HEIGHT / 2}
                className='fill-muted'
              />
              <rect
                x={BAR_INSET}
                y={TECH_NODE.height - BAR_INSET - BAR_HEIGHT / 2}
                width={(barWidth * spread) / PERCENT}
                height={BAR_HEIGHT}
                rx={BAR_HEIGHT / 2}
                className={spread >= PERCENT ? 'fill-success' : 'fill-primary'}
              />
            </g>
          )
        })}
      </svg>
    </div>
  )
}
