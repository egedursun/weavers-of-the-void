import { type SVGProps, useId } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { components } from '@/api/generated/schema'
import { Muted } from '@/components/typography'
import {
  DRAW_LABELS,
  DRAW_STATES,
  type DrawState,
  calloutSpots,
  drawState,
} from './diagramModel'

type PartView = components['schemas']['PartView']
type Layer = Record<string, string>
type Condition = [string, string[]][]

type PlanPart = {
  key: string
  label: string
  paths: string[]
  anchor: [number, number]
  inner: boolean
  subtle: boolean
  far: boolean
  tone: string
  prelude: string
}

type PlanData = {
  plan: string
  width: number
  height: number
  underlay: string
  parts: PlanPart[]
  details: string[]
  marks: { svg: string; hide?: Condition; show?: Condition }[]
}

type Shared = {
  defs: string
  looks: Record<string, Layer[]>
  glyphs: Record<string, string>
  tones: Record<string, string>
  detail: string
  swatch: string
}

type Drawing = { plan: PlanData; shared: Shared }

const FILES = import.meta.glob<PlanData | Shared>('./anatomy/*.json', {
  import: 'default',
})
const SHARED_FILE = './anatomy/shared.json'
const GUTTER = 92
const LABEL_WIDTH = 66
const PREFIX = '__ID__'

function fileOf(plan: string): string {
  return `./anatomy/${plan}.json`
}

function hasDrawing(plan: string): boolean {
  return fileOf(plan) in FILES
}

async function loadDrawing(plan: string): Promise<Drawing> {
  const [data, shared] = await Promise.all([
    FILES[fileOf(plan)](),
    FILES[SHARED_FILE](),
  ])
  return { plan: data as PlanData, shared: shared as Shared }
}

function camel(name: string): string {
  return name.replace(/-([a-z])/g, (_, letter: string) => letter.toUpperCase())
}

function lookOf(part: PlanPart, state: DrawState): string {
  if (state !== 'unhurt') return state
  if (part.inner) return 'unhurt:inner'
  if (part.subtle) return 'unhurt:subtle'
  if (part.tone === 'divine') return 'unhurt:divine'
  if (part.tone === 'aura') return 'unhurt:aura'
  if (part.far) return 'unhurt:far'
  return 'unhurt'
}

function matches(
  condition: Condition | undefined,
  states: Map<string, DrawState>
): boolean {
  return (
    condition?.some(([key, wanted]) =>
      wanted.includes(states.get(key) ?? 'unhurt')
    ) ?? false
  )
}

function Raw({ svg, scope }: { svg: string; scope: string }) {
  if (!svg) return null
  return (
    <g dangerouslySetInnerHTML={{ __html: svg.replaceAll(PREFIX, scope) }} />
  )
}

function Shape({
  paths,
  layers,
  scope,
  title,
}: {
  paths: string[]
  layers: Layer[]
  scope: string
  title?: string
}) {
  return paths.flatMap((d, piece) =>
    layers.map((layer, index) => {
      const props: SVGProps<SVGPathElement> & Record<string, string> = {}
      for (const [name, value] of Object.entries(layer))
        if (name !== 'title')
          props[camel(name)] = value.replaceAll(PREFIX, scope)
      return (
        <path key={`${piece}-${index}`} d={d} {...props}>
          {layer.title && title && <title>{title}</title>}
        </path>
      )
    })
  )
}

function Callouts({
  plan,
  wounded,
  tones,
}: {
  plan: PlanData
  wounded: { part: PlanPart; label: string; state: DrawState }[]
  tones: Record<string, string>
}) {
  const total = plan.width + GUTTER * 2
  const sides = [
    wounded.filter((item) => item.part.anchor[0] < plan.width / 2),
    wounded.filter((item) => item.part.anchor[0] >= plan.width / 2),
  ]
  return sides.flatMap((column, side) => {
    const sorted = [...column].sort(
      (a, b) => a.part.anchor[1] - b.part.anchor[1]
    )
    const spots = calloutSpots(
      sorted.map((item) => item.part.anchor[1]),
      plan.height
    )
    const left = side === 0
    const tx = left ? 8 : total - 8
    const edge = left ? GUTTER + 22 : GUTTER + plan.width - 22
    const elbow = left ? GUTTER - 4 : GUTTER + plan.width + 4
    const end = left ? tx + LABEL_WIDTH : tx - LABEL_WIDTH
    const anchor = left ? 'start' : 'end'
    return sorted.map((item, index) => {
      const ax = item.part.anchor[0] + GUTTER
      const ay = item.part.anchor[1]
      const ly = spots[index]
      const tone = tones[item.state]
      return (
        <g key={item.part.key}>
          <path
            d={`M${ax},${ay} L${edge},${ay} L${elbow},${ly} L${end},${ly}`}
            fill='none'
            stroke={tone}
            strokeOpacity={0.55}
            strokeWidth={0.7}
          />
          <circle cx={ax} cy={ay} r={1.6} fill={tone} />
          <text
            x={tx}
            y={ly - 3.5}
            textAnchor={anchor}
            fontSize={8.6}
            fontWeight={500}
            fill='var(--foreground)'
          >
            {item.label}
          </text>
          <text
            x={tx}
            y={ly + 7.5}
            textAnchor={anchor}
            fontSize={6.8}
            letterSpacing={0.6}
            fill={tone}
          >
            {DRAW_LABELS[item.state].toUpperCase()}
          </text>
        </g>
      )
    })
  })
}

function Figure({
  drawing,
  parts,
  scope,
  describe,
}: {
  drawing: Drawing
  parts: PartView[]
  scope: string
  describe: (part: PartView) => string
}) {
  const { plan, shared } = drawing
  const views = new Map(parts.map((part) => [part.key, part]))
  const states = new Map(
    parts.map((part) => [part.key, drawState(part)] as const)
  )
  const stateOf = (key: string) => states.get(key) ?? 'unhurt'
  const titleOf = (part: PlanPart) => {
    const view = views.get(part.key)
    return view ? describe(view) : part.label
  }
  const outer = plan.parts.filter((part) => !part.inner)
  const inner = plan.parts.filter(
    (part) => part.inner && !(part.subtle && stateOf(part.key) === 'unhurt')
  )
  const marks = plan.marks.filter((mark) =>
    mark.show ? matches(mark.show, states) : !matches(mark.hide, states)
  )
  const wounded = plan.parts
    .filter((part) => stateOf(part.key) !== 'unhurt')
    .map((part) => ({
      part,
      label: views.get(part.key)?.label ?? part.label,
      state: stateOf(part.key),
    }))
  const drawPart = (part: PlanPart) => (
    <g key={part.key}>
      <Raw svg={part.prelude} scope={scope} />
      <Shape
        paths={part.paths}
        layers={shared.looks[lookOf(part, stateOf(part.key))]}
        scope={scope}
        title={titleOf(part)}
      />
    </g>
  )
  const total = plan.width + GUTTER * 2
  return (
    <svg
      viewBox={`0 0 ${total} ${plan.height}`}
      role='img'
      aria-label={`Body diagram, ${wounded.length} parts marked`}
      className='h-auto w-full max-w-xl'
    >
      <Raw svg={shared.defs} scope={scope} />
      <g transform={`translate(${GUTTER},0)`}>
        <Raw svg={plan.underlay} scope={scope} />
        {outer.map(drawPart)}
        {plan.details.map((d, index) => (
          <path
            key={index}
            d={d}
            fill='none'
            stroke={shared.detail}
            strokeWidth={0.85}
            strokeLinecap='round'
          />
        ))}
        {marks.map((mark, index) => (
          <Raw key={index} svg={mark.svg} scope={scope} />
        ))}
        {inner.map(drawPart)}
        {wounded.map(({ part, state }) => (
          <g
            key={part.key}
            transform={`translate(${part.anchor[0]},${part.anchor[1]})`}
          >
            <Raw svg={shared.glyphs[state] ?? ''} scope={scope} />
          </g>
        ))}
      </g>
      <Callouts plan={plan} wounded={wounded} tones={shared.tones} />
    </svg>
  )
}

function Legend({ shared, scope }: { shared: Shared; scope: string }) {
  return (
    <div className='flex min-w-0 flex-wrap justify-center gap-x-4 gap-y-2'>
      {DRAW_STATES.map(({ state, label }) => (
        <span key={state} className='flex items-center gap-1.5'>
          <svg viewBox='0 0 22 20' aria-hidden='true' className='h-5 w-6'>
            <Shape
              paths={[shared.swatch]}
              layers={shared.looks[state]}
              scope={scope}
            />
            <g transform='translate(11,10)'>
              <Raw svg={shared.glyphs[state] ?? ''} scope={scope} />
            </g>
          </svg>
          <Muted as='span' variant='caption'>
            {label}
          </Muted>
        </span>
      ))}
    </div>
  )
}

export function AnatomyFigure({
  plan,
  parts,
  describe,
}: {
  plan: string
  parts: PartView[]
  describe: (part: PartView) => string
}) {
  const scope = `anatomy${useId().replace(/[^a-zA-Z0-9]/g, '')}`
  const drawing = useQuery({
    queryKey: ['anatomy', plan],
    queryFn: () => loadDrawing(plan),
    enabled: hasDrawing(plan),
    staleTime: Infinity,
  })
  if (!drawing.data) return null
  return (
    <div className='dark flex min-w-0 flex-col items-center gap-3 rounded-lg border bg-background p-3 text-foreground'>
      <Figure
        drawing={drawing.data}
        parts={parts}
        scope={scope}
        describe={describe}
      />
      <Legend shared={drawing.data.shared} scope={scope} />
    </div>
  )
}
