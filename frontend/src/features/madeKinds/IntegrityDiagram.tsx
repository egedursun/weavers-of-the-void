import { useId } from 'react'
import { Crosshair, HeartCrack, type LucideIcon, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useWidth } from '@/features/entity/society/tones'
import { Hull } from './Silhouette'
import {
  CRITICALITY,
  type Criticality,
  HAZARD,
  SECTION_STATE,
  type SectionState,
  sectionLabel,
} from './labels'
import { MARGINS, type Silhouette } from './silhouettes'

export type Zone = 'top' | 'front' | 'body' | 'rear' | 'under'

export type DiagramPart = {
  key: string
  state: SectionState
  criticality: Criticality
  share: number
  hazard: keyof typeof HAZARD
  detail?: string
}

export type MountArc = 'forward' | 'aft' | 'side' | 'all_round'

export type DiagramMount = {
  key: string
  section: string | null
  label: string
  count: number
  arc?: MountArc
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
const FONT = 7
const SMALLEST = 4.5
const GLYPH = 0.56
const INSET = 4
const LINE = 1.15
const SCALE = 2
const CRAMPED = 0.7

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

const ORDER: Zone[] = ['top', 'front', 'body', 'rear', 'under']

function stack(
  parts: DiagramPart[],
  zoneOf: (key: string) => Zone
): { laid: Box[]; width: number; height: number } {
  const by = (zone: Zone) => parts.filter((part) => zoneOf(part.key) === zone)
  const width = Math.max(
    BODY_WIDTH,
    ...ORDER.map((zone) => span(by(zone).length))
  )
  const laid: Box[] = []
  let cursor = PAD
  for (const zone of ORDER) {
    const row = by(zone)
    if (row.length === 0) continue
    laid.push(...lay(row, 0, width, zone, cursor))
    cursor += ROW_HEIGHT[zone] + ROW_GAP
  }
  return { laid, width, height: cursor - ROW_GAP + PAD }
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

type Fitted = { lines: string[]; size: number }

function sized(lines: string[], w: number, h: number): number {
  const longest = Math.max(...lines.map((line) => line.length))
  return Math.min(
    FONT,
    (w - INSET) / (longest * GLYPH),
    (h - INSET) / (lines.length * LINE)
  )
}

function halves(text: string): string[] {
  const spaces = [...text.matchAll(/ /g)].map((match) => match.index)
  if (spaces.length === 0) return [text]
  const cut = spaces.reduce((best, at) =>
    Math.abs(at - text.length / 2) < Math.abs(best - text.length / 2)
      ? at
      : best
  )
  return [text.slice(0, cut), text.slice(cut + 1)]
}

function fit(key: string, w: number, h: number): Fitted {
  const text = sectionLabel(key)
  const single = sized([text], w, h)
  if (single >= SMALLEST + 0.5) return { lines: [text], size: single }
  const split = halves(text)
  const double = split.length > 1 ? sized(split, w, h) : 0
  if (double > single && double >= SMALLEST) {
    return { lines: split, size: double }
  }
  if (single >= SMALLEST || split.length === 1) {
    return { lines: [text], size: Math.max(SMALLEST, single) }
  }
  return { lines: split, size: SMALLEST }
}

function describe(part: DiagramPart): string {
  const hazard =
    part.hazard === 'none'
      ? ''
      : `; ${HAZARD[part.hazard].label.toLowerCase()} when struck`
  return `${sectionLabel(part.key)}: ${SECTION_STATE[part.state].label.toLowerCase()}, ${CRITICALITY[part.criticality].label.toLowerCase()} section, ${part.share}% of the whole${hazard}${part.detail ? `; ${part.detail}` : ''}`
}

function BoxLabel({ box }: { box: Box }) {
  const { lines, size } = fit(box.part.key, box.w, box.h)
  const top = box.y + box.h / 2 - ((lines.length - 1) * size * LINE) / 2
  return (
    <text
      x={box.x + box.w / 2}
      y={top}
      textAnchor='middle'
      dominantBaseline='central'
      className='fill-foreground'
      fontSize={size}
    >
      {lines.map((line, index) => (
        <tspan
          key={line}
          x={box.x + box.w / 2}
          dy={index === 0 ? 0 : size * LINE}
        >
          {line}
        </tspan>
      ))}
    </text>
  )
}

const SHARE_BAR = 2.2
const BADGE = 6.5
const MOUNT_RADIUS = 5
const ARROW = 5
const STATE_HUE: Record<SectionState, string> = {
  sound: 'text-success',
  damaged: 'text-warning',
  disabled: 'text-destructive',
  destroyed: 'text-muted-foreground',
}
const CELL_STROKE: Record<SectionState, string> = {
  sound: 'stroke-success',
  damaged: 'stroke-warning',
  disabled: 'stroke-destructive',
  destroyed: 'stroke-destructive',
}
const STATE_TEXT: Record<SectionState, string> = {
  sound: 'text-success',
  damaged: 'text-warning',
  disabled: 'text-destructive',
  destroyed: 'text-destructive',
}

type Ids = {
  hatch: string
  surface: string
  shadow: string
  cells: Record<SectionState, string>
}

function Defs({ ids }: { ids: Ids }) {
  return (
    <defs>
      <pattern
        id={ids.hatch}
        width={5}
        height={5}
        patternUnits='userSpaceOnUse'
        patternTransform='rotate(45)'
      >
        <line
          x1={0}
          y1={0}
          x2={0}
          y2={5}
          className='stroke-destructive/45'
          strokeWidth={1.6}
        />
      </pattern>
      <linearGradient id={ids.surface} x1={0} y1={0} x2={0} y2={1}>
        <stop
          offset={0}
          stopColor='currentColor'
          stopOpacity={0.26}
          className='text-primary'
        />
        <stop
          offset={0.45}
          stopColor='currentColor'
          stopOpacity={0.9}
          className='text-card'
        />
        <stop
          offset={1}
          stopColor='currentColor'
          stopOpacity={1}
          className='text-muted'
        />
      </linearGradient>
      <filter id={ids.shadow} x='-20%' y='-200%' width='140%' height='500%'>
        <feGaussianBlur stdDeviation={3} />
      </filter>
      {(Object.keys(STATE_HUE) as SectionState[]).map((state) => (
        <linearGradient
          key={state}
          id={ids.cells[state]}
          x1={0}
          y1={0}
          x2={0}
          y2={1}
        >
          <stop
            offset={0}
            stopColor='currentColor'
            stopOpacity={state === 'destroyed' ? 0.25 : 0.42}
            className={STATE_HUE[state]}
          />
          <stop
            offset={1}
            stopColor='currentColor'
            stopOpacity={state === 'destroyed' ? 0.12 : 0.14}
            className={STATE_HUE[state]}
          />
        </linearGradient>
      ))}
    </defs>
  )
}

function Cell({ box, ids }: { box: Box; ids: Ids }) {
  const { part } = box
  const w = Math.max(2, box.w)
  const hazard = part.hazard !== 'none' ? HAZARD[part.hazard] : null
  const HazardIcon = hazard?.icon
  return (
    <>
      {part.criticality === 'critical' && (
        <rect
          x={box.x - 1.6}
          y={box.y - 1.6}
          width={w + 3.2}
          height={box.h + 3.2}
          rx={5.5}
          className='fill-none stroke-destructive/35'
          strokeWidth={2.4}
        />
      )}
      <rect
        x={box.x}
        y={box.y}
        width={w}
        height={box.h}
        rx={4}
        data-section={part.key}
        fill={`url(#${ids.cells[part.state]})`}
        className={CELL_STROKE[part.state]}
        strokeWidth={part.criticality === 'critical' ? 1.6 : 1}
        strokeDasharray={part.criticality === 'minor' ? '3 2' : undefined}
      />
      {part.state === 'destroyed' && (
        <rect
          x={box.x}
          y={box.y}
          width={w}
          height={box.h}
          rx={4}
          fill={`url(#${ids.hatch})`}
        />
      )}
      <rect
        x={box.x + 1}
        y={box.y + 1}
        width={Math.max(0, w - 2)}
        height={box.h * 0.38}
        rx={3}
        className='fill-foreground/5 stroke-none'
      />
      <rect
        x={box.x + 2}
        y={box.y + box.h - SHARE_BAR - 2}
        width={Math.max(0, w - 4)}
        height={SHARE_BAR}
        rx={SHARE_BAR / 2}
        className='fill-foreground/10 stroke-none'
      />
      <rect
        x={box.x + 2}
        y={box.y + box.h - SHARE_BAR - 2}
        width={Math.max(0, ((w - 4) * Math.min(100, part.share)) / 100)}
        height={SHARE_BAR}
        rx={SHARE_BAR / 2}
        className='fill-primary/70 stroke-none'
      />
      {HazardIcon && w > BADGE * 2.4 && (
        <g>
          <circle
            cx={box.x + w - BADGE / 2 - 1.5}
            cy={box.y + BADGE / 2 + 1.5}
            r={BADGE / 2}
            className='fill-background stroke-border'
            strokeWidth={0.6}
          />
          <HazardIcon
            x={box.x + w - BADGE + 0.5 - 1.5}
            y={box.y + 2}
            width={BADGE - 1}
            height={BADGE - 1}
            strokeWidth={2.4}
            className={
              hazard.tone === 'info'
                ? 'text-info'
                : hazard.tone === 'warning'
                  ? 'text-warning'
                  : 'text-destructive'
            }
          />
        </g>
      )}
      {part.criticality === 'critical' && w > BADGE * 2.4 && (
        <HeartCrack
          x={box.x + 2}
          y={box.y + 2}
          width={BADGE - 1}
          height={BADGE - 1}
          strokeWidth={2.4}
          className={STATE_TEXT[part.state]}
        />
      )}
      <BoxLabel box={box} />
    </>
  )
}

function Aim({ x, y, arc }: { x: number; y: number; arc: MountArc }) {
  const className = 'fill-primary stroke-none'
  if (arc === 'all_round')
    return (
      <circle
        cx={x}
        cy={y}
        r={MOUNT_RADIUS + 2.2}
        className='fill-none stroke-primary/50'
        strokeWidth={0.9}
        strokeDasharray='1.6 1.4'
      />
    )
  if (arc === 'forward')
    return (
      <path
        d={`M ${x - MOUNT_RADIUS - ARROW} ${y} l ${ARROW} ${-ARROW / 1.6} v ${ARROW * 1.25} Z`}
        className={className}
      />
    )
  if (arc === 'aft')
    return (
      <path
        d={`M ${x + MOUNT_RADIUS + ARROW} ${y} l ${-ARROW} ${-ARROW / 1.6} v ${ARROW * 1.25} Z`}
        className={className}
      />
    )
  return (
    <>
      <path
        d={`M ${x} ${y - MOUNT_RADIUS - ARROW} l ${-ARROW / 1.6} ${ARROW} h ${ARROW * 1.25} Z`}
        className={className}
      />
      <path
        d={`M ${x} ${y + MOUNT_RADIUS + ARROW} l ${-ARROW / 1.6} ${-ARROW} h ${ARROW * 1.25} Z`}
        className={className}
      />
    </>
  )
}

type LegendItem = { key: string; icon: LucideIcon; tone: string; label: string }

function legendOf(parts: DiagramPart[], mounts: number): LegendItem[] {
  const states = (Object.keys(SECTION_STATE) as SectionState[])
    .filter((state) => parts.some((part) => part.state === state))
    .map((state) => ({
      key: state,
      icon: SECTION_STATE[state].icon,
      tone: STATE_TEXT[state],
      label: SECTION_STATE[state].label,
    }))
  const hazards = [
    ...new Set(
      parts.map((part) => part.hazard).filter((hazard) => hazard !== 'none')
    ),
  ].map((hazard) => ({
    key: hazard,
    icon: HAZARD[hazard].icon,
    tone: 'text-muted-foreground',
    label: HAZARD[hazard].label,
  }))
  return [
    ...states,
    ...(parts.some((part) => part.criticality === 'critical')
      ? [
          {
            key: 'critical',
            icon: HeartCrack,
            tone: 'text-destructive',
            label: 'Critical: lost, it loses the whole',
          },
        ]
      : []),
    ...hazards,
    ...(mounts > 0
      ? [
          {
            key: 'mounts',
            icon: Crosshair,
            tone: 'text-primary',
            label: 'Weapon mounts, aimed by their arc',
          },
        ]
      : []),
    {
      key: 'share',
      icon: Minus,
      tone: 'text-primary',
      label: 'Bar: its share of the whole',
    },
  ]
}

function Legend({ parts, mounts }: { parts: DiagramPart[]; mounts: number }) {
  return (
    <PagedList
      items={legendOf(parts, mounts)}
      initial={16}
      noun={['key', 'keys']}
      as='div'
      className='flex min-w-0 flex-wrap items-center justify-center gap-x-3 gap-y-1'
      listProps={{ 'aria-label': 'How to read the drawing' }}
      itemKey={(item) => item.key}
    >
      {(item) => (
        <span key={item.key} className='flex items-center gap-1'>
          <item.icon
            aria-hidden='true'
            className={cn('size-icon-xs', item.tone)}
          />
          <Muted as='span' variant='caption'>
            {item.label}
          </Muted>
        </span>
      )}
    </PagedList>
  )
}

export function IntegrityDiagram({
  title,
  parts,
  mounts = [],
  zoneOf,
  shape,
}: {
  title: string
  parts: DiagramPart[]
  mounts?: DiagramMount[]
  zoneOf: (key: string) => Zone
  shape: Silhouette
}) {
  const base = useId().replace(/:/g, '')
  const ids: Ids = {
    hatch: `${base}hatch`,
    surface: `${base}surface`,
    shadow: `${base}shadow`,
    cells: {
      sound: `${base}sound`,
      damaged: `${base}damaged`,
      disabled: `${base}disabled`,
      destroyed: `${base}destroyed`,
    },
  }
  const [measure, room] = useWidth()
  const margins = MARGINS[shape]
  const wide = boxes(parts, zoneOf)
  const full = (layout: { width: number }) =>
    layout.width + margins.left + margins.right
  const cramped = room > 0 && room < full(wide) * SCALE * CRAMPED
  const { laid, width, height } = cramped ? stack(parts, zoneOf) : wide
  const frameWidth = width + margins.left + margins.right
  const frameHeight = height + margins.top + margins.bottom
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
    <div ref={measure} className='flex min-w-0 flex-col gap-3'>
      <svg
        role='img'
        aria-label={title}
        viewBox={`${-margins.left} ${-margins.top} ${frameWidth} ${frameHeight}`}
        width={frameWidth * SCALE}
        height={frameHeight * SCALE}
        className='h-auto max-w-full self-center'
      >
        <Defs ids={ids} />
        <Hull
          shape={shape}
          x={0}
          y={PAD}
          w={width}
          h={height - PAD * 2}
          paint={{ surface: ids.surface, shadow: ids.shadow }}
        />
        {laid.map((box) => (
          <Tooltip key={box.part.key}>
            <TooltipTrigger asChild>
              <g
                tabIndex={0}
                aria-label={describe(box.part)}
                className='outline-none focus-visible:opacity-80'
              >
                <Cell box={box} ids={ids} />
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
                <g
                  tabIndex={0}
                  aria-label={`${mount.label} × ${mount.count}`}
                  className='outline-none'
                >
                  <Aim x={at.x} y={at.y} arc={mount.arc ?? 'all_round'} />
                  <circle
                    cx={at.x}
                    cy={at.y}
                    r={MOUNT_RADIUS}
                    className='fill-background stroke-primary'
                    strokeWidth={1.2}
                  />
                  <Crosshair
                    x={at.x - MOUNT_RADIUS * 0.75}
                    y={at.y - MOUNT_RADIUS * 0.75}
                    width={MOUNT_RADIUS * 1.5}
                    height={MOUNT_RADIUS * 1.5}
                    strokeWidth={2.6}
                    className='text-primary'
                  />
                  {mount.count > 1 && (
                    <g>
                      <circle
                        cx={at.x + MOUNT_RADIUS}
                        cy={at.y - MOUNT_RADIUS}
                        r={3.4}
                        className='fill-primary stroke-background'
                        strokeWidth={0.6}
                      />
                      <text
                        x={at.x + MOUNT_RADIUS}
                        y={at.y - MOUNT_RADIUS}
                        textAnchor='middle'
                        dominantBaseline='central'
                        className='fill-primary-foreground'
                        fontSize={4.4}
                      >
                        {mount.count}
                      </text>
                    </g>
                  )}
                </g>
              </TooltipTrigger>
              <TooltipContent>{`${mount.label} × ${mount.count}`}</TooltipContent>
            </Tooltip>
          )
        })}
      </svg>
      <Legend parts={parts} mounts={mounts.length} />
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
