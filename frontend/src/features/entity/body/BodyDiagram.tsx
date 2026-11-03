import type { components } from '@/api/generated/schema'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Muted, Text } from '@/components/typography'
import { AnatomyFigure } from './AnatomyFigure'
import { partTone } from './diagramModel'
import { MATERIALS, REGIONS, STATES, plain } from './labels'

type Part = components['schemas']['PartView']

const STROKE = 1.3

function describe(part: Part): string {
  const state = part.state ? STATES[part.state]?.label : 'Unhurt'
  const loss = part.loss > 0 ? `, ${part.loss}% of its use lost` : ''
  const worn = part.prosthesis
    ? `, replaced with ${plain(MATERIALS, part.prosthesis).toLowerCase()}`
    : ''
  return `${part.label}: ${state}${loss}${worn}`
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
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <AnatomyFigure plan={plan} parts={parts} describe={describe} />
      <PartGrid parts={parts} />
    </div>
  )
}
