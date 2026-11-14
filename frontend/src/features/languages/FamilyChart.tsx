import { type KeyboardEvent } from 'react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { mediaUrl } from '@/features/pantheon/media'
import { type Family } from './languageFamilies'
import { SCRIPT_ICON, UNWRITTEN_ICON } from './languageIcons'
import { FAMILY_NODE, clip, curve, layoutFamily } from './treeLayout'

const NAME_LIMIT = 17
const BADGE_RADIUS = 15
const ICON_SIZE = 16
const COVER_WIDTH = 160

function activate(event: KeyboardEvent, run: () => void) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    run()
  }
}

export function FamilyChart({
  family,
  covers,
  selected,
  lineage,
  onSelect,
}: {
  family: Family
  covers: Map<number, string | null>
  selected: number
  lineage: Set<number>
  onSelect: (id: number) => void
}) {
  const layout = layoutFamily(family)
  const middle = FAMILY_NODE.height / 2
  return (
    <div className='min-w-0 overflow-x-auto'>
      <svg
        role='group'
        aria-label={`Family of ${family.node.language.name}`}
        width={layout.width}
        height={layout.height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className='block'
      >
        {layout.links.map(({ from, to }) => {
          const lit =
            lineage.has(to.node.language.id) &&
            lineage.has(from.node.language.id)
          return (
            <path
              key={`${from.node.language.id}-${to.node.language.id}`}
              d={curve(
                { x: from.x + FAMILY_NODE.width, y: from.y + middle },
                { x: to.x, y: to.y + middle }
              )}
              fill='none'
              strokeWidth={lit ? 2.5 : 1.5}
              strokeLinecap='round'
              className={lit ? 'stroke-primary' : 'stroke-border'}
            />
          )
        })}
        {layout.nodes.map((placed) => {
          const id = placed.node.language.id
          const active = id === selected
          const inLine = lineage.has(id)
          const script = placed.node.writing_system
          const Icon = script ? SCRIPT_ICON[script] : UNWRITTEN_ICON
          const cover = mediaUrl(covers.get(id), COVER_WIDTH)
          return (
            <g
              key={id}
              transform={`translate(${placed.x} ${placed.y})`}
              role='button'
              tabIndex={0}
              aria-pressed={active}
              aria-label={`${placed.node.language.name}, ${plural(placed.node.words, 'word', 'words')}`}
              className='cursor-pointer'
              onClick={() => onSelect(id)}
              onKeyDown={(event) => activate(event, () => onSelect(id))}
            >
              <title>{placed.node.language.name}</title>
              <rect
                width={FAMILY_NODE.width}
                height={FAMILY_NODE.height}
                rx={12}
                strokeWidth={active ? 2 : 1}
                className={cn(
                  active
                    ? 'fill-primary/10 stroke-primary'
                    : inLine
                      ? 'fill-card stroke-primary/50'
                      : 'fill-card stroke-border hover:stroke-primary/60'
                )}
              />
              {cover ? (
                <>
                  <clipPath id={`language-cover-${id}`}>
                    <circle
                      cx={8 + BADGE_RADIUS}
                      cy={middle}
                      r={BADGE_RADIUS}
                    />
                  </clipPath>
                  <image
                    href={cover}
                    x={8}
                    y={middle - BADGE_RADIUS}
                    width={BADGE_RADIUS * 2}
                    height={BADGE_RADIUS * 2}
                    preserveAspectRatio='xMidYMid slice'
                    clipPath={`url(#language-cover-${id})`}
                  />
                  <circle
                    cx={8 + BADGE_RADIUS}
                    cy={middle}
                    r={BADGE_RADIUS}
                    fill='none'
                    strokeWidth={1.5}
                    className={
                      active || inLine ? 'stroke-primary' : 'stroke-border'
                    }
                  />
                </>
              ) : (
                <circle
                  cx={8 + BADGE_RADIUS}
                  cy={middle}
                  r={BADGE_RADIUS}
                  className='fill-muted stroke-border'
                />
              )}
              <Icon
                x={
                  cover
                    ? FAMILY_NODE.width - ICON_SIZE - 10
                    : 8 + BADGE_RADIUS - ICON_SIZE / 2
                }
                y={cover ? 10 : middle - ICON_SIZE / 2}
                width={cover ? ICON_SIZE - 2 : ICON_SIZE}
                height={cover ? ICON_SIZE - 2 : ICON_SIZE}
                className={
                  placed.node.writing_system
                    ? 'text-info'
                    : 'text-muted-foreground'
                }
              />
              <text
                x={16 + BADGE_RADIUS * 2}
                y={middle - 4}
                fontSize={14}
                fontWeight={600}
                className='fill-foreground font-display'
              >
                {clip(placed.node.language.name, NAME_LIMIT)}
              </text>
              <text
                x={16 + BADGE_RADIUS * 2}
                y={middle + 13}
                fontSize={11}
                className='fill-muted-foreground'
              >
                {`${plural(placed.node.words, 'word', 'words')} · ${plural(placed.node.speakers, 'speaker', 'speakers')}`}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
