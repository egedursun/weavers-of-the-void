import { VISION_MANIFESTO, VISION_TITLE, VISION_VOWS } from '@/config/about'
import { Telescope } from 'lucide-react'
import { formatCompact } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { type Rarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Label, Text } from '@/components/typography'
import {
  type LoreTotals,
  type WorldState,
  useLoreTotals,
  useWorldState,
} from '@/features/overview/api'
import { SectionHeading } from './aboutParts'

const VIEW_WIDTH = 720
const VIEW_HEIGHT = 384
const CENTER_X = VIEW_WIDTH / 2
const CENTER_Y = VIEW_HEIGHT / 2 + 8
const RING_X = 290
const RING_Y = 128
const LABEL_GAP = 20
const NODE_RADIUS = 7
const CORE_SIZE = 76
const FULL_TURN = Math.PI * 2
const QUARTER_TURN = Math.PI / 2
const CHORD_STEPS = [1, 4, 5] as const

type WebNode = {
  label: string
  rarity: Rarity
  count: (totals: LoreTotals, state: WorldState | undefined) => number | null
}

function ofType(type: string) {
  return (totals: LoreTotals) => totals.by_type?.[type] ?? 0
}

const WEB_NODES: readonly WebNode[] = [
  {
    label: 'Gods',
    rarity: 'mythic',
    count: (_, state) => (state ? state.sons.length : null),
  },
  { label: 'Mortals', rarity: 'rare', count: ofType('mortal') },
  { label: 'Peoples', rarity: 'uncommon', count: ofType('people') },
  { label: 'Places', rarity: 'common', count: ofType('place') },
  { label: 'Tongues', rarity: 'epic', count: ofType('language') },
  { label: 'Wars', rarity: 'legendary', count: (totals) => totals.wars },
  { label: 'Relics', rarity: 'mythic', count: ofType('item') },
  { label: 'Legends', rarity: 'rare', count: ofType('legend') },
  { label: 'Prophecies', rarity: 'uncommon', count: ofType('prophecy') },
  { label: 'Cults', rarity: 'common', count: ofType('cult') },
  { label: 'Traditions', rarity: 'epic', count: ofType('tradition') },
  { label: 'Species', rarity: 'legendary', count: ofType('species') },
]

const NODE_FILL: Record<Rarity, string> = {
  common: 'fill-rarity-common',
  uncommon: 'fill-rarity-uncommon',
  rare: 'fill-rarity-rare',
  epic: 'fill-rarity-epic',
  legendary: 'fill-rarity-legendary',
  mythic: 'fill-rarity-mythic',
}

const POINTS = WEB_NODES.map((_, index) => {
  const angle = (index / WEB_NODES.length) * FULL_TURN - QUARTER_TURN
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  return {
    x: CENTER_X + cos * RING_X,
    y: CENTER_Y + sin * RING_Y,
    labelX: CENTER_X + cos * (RING_X + LABEL_GAP),
    labelY: CENTER_Y + sin * (RING_Y + LABEL_GAP),
    anchor: (Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end') as
      'middle' | 'start' | 'end',
    below: sin > 0.2,
  }
})

const EDGES = CHORD_STEPS.flatMap((step) =>
  WEB_NODES.map((_, index) => [index, (index + step) % WEB_NODES.length])
)

function labelBaseline(point: (typeof POINTS)[number]): number {
  if (point.below) return point.labelY + 6
  if (point.anchor === 'middle') return point.labelY - 26
  return point.labelY - 10
}

export function AboutVision() {
  const state = useWorldState().data
  const totals = useLoreTotals().data
  const counts = WEB_NODES.map((node) =>
    totals ? node.count(totals, state) : null
  )
  return (
    <section aria-labelledby='about-vision' className='flex flex-col gap-6'>
      <SectionHeading
        id='about-vision'
        icon={Telescope}
        eyebrow='The grand design'
        title={VISION_TITLE}
        aside={
          totals ? (
            <div className='flex flex-wrap gap-2'>
              <Badge className='gap-1.5 border-brand-gold/50 bg-brand-gold/15 text-brand-gold'>
                {`${plural(totals.records, 'record', 'records')} woven`}
              </Badge>
              <Badge className='gap-1.5 border-brand-violet/50 bg-brand-violet/15 text-foreground'>
                {`${plural(totals.bonds, 'thread', 'threads')} binding them`}
              </Badge>
            </div>
          ) : undefined
        }
      />
      <div className='flex flex-col gap-3'>
        {VISION_MANIFESTO.map((line, index) => (
          <Text
            key={line}
            variant='prose'
            className={cn(
              'max-w-none',
              index === 0
                ? 'text-title font-semibold text-primary'
                : 'text-foreground/90'
            )}
          >
            {line}
          </Text>
        ))}
      </div>

      <figure className='relative overflow-hidden rounded-2xl border border-brand-violet/40 bg-radial from-brand-violet/30 via-brand-night/60 to-brand-night p-4 shadow-inner'>
        <svg
          viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
          className='w-full'
          role='img'
          aria-label='Every kind of record in the cosmos is bound to every other'
        >
          <g className='text-brand-gold'>
            {WEB_NODES.map((node, index) => (
              <line
                key={`core-${node.label}`}
                x1={CENTER_X}
                y1={CENTER_Y}
                x2={POINTS[index].x}
                y2={POINTS[index].y}
                stroke='currentColor'
                strokeOpacity={0.18}
              />
            ))}
            {EDGES.map(([from, to]) => (
              <line
                key={`${from}-${to}`}
                className='about-web-edge'
                x1={POINTS[from].x}
                y1={POINTS[from].y}
                x2={POINTS[to].x}
                y2={POINTS[to].y}
                stroke='currentColor'
                strokeOpacity={0.45}
                strokeWidth={1.2}
              />
            ))}
          </g>
          <circle
            cx={CENTER_X}
            cy={CENTER_Y}
            r={CORE_SIZE / 2 + 10}
            className='fill-brand-gold/10 stroke-brand-gold/50'
          />
          <image
            href='/brand/logo-128.webp'
            x={CENTER_X - CORE_SIZE / 2}
            y={CENTER_Y - CORE_SIZE / 2}
            width={CORE_SIZE}
            height={CORE_SIZE}
          />
          {WEB_NODES.map((node, index) => {
            const point = POINTS[index]
            const count = counts[index]
            return (
              <g key={node.label}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={NODE_RADIUS * 2}
                  className={cn(
                    'about-web-node opacity-30',
                    NODE_FILL[node.rarity]
                  )}
                  style={{ animationDelay: `${index * 0.27}s` }}
                />
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={NODE_RADIUS}
                  className={cn('stroke-brand-night', NODE_FILL[node.rarity])}
                  strokeWidth={2}
                />
                <text
                  x={point.labelX}
                  y={labelBaseline(point)}
                  textAnchor={point.anchor}
                  className='hidden fill-foreground font-sans sm:block'
                  fontSize={14}
                  fontWeight={600}
                >
                  {node.label}
                  {count !== null && (
                    <tspan
                      x={point.labelX}
                      dy={16}
                      className='fill-brand-gold font-mono'
                      fontSize={12}
                      fontWeight={500}
                    >
                      {formatCompact(count)}
                    </tspan>
                  )}
                </text>
              </g>
            )
          })}
        </svg>
        <ul className='mt-3 flex flex-wrap justify-center gap-1.5 sm:hidden'>
          {WEB_NODES.map((node, index) => (
            <li key={node.label}>
              <Badge variant='outline' className='gap-1'>
                {node.label}
                {counts[index] !== null && (
                  <span className='font-mono text-brand-gold'>
                    {formatCompact(counts[index] ?? 0)}
                  </span>
                )}
              </Badge>
            </li>
          ))}
        </ul>
        <figcaption className='pt-2 text-center'>
          <Label>
            Every kind of record is bound to every other. Change one and the
            whole world moves.
          </Label>
        </figcaption>
      </figure>

      <ul className='grid gap-3 md:grid-cols-3'>
        {VISION_VOWS.map(({ title, body, icon: Icon }) => (
          <li
            key={title}
            className='group flex flex-col gap-3 rounded-xl border border-brand-gold/30 bg-linear-to-b from-brand-gold/10 to-transparent p-5 transition duration-200 hover:-translate-y-0.5 hover:border-brand-gold/60 hover:shadow-lg hover:shadow-brand-gold/10'
          >
            <span className='flex size-11 items-center justify-center rounded-full border border-brand-gold/50 bg-brand-night text-brand-gold transition group-hover:scale-110'>
              <Icon className='size-icon-lg' aria-hidden />
            </span>
            <Text weight='semibold' className='font-brand text-primary'>
              {title}
            </Text>
            <Text variant='caption' tone='muted'>
              {body}
            </Text>
          </li>
        ))}
      </ul>
    </section>
  )
}
