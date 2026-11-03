import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Muted, Text } from '@/components/typography'
import { LEGEND, isLost, partTone } from './diagramModel'
import { MATERIALS, REGIONS, STATES, plain } from './labels'

type Part = components['schemas']['PartView']

type Shape =
  | { kind: 'circle'; cx: number; cy: number; r: number }
  | { kind: 'rect'; x: number; y: number; w: number; h: number; rx?: number }

const HUMANOID: Record<string, Shape> = {
  aura: { kind: 'circle', cx: 60, cy: 22, r: 21 },
  head: { kind: 'circle', cx: 60, cy: 22, r: 14 },
  face: { kind: 'rect', x: 52, y: 20, w: 16, h: 10, rx: 4 },
  left_eye: { kind: 'circle', cx: 55, cy: 19, r: 2.4 },
  right_eye: { kind: 'circle', cx: 65, cy: 19, r: 2.4 },
  left_ear: { kind: 'rect', x: 43, y: 17, w: 4, h: 8, rx: 2 },
  right_ear: { kind: 'rect', x: 73, y: 17, w: 4, h: 8, rx: 2 },
  nose: { kind: 'rect', x: 58.5, y: 21, w: 3, h: 5, rx: 1.5 },
  jaw: { kind: 'rect', x: 54, y: 30, w: 12, h: 4, rx: 2 },
  tongue: { kind: 'rect', x: 57.5, y: 30.5, w: 5, h: 2, rx: 1 },
  neck: { kind: 'rect', x: 55, y: 36, w: 10, h: 7, rx: 2 },
  torso: { kind: 'rect', x: 42, y: 44, w: 36, h: 46, rx: 8 },
  heart: { kind: 'circle', cx: 65, cy: 56, r: 4 },
  lungs: { kind: 'rect', x: 48, y: 50, w: 10, h: 14, rx: 4 },
  gut: { kind: 'rect', x: 52, y: 68, w: 16, h: 12, rx: 5 },
  groin: { kind: 'rect', x: 52, y: 84, w: 16, h: 7, rx: 3 },
  left_arm: { kind: 'rect', x: 28, y: 46, w: 11, h: 40, rx: 5 },
  right_arm: { kind: 'rect', x: 81, y: 46, w: 11, h: 40, rx: 5 },
  left_hand: { kind: 'circle', cx: 33.5, cy: 92, r: 6 },
  right_hand: { kind: 'circle', cx: 86.5, cy: 92, r: 6 },
  fingers: { kind: 'rect', x: 80, y: 99, w: 13, h: 5, rx: 2 },
  left_leg: { kind: 'rect', x: 44, y: 93, w: 13, h: 44, rx: 6 },
  right_leg: { kind: 'rect', x: 63, y: 93, w: 13, h: 44, rx: 6 },
  left_foot: { kind: 'rect', x: 40, y: 139, w: 17, h: 7, rx: 3 },
  right_foot: { kind: 'rect', x: 63, y: 139, w: 17, h: 7, rx: 3 },
}

const STROKE = 1.3
const LOST_DASH = '3 2'
const INNER_DASH = '2 1.5'
const INNER = new Set(['heart', 'lungs', 'gut', 'groin', 'tongue'])
const DRAW_ORDER = [
  'aura',
  'torso',
  'left_arm',
  'right_arm',
  'left_leg',
  'right_leg',
  'neck',
  'head',
]

function describe(part: Part): string {
  const state = part.state ? STATES[part.state]?.label : 'Unhurt'
  const loss = part.loss > 0 ? `, ${part.loss}% of its use lost` : ''
  const worn = part.prosthesis
    ? `, replaced with ${plain(MATERIALS, part.prosthesis).toLowerCase()}`
    : ''
  return `${part.label}: ${state}${loss}${worn}`
}

function ShapeOf({
  shape,
  className,
  dash,
}: {
  shape: Shape
  className: string
  dash?: string
}) {
  if (shape.kind === 'circle')
    return (
      <circle
        cx={shape.cx}
        cy={shape.cy}
        r={shape.r}
        className={className}
        strokeWidth={STROKE}
        strokeDasharray={dash}
      />
    )
  return (
    <rect
      x={shape.x}
      y={shape.y}
      width={shape.w}
      height={shape.h}
      rx={shape.rx ?? 2}
      className={className}
      strokeWidth={STROKE}
      strokeDasharray={dash}
    />
  )
}

function Silhouette({ parts }: { parts: Part[] }) {
  const byKey = new Map(parts.map((part) => [part.key, part]))
  const ordered = [
    ...DRAW_ORDER.filter((key) => byKey.has(key)),
    ...parts.map((part) => part.key).filter((key) => !DRAW_ORDER.includes(key)),
  ]
  return (
    <svg
      viewBox='0 0 120 150'
      role='img'
      aria-label='Body diagram'
      className='h-72 w-auto max-w-full shrink-0'
    >
      {ordered.map((key) => {
        const part = byKey.get(key)
        const shape = HUMANOID[key]
        if (!part || !shape) return null
        return (
          <g key={key}>
            <title>{describe(part)}</title>
            <ShapeOf
              shape={shape}
              dash={
                isLost(part)
                  ? LOST_DASH
                  : INNER.has(key) && part.state === null
                    ? INNER_DASH
                    : undefined
              }
              className={cn(
                partTone(part),
                INNER.has(key) && part.state === null && 'fill-background/60',
                key === 'aura' &&
                  part.state === null &&
                  'fill-transparent stroke-primary/50'
              )}
            />
          </g>
        )
      })}
    </svg>
  )
}

function PartChip({ part }: { part: Part }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          tabIndex={0}
          aria-label={describe(part)}
          className='flex min-w-0 items-center gap-2 rounded-md border bg-background px-2 py-1'
        >
          <svg
            viewBox='0 0 10 10'
            aria-hidden='true'
            className='size-icon-xs shrink-0'
          >
            <circle
              cx={5}
              cy={5}
              r={4}
              className={partTone(part)}
              strokeWidth={STROKE}
            />
          </svg>
          <Text as='span' variant='caption' truncate>
            {part.label}
          </Text>
          {part.loss > 0 && (
            <Muted as='span' variant='caption'>
              {`−${part.loss}%`}
            </Muted>
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent>{describe(part)}</TooltipContent>
    </Tooltip>
  )
}

export function PartGrid({ parts }: { parts: Part[] }) {
  const regions = [...new Set(parts.map((part) => part.region))]
  return (
    <div className='flex min-w-0 flex-1 flex-col gap-3'>
      {regions.map((region) => (
        <div key={region} className='flex min-w-0 flex-col gap-1.5'>
          <Muted variant='caption'>{REGIONS[region] ?? region}</Muted>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {parts
              .filter((part) => part.region === region)
              .map((part) => (
                <PartChip key={part.key} part={part} />
              ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export function BodyDiagram({ parts, plan }: { parts: Part[]; plan: string }) {
  const drawn =
    plan === 'humanoid' || plan === 'colossal' || plan === 'divine_manifest'
  return (
    <div className='flex min-w-0 flex-col items-center gap-4 @lg/body:flex-row @lg/body:items-start'>
      {drawn && <Silhouette parts={parts} />}
      <PartGrid parts={parts} />
    </div>
  )
}

export function DiagramLegend() {
  return (
    <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
      {LEGEND.map((item) => (
        <span key={item.label} className='flex items-center gap-1.5'>
          <svg viewBox='0 0 10 10' aria-hidden='true' className='size-icon-xs'>
            <circle
              cx={5}
              cy={5}
              r={4}
              className={item.className}
              strokeWidth={STROKE}
              strokeDasharray={item.dashed ? LOST_DASH : undefined}
            />
          </svg>
          <Muted as='span' variant='caption'>
            {item.label}
          </Muted>
        </span>
      ))}
    </div>
  )
}
