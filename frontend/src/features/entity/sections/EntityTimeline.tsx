import { useMemo } from 'react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Paged } from '@/components/domain'
import { Label } from '@/components/typography'
import { kindTone } from '@/features/chronicle/chronicleKinds'
import { type ChronicleLine } from '../api/types'
import { timelineColumns } from './timeline'

type EntityTimelineProps = {
  lines: ChronicleLine[]
  birthEpoch: number
  currentEpoch: number
  onPick: (epoch: number) => void
}

const DOT_SIZE = [
  'size-icon-xs',
  'size-icon-sm',
  'size-icon-md',
  'size-icon-lg',
] as const
const DOT_STEP = 2

const DOT_TONE = {
  default: 'bg-primary',
  primary: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  destructive: 'bg-destructive',
} as const

export function EntityTimeline({
  lines,
  birthEpoch,
  currentEpoch,
  onPick,
}: EntityTimelineProps) {
  const columns = useMemo(
    () => timelineColumns(lines, birthEpoch, currentEpoch),
    [lines, birthEpoch, currentEpoch]
  )
  if (columns.length < 2 && lines.length < 2) return null
  return (
    <nav aria-label='Timeline' className='min-w-0 overflow-x-auto'>
      <ol className='flex min-w-max items-end gap-1 pb-1'>
        <Paged items={columns} as='li'>
          {(column) => (
            <li
              key={column.epoch}
              className='flex w-control-sm flex-col items-center gap-1'
            >
              <a
                href={`#epoch-${column.epoch}`}
                aria-label={`Epoch ${column.epoch}: ${plural(column.count, 'record', 'records')}`}
                title={`Epoch ${column.epoch}: ${plural(column.count, 'record', 'records')}`}
                onClick={(event) => {
                  event.preventDefault()
                  if (column.count > 0) onPick(column.epoch)
                }}
                className={cn(
                  'flex size-control-sm items-center justify-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  column.count === 0 && 'pointer-events-none'
                )}
              >
                {column.kind ? (
                  <span
                    className={cn(
                      'rounded-full',
                      DOT_SIZE[
                        Math.min(
                          DOT_SIZE.length - 1,
                          Math.floor(column.count / DOT_STEP)
                        )
                      ],
                      DOT_TONE[kindTone(column.kind)]
                    )}
                  />
                ) : (
                  <span className='h-1 w-1 rounded-full bg-border' />
                )}
              </a>
              <Label
                className={
                  column.epoch === birthEpoch ? 'text-primary' : undefined
                }
              >
                {String(column.epoch)}
              </Label>
            </li>
          )}
        </Paged>
      </ol>
    </nav>
  )
}
