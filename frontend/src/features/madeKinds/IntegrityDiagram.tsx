import { HeartCrack } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  CRITICALITY,
  type Criticality,
  HAZARD,
  SECTION_STATE,
  STATE_FILL,
  type SectionState,
  sectionLabel,
} from './labels'

export type Zone = 'top' | 'front' | 'body' | 'rear' | 'under'

export type DiagramPart = {
  key: string
  state: SectionState
  criticality: Criticality
  share: number
  hazard: keyof typeof HAZARD
  detail?: string
}

export type DiagramMount = {
  key: string
  section: string | null
  label: string
  count: number
}

type Box = { part: DiagramPart; x: number; y: number; w: number; h: number }

const ROW_HEIGHT: Record<Zone, number> = {
  top: 30,
  front: 34,
  body: 34,
  rear: 34,
  under: 22,
}
const ROW_OF: Record<Zone, 'upper' | 'middle' | 'lower'> = {
  top: 'upper',
  front: 'middle',
  body: 'middle',
  rear: 'middle',
  under: 'lower',
}
const PAD = 8
const ROW_GAP = 4
const PART_WIDTH = 34
const BODY_WIDTH = 120
const GAP = 3
const MIN_SHARE = 4
const LABELLED = 26
const LETTER = 5.5

function lay(
  parts: DiagramPart[],
  x: number,
  width: number,
  zone: Zone,
  y: number
): Box[] {
  if (parts.length === 0) return []
  const total = parts.reduce(
    (sum, part) => sum + Math.max(MIN_SHARE, part.share),
    0
  )
  const floor = Math.min(PART_WIDTH, width / parts.length - GAP)
  const spare = Math.max(
    0,
    width - GAP * (parts.length - 1) - floor * parts.length
  )
  let cursor = x
  return parts.map((part) => {
    const w = floor + (spare * Math.max(MIN_SHARE, part.share)) / total
    const box = { part, x: cursor, y, w, h: ROW_HEIGHT[zone] }
    cursor += w + GAP
    return box
  })
}

function span(count: number): number {
  return count * PART_WIDTH + GAP * Math.max(0, count - 1)
}

function boxes(
  parts: DiagramPart[],
  zoneOf: (key: string) => Zone
): { laid: Box[]; width: number; height: number } {
  const by = (zone: Zone) => parts.filter((part) => zoneOf(part.key) === zone)
  const rows = { upper: 0, middle: 0, lower: 0 }
  let cursor = PAD
  for (const row of ['upper', 'middle', 'lower'] as const) {
    const zones = (Object.keys(ROW_OF) as Zone[]).filter(
      (zone) => ROW_OF[zone] === row && by(zone).length > 0
    )
    if (zones.length === 0) continue
    rows[row] = cursor
    cursor += Math.max(...zones.map((zone) => ROW_HEIGHT[zone])) + ROW_GAP
  }
  const at = (zone: Zone) => rows[ROW_OF[zone]]
  const front = by('front')
  const rear = by('rear')
  const middle = Math.max(
    BODY_WIDTH,
    span(by('top').length),
    span(by('body').length),
    span(by('under').length)
  )
  const left = front.length ? span(front.length) + GAP : 0
  const right = rear.length ? span(rear.length) + GAP : 0
  return {
    width: left + middle + right,
    height: cursor - ROW_GAP + PAD,
    laid: [
      ...lay(by('top'), left, middle, 'top', at('top')),
      ...lay(front, 0, span(front.length), 'front', at('front')),
      ...lay(by('body'), left, middle, 'body', at('body')),
      ...lay(rear, left + middle + GAP, span(rear.length), 'rear', at('rear')),
      ...lay(by('under'), left, middle, 'under', at('under')),
    ],
  }
}

function shortLabel(key: string, width: number): string {
  const text = sectionLabel(key)
  const room = Math.max(2, Math.floor((width - 4) / LETTER))
  return text.length <= room ? text : `${text.slice(0, Math.max(1, room - 1))}…`
}

function describe(part: DiagramPart): string {
  const hazard =
    part.hazard === 'none'
      ? ''
      : `; ${HAZARD[part.hazard].label.toLowerCase()} when struck`
  return `${sectionLabel(part.key)}: ${SECTION_STATE[part.state].label.toLowerCase()}, ${CRITICALITY[part.criticality].label.toLowerCase()} section, ${part.share}% of the whole${hazard}${part.detail ? `; ${part.detail}` : ''}`
}

export function IntegrityDiagram({
  title,
  parts,
  mounts = [],
  zoneOf,
}: {
  title: string
  parts: DiagramPart[]
  mounts?: DiagramMount[]
  zoneOf: (key: string) => Zone
}) {
  const { laid, width, height } = boxes(parts, zoneOf)
  const home = (section: string | null): Box | undefined =>
    laid.find((item) => item.part.key === section) ??
    laid.find((item) => zoneOf(item.part.key) === 'top') ??
    laid[0]
  const anchor = (mount: DiagramMount, index: number) => {
    const box = home(mount.section)
    if (!box) return { x: 12 + index * 14, y: 4 }
    const siblings = mounts.filter((item) => home(item.section) === box)
    const place = siblings.findIndex((item) => item.key === mount.key)
    const step = box.w / (siblings.length + 1)
    return { x: box.x + step * (place + 1), y: box.y }
  }
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <svg
        role='img'
        aria-label={title}
        viewBox={`-4 0 ${width + 8} ${height}`}
        className='h-auto w-full max-w-2xl self-center'
      >
        {laid.map((box) => (
          <Tooltip key={box.part.key}>
            <TooltipTrigger asChild>
              <g tabIndex={0} aria-label={describe(box.part)}>
                <rect
                  x={box.x}
                  y={box.y}
                  width={Math.max(2, box.w)}
                  height={box.h}
                  rx={4}
                  className={cn(
                    STATE_FILL[box.part.state],
                    box.part.criticality === 'critical' && 'stroke-2'
                  )}
                  strokeDasharray={
                    box.part.criticality === 'minor' ? '3 2' : undefined
                  }
                />
                <text
                  x={box.x + box.w / 2}
                  y={box.y + box.h / 2 + 3}
                  textAnchor='middle'
                  className='fill-foreground'
                  fontSize={box.w >= LABELLED ? 7 : 6}
                >
                  {shortLabel(box.part.key, box.w)}
                </text>
              </g>
            </TooltipTrigger>
            <TooltipContent>{describe(box.part)}</TooltipContent>
          </Tooltip>
        ))}
        {mounts.map((mount, index) => {
          const at = anchor(mount, index)
          return (
            <Tooltip key={mount.key}>
              <TooltipTrigger asChild>
                <g tabIndex={0} aria-label={`${mount.label} × ${mount.count}`}>
                  <circle
                    cx={at.x}
                    cy={at.y}
                    r={3.5}
                    className='fill-primary stroke-background'
                  />
                  {mount.count > 1 && (
                    <text
                      x={at.x + 5}
                      y={at.y + 3}
                      className='fill-primary'
                      fontSize={7}
                    >
                      {mount.count}
                    </text>
                  )}
                </g>
              </TooltipTrigger>
              <TooltipContent>{`${mount.label} × ${mount.count}`}</TooltipContent>
            </Tooltip>
          )
        })}
      </svg>
      <PagedList
        items={parts}
        initial={12}
        noun={['section', 'sections']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(part) => part.key}
      >
        {(part) => {
          const state = SECTION_STATE[part.state]
          const Icon = part.criticality === 'critical' ? HeartCrack : state.icon
          return (
            <div
              key={part.key}
              className='flex min-w-0 items-center gap-1.5 rounded-md border bg-background px-2 py-1'
              aria-label={describe(part)}
            >
              <Icon
                aria-hidden='true'
                className={cn(
                  'size-icon-xs shrink-0',
                  part.state === 'sound'
                    ? 'text-success'
                    : part.state === 'damaged'
                      ? 'text-warning'
                      : 'text-destructive'
                )}
              />
              <Text as='span' variant='caption' truncate>
                {sectionLabel(part.key)}
              </Text>
              <Muted as='span' variant='caption'>
                {state.label}
              </Muted>
            </div>
          )
        }}
      </PagedList>
    </div>
  )
}
