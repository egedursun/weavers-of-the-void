import { type ReactNode, useId } from 'react'
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
import {
  BLUEPRINTS,
  type Blueprint,
  CANVAS,
  type Feature,
  type Hold,
  type Mark,
  type Setting,
  type Silhouette,
} from './blueprints'
import {
  CRITICALITY,
  type Criticality,
  HAZARD,
  SECTION_STATE,
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

export type MountArc = 'forward' | 'aft' | 'side' | 'all_round'

export type DiagramMount = {
  key: string
  section: string | null
  label: string
  count: number
  arc?: MountArc
}

type Box = { part: DiagramPart; x: number; y: number; w: number; h: number }
type Fitted = { lines: string[]; size: number }
type Ids = {
  clip: string
  hatch: string
  surface: string
  glow: string
  cells: Record<SectionState, string>
}

const FONT = 11
const SMALLEST = 6.5
const GLYPH = 0.56
const INSET = 6
const LINE = 1.15
const GAP = 3
const MIN_SHARE = 4
const SHARE_BAR = 3
const BADGE = 10
const MOUNT_RADIUS = 7
const ARROW = 7
const PILL_FONT = 9.5
const PILL_ROOM = 440
const SKINS: ReadonlySet<string> = new Set([
  'armour_plating',
  'barding',
  'shielding',
])
const AURAS: ReadonlySet<string> = new Set(['ward', 'wards'])
const MARGIN = 14
const ZONE_ORDER: Zone[] = ['front', 'top', 'body', 'under', 'rear']
const STATE_HUE: Record<SectionState, string> = {
  sound: 'text-success',
  damaged: 'text-warning',
  disabled: 'text-destructive',
  destroyed: 'text-muted-foreground',
}
const STATE_STROKE: Record<SectionState, string> = {
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
const STARS = [
  [40, 30],
  [120, 250],
  [190, 18],
  [260, 262],
  [330, 22],
  [420, 256],
  [500, 34],
  [548, 230],
  [70, 210],
  [470, 70],
  [22, 120],
  [540, 120],
] as const
const CLOUDS = [
  [80, 236, 46],
  [470, 34, 38],
  [500, 252, 30],
] as const

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
  if (double > single && double >= SMALLEST)
    return { lines: split, size: double }
  if (single >= SMALLEST || split.length === 1)
    return { lines: [text], size: Math.max(SMALLEST, single) }
  return { lines: split, size: SMALLEST }
}

function describe(part: DiagramPart): string {
  const hazard =
    part.hazard === 'none'
      ? ''
      : `; ${HAZARD[part.hazard].label.toLowerCase()} when struck`
  return `${sectionLabel(part.key)}: ${SECTION_STATE[part.state].label.toLowerCase()}, ${CRITICALITY[part.criticality].label.toLowerCase()} section, ${part.share}% of the whole${hazard}${part.detail ? `; ${part.detail}` : ''}`
}

function lay(parts: DiagramPart[], hold: Hold): Box[] {
  if (parts.length === 0) return []
  const rows = parts.length <= 5 ? 1 : parts.length <= 10 ? 2 : 3
  const perRow = Math.ceil(parts.length / rows)
  const height = (hold.h - GAP * (rows - 1)) / rows
  return Array.from({ length: rows }, (_, row) =>
    parts.slice(row * perRow, (row + 1) * perRow)
  ).flatMap((items, row) => {
    const total = items.reduce(
      (sum, part) => sum + Math.max(MIN_SHARE, part.share),
      0
    )
    const room = hold.w - GAP * (items.length - 1)
    let cursor = hold.x
    return items.map((part) => {
      const w = (room * Math.max(MIN_SHARE, part.share)) / total
      const box = {
        part,
        x: cursor,
        y: hold.y + row * (height + GAP),
        w,
        h: height,
      }
      cursor += w + GAP
      return box
    })
  })
}

function Defs({ ids, body }: { ids: Ids; body: string }) {
  return (
    <defs>
      <clipPath id={ids.clip}>
        <path d={body} clipRule='evenodd' />
      </clipPath>
      <pattern
        id={ids.hatch}
        width={6}
        height={6}
        patternUnits='userSpaceOnUse'
        patternTransform='rotate(45)'
      >
        <line
          x1={0}
          y1={0}
          x2={0}
          y2={6}
          className='stroke-destructive/50'
          strokeWidth={2}
        />
      </pattern>
      <linearGradient id={ids.surface} x1={0} y1={0} x2={0} y2={1}>
        <stop
          offset={0}
          stopColor='currentColor'
          stopOpacity={0.35}
          className='text-primary'
        />
        <stop
          offset={0.5}
          stopColor='currentColor'
          stopOpacity={0.95}
          className='text-card'
        />
        <stop
          offset={1}
          stopColor='currentColor'
          stopOpacity={1}
          className='text-muted'
        />
      </linearGradient>
      <filter id={ids.glow} x='-50%' y='-50%' width='200%' height='200%'>
        <feGaussianBlur stdDeviation={6} />
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
            stopOpacity={state === 'destroyed' ? 0.3 : 0.62}
            className={STATE_HUE[state]}
          />
          <stop
            offset={1}
            stopColor='currentColor'
            stopOpacity={state === 'destroyed' ? 0.14 : 0.24}
            className={STATE_HUE[state]}
          />
        </linearGradient>
      ))}
    </defs>
  )
}

function Backdrop({ setting, ids }: { setting: Setting; ids: Ids }) {
  const { width, height } = CANVAS
  if (setting === 'water')
    return (
      <rect
        x={-MARGIN}
        y={226}
        width={width + MARGIN * 2}
        height={height - 226 + MARGIN}
        className='fill-info/15 stroke-none'
      />
    )
  if (setting === 'deep')
    return (
      <rect
        x={-MARGIN}
        y={-MARGIN}
        width={width + MARGIN * 2}
        height={height + MARGIN * 2}
        rx={12}
        className='fill-info/10 stroke-none'
      />
    )
  if (setting === 'space')
    return (
      <g>
        <ellipse
          cx={width * 0.45}
          cy={height / 2}
          rx={width * 0.42}
          ry={height * 0.36}
          className='fill-primary/10 stroke-none'
          filter={`url(#${ids.glow})`}
        />
        {STARS.map(([x, y]) => (
          <circle
            key={`${x}.${y}`}
            cx={x}
            cy={y}
            r={1.4}
            className='fill-foreground/60 stroke-none'
          />
        ))}
      </g>
    )
  if (setting === 'air')
    return (
      <g>
        {CLOUDS.map(([x, y, r]) => (
          <ellipse
            key={x}
            cx={x}
            cy={y}
            rx={r}
            ry={r * 0.32}
            className='fill-foreground/10 stroke-none'
          />
        ))}
      </g>
    )
  return (
    <g>
      <ellipse
        cx={width / 2}
        cy={258}
        rx={width * 0.42}
        ry={8}
        className='fill-foreground/25 stroke-none'
        filter={`url(#${ids.glow})`}
      />
      <line
        x1={-MARGIN}
        y1={258}
        x2={width + MARGIN}
        y2={258}
        className='stroke-border'
        strokeWidth={1.2}
      />
    </g>
  )
}

function Waves() {
  const step = 14
  const count = Math.ceil((CANVAS.width + MARGIN * 2) / step)
  const crest = Array.from(
    { length: count },
    () => `q ${step / 4} -4 ${step / 2} 0 t ${step / 2} 0`
  ).join(' ')
  return (
    <path
      d={`M ${-MARGIN} 230 ${crest}`}
      className='fill-none stroke-info/60'
      strokeWidth={1.4}
    />
  )
}

function Paint({
  mark,
  part,
  ids,
}: {
  mark: Mark
  part: DiagramPart
  ids: Ids
}) {
  if (mark.neutral)
    return mark.line ? (
      <path
        d={mark.d}
        className='fill-none stroke-foreground/40'
        strokeWidth={mark.line}
        strokeLinecap='round'
      />
    ) : (
      <path d={mark.d} className='fill-muted stroke-border' strokeWidth={1} />
    )
  if (mark.line)
    return (
      <path
        d={mark.d}
        className={cn('fill-none', STATE_STROKE[part.state])}
        strokeWidth={mark.line}
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeDasharray={part.state === 'destroyed' ? '4 4' : undefined}
      />
    )
  return (
    <>
      <path
        d={mark.d}
        fill={`url(#${ids.cells[part.state]})`}
        className={STATE_STROKE[part.state]}
        strokeWidth={part.criticality === 'critical' ? 2 : 1.3}
        strokeDasharray={part.criticality === 'minor' ? '4 3' : undefined}
        strokeLinejoin='round'
      />
      {part.state === 'destroyed' && (
        <path d={mark.d} fill={`url(#${ids.hatch})`} />
      )}
    </>
  )
}

function Hint({ part, children }: { part: DiagramPart; children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <g
          tabIndex={0}
          aria-label={describe(part)}
          className='outline-none focus-visible:opacity-80'
        >
          {children}
        </g>
      </TooltipTrigger>
      <TooltipContent>{describe(part)}</TooltipContent>
    </Tooltip>
  )
}

function Pill({ x, y, part }: { x: number; y: number; part: DiagramPart }) {
  const text = sectionLabel(part.key)
  const width = text.length * PILL_FONT * GLYPH + 14
  return (
    <g aria-hidden='true'>
      <rect
        x={x - width / 2}
        y={y - 9}
        width={width}
        height={18}
        rx={9}
        className={cn('fill-background/90', STATE_STROKE[part.state])}
        strokeWidth={1}
      />
      <text
        x={x}
        y={y}
        textAnchor='middle'
        dominantBaseline='central'
        className='fill-foreground'
        fontSize={PILL_FONT}
      >
        {text}
      </text>
    </g>
  )
}

function Compartment({ box, ids }: { box: Box; ids: Ids }) {
  const { part } = box
  const hazard = part.hazard !== 'none' ? HAZARD[part.hazard] : null
  const HazardIcon = hazard?.icon
  const { lines, size } = fit(part.key, box.w, box.h - SHARE_BAR * 2)
  const top = box.y + box.h / 2 - ((lines.length - 1) * size * LINE) / 2
  return (
    <>
      <rect
        x={box.x}
        y={box.y}
        width={Math.max(1, box.w)}
        height={box.h}
        data-section={part.key}
        fill={`url(#${ids.cells[part.state]})`}
        className={STATE_STROKE[part.state]}
        strokeWidth={part.criticality === 'critical' ? 2.2 : 0.9}
        strokeDasharray={part.criticality === 'minor' ? '4 3' : undefined}
      />
      {part.state === 'destroyed' && (
        <rect
          x={box.x}
          y={box.y}
          width={box.w}
          height={box.h}
          fill={`url(#${ids.hatch})`}
        />
      )}
      <rect
        x={box.x + 3}
        y={box.y + box.h - SHARE_BAR - 3}
        width={Math.max(0, ((box.w - 6) * Math.min(100, part.share)) / 100)}
        height={SHARE_BAR}
        rx={SHARE_BAR / 2}
        className='fill-primary/80 stroke-none'
      />
      {HazardIcon && box.w > BADGE * 2.6 && (
        <HazardIcon
          x={box.x + box.w - BADGE - 2}
          y={box.y + 2}
          width={BADGE}
          height={BADGE}
          strokeWidth={2.2}
          className={
            hazard.tone === 'info'
              ? 'text-info'
              : hazard.tone === 'warning'
                ? 'text-warning'
                : 'text-destructive'
          }
        />
      )}
      {part.criticality === 'critical' && box.w > BADGE * 2.6 && (
        <HeartCrack
          x={box.x + 2}
          y={box.y + 2}
          width={BADGE}
          height={BADGE}
          strokeWidth={2.2}
          className={STATE_TEXT[part.state]}
        />
      )}
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
        r={MOUNT_RADIUS + 3}
        className='fill-none stroke-primary/60'
        strokeWidth={1.2}
        strokeDasharray='2 2'
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

function MountMark({
  mount,
  x,
  y,
}: {
  mount: DiagramMount
  x: number
  y: number
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <g
          tabIndex={0}
          aria-label={`${mount.label} × ${mount.count}`}
          className='outline-none'
        >
          <Aim x={x} y={y} arc={mount.arc ?? 'all_round'} />
          <circle
            cx={x}
            cy={y}
            r={MOUNT_RADIUS}
            className='fill-background stroke-primary'
            strokeWidth={1.6}
          />
          <Crosshair
            x={x - MOUNT_RADIUS * 0.72}
            y={y - MOUNT_RADIUS * 0.72}
            width={MOUNT_RADIUS * 1.44}
            height={MOUNT_RADIUS * 1.44}
            strokeWidth={2.6}
            className='text-primary'
          />
          {mount.count > 1 && (
            <g>
              <circle
                cx={x + MOUNT_RADIUS}
                cy={y - MOUNT_RADIUS}
                r={5}
                className='fill-primary stroke-background'
                strokeWidth={1}
              />
              <text
                x={x + MOUNT_RADIUS}
                y={y - MOUNT_RADIUS}
                textAnchor='middle'
                dominantBaseline='central'
                className='fill-primary-foreground'
                fontSize={6.5}
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

function claim(blueprint: Blueprint, parts: DiagramPart[]) {
  const byKey = new Map(parts.map((part) => [part.key, part]))
  const pick = (keys: readonly string[]) =>
    keys.map((key) => byKey.get(key)).find((part) => part !== undefined)
  const features = blueprint.features.flatMap((feature, index) => {
    const part = pick(feature.keys)
    return part ? [{ feature, part, order: index }] : []
  })
  const body = pick(blueprint.bodyKeys)
  const taken = new Set([
    ...features.map(({ part }) => part.key),
    ...(body ? [body.key] : []),
  ])
  const loose = parts.filter((part) => !taken.has(part.key))
  return {
    features,
    body,
    skins: loose.filter((part) => SKINS.has(part.key)),
    auras: loose.filter((part) => AURAS.has(part.key)),
    inside: loose.filter(
      (part) => !SKINS.has(part.key) && !AURAS.has(part.key)
    ),
  }
}

function Skin({ part, body }: { part: DiagramPart; body: string }) {
  return (
    <Hint part={part}>
      <path
        d={body}
        fillRule='evenodd'
        className={cn('fill-none', STATE_STROKE[part.state])}
        strokeWidth={6}
        strokeLinejoin='round'
        strokeDasharray={part.state === 'destroyed' ? '10 6' : undefined}
        opacity={0.75}
      />
    </Hint>
  )
}

function Aura({ part, ring }: { part: DiagramPart; ring: number }) {
  return (
    <Hint part={part}>
      <ellipse
        cx={CANVAS.width / 2}
        cy={CANVAS.height / 2}
        rx={CANVAS.width / 2 - 6 - ring * 10}
        ry={CANVAS.height / 2 - 6 - ring * 10}
        className={cn('fill-none', STATE_STROKE[part.state])}
        strokeWidth={1.6}
        strokeDasharray='2 6'
        strokeLinecap='round'
      />
    </Hint>
  )
}

function FeatureMark({
  feature,
  part,
  ids,
}: {
  feature: Feature
  part: DiagramPart
  ids: Ids
}) {
  return (
    <Hint part={part}>
      {feature.marks.map((mark, index) => (
        <Paint key={index} mark={mark} part={part} ids={ids} />
      ))}
    </Hint>
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
    clip: `${base}clip`,
    hatch: `${base}hatch`,
    surface: `${base}surface`,
    glow: `${base}glow`,
    cells: {
      sound: `${base}sound`,
      damaged: `${base}damaged`,
      disabled: `${base}disabled`,
      destroyed: `${base}destroyed`,
    },
  }
  const [measure, room] = useWidth()
  const blueprint = BLUEPRINTS[shape]
  const { features, body, skins, auras, inside } = claim(blueprint, parts)
  const ordered = [...inside].sort(
    (left, right) =>
      ZONE_ORDER.indexOf(zoneOf(left.key)) -
      ZONE_ORDER.indexOf(zoneOf(right.key))
  )
  const boxes = lay(ordered, blueprint.hold)
  const pills = room === 0 || room >= PILL_ROOM
  const anchor = (section: string | null) => {
    const found = features.find(({ part }) => part.key === section)
    if (found) return { x: found.feature.at[0], y: found.feature.at[1] }
    const box = boxes.find((item) => item.part.key === section)
    if (box) return { x: box.x + box.w / 2, y: box.y }
    return {
      x: blueprint.hold.x + blueprint.hold.w / 2,
      y: blueprint.hold.y,
    }
  }
  const spread = (mount: DiagramMount) => {
    const point = anchor(mount.section)
    const siblings = mounts.filter((item) => item.section === mount.section)
    const place = siblings.findIndex((item) => item.key === mount.key)
    return {
      x: point.x + (place - (siblings.length - 1) / 2) * MOUNT_RADIUS * 3.2,
      y: point.y,
    }
  }
  const back = features.filter(({ feature }) => feature.back)
  const front = features.filter(({ feature }) => !feature.back)
  const shell = (
    <path
      d={blueprint.body}
      fillRule='evenodd'
      fill={body ? `url(#${ids.cells[body.state]})` : `url(#${ids.surface})`}
      className={body ? STATE_STROKE[body.state] : 'stroke-primary/60'}
      strokeWidth={body?.criticality === 'critical' ? 2.4 : 1.6}
      strokeLinejoin='round'
    />
  )
  return (
    <div ref={measure} className='flex min-w-0 flex-col gap-3'>
      <svg
        role='img'
        aria-label={title}
        viewBox={`${-MARGIN} ${-MARGIN} ${CANVAS.width + MARGIN * 2} ${CANVAS.height + MARGIN * 2}`}
        className='h-auto w-full max-w-3xl self-center'
      >
        <Defs ids={ids} body={blueprint.body} />
        <Backdrop setting={blueprint.setting} ids={ids} />
        {blueprint.decor?.map((mark, index) => (
          <path
            key={index}
            d={mark.d}
            className={
              mark.line
                ? 'fill-none stroke-foreground/30'
                : 'fill-muted stroke-foreground/30'
            }
            strokeWidth={mark.line ?? 1.2}
            strokeLinejoin='round'
          />
        ))}
        {back.map(({ feature, part, order }) => (
          <FeatureMark key={order} feature={feature} part={part} ids={ids} />
        ))}
        {auras.map((part, index) => (
          <Aura key={part.key} part={part} ring={index} />
        ))}
        {body ? <Hint part={body}>{shell}</Hint> : shell}
        <g clipPath={`url(#${ids.clip})`}>
          {boxes.map((box) => (
            <Hint key={box.part.key} part={box.part}>
              <Compartment box={box} ids={ids} />
            </Hint>
          ))}
        </g>
        {skins.map((part) => (
          <Skin key={part.key} part={part} body={blueprint.body} />
        ))}
        {front.map(({ feature, part, order }) => (
          <FeatureMark key={order} feature={feature} part={part} ids={ids} />
        ))}
        {blueprint.setting === 'water' && <Waves />}
        {pills &&
          features
            .filter(
              (item, index) =>
                features.findIndex(({ part }) => part.key === item.part.key) ===
                index
            )
            .map(({ feature, part, order }) => (
              <Pill
                key={order}
                x={feature.label[0]}
                y={feature.label[1]}
                part={part}
              />
            ))}
        {mounts.map((mount) => {
          const at = spread(mount)
          return <MountMark key={mount.key} mount={mount} x={at.x} y={at.y} />
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
                className={cn('size-icon-xs shrink-0', STATE_TEXT[part.state])}
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
