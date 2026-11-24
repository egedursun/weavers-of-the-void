import { Mountain } from 'lucide-react'
import { undergroundStratumValues } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Label, Text } from '@/components/typography'
import { STRATUM } from '@/features/entity/environment/geologyLabels'
import { type DepthOption } from './MapToolbar'
import { StratumSwatch } from './SwatchMarker'
import { type MapStratum } from './api'
import { STRATUM_LOOK } from './deepLooks'

export function DepthLadder({
  depth,
  depths,
  onDepth,
}: {
  depth: MapStratum | null
  depths: readonly DepthOption[]
  onDepth: (depth: MapStratum | null) => void
}) {
  if (depths.length === 0) return null
  const ordered = [...depths].sort(
    (left, right) =>
      left.depth - right.depth || left.stratum.localeCompare(right.stratum)
  )
  const name = depth === null ? 'Surface' : STRATUM[depth].label
  const level =
    depth === null
      ? 0
      : ordered.findIndex((option) => option.stratum === depth) + 1
  return (
    <div
      role='group'
      aria-label={`Depth shown: ${name}, ${level} of ${ordered.length} below the surface`}
      className='absolute top-3 left-3 flex w-max max-w-1/2 min-w-0 flex-col gap-1 rounded-md bg-background/85 px-2 py-1.5 shadow-md'
    >
      <Label variant='overline'>Depth</Label>
      <ol className='flex min-w-0 flex-col'>
        <li className='flex min-w-0'>
          <Button
            variant='ghost'
            size='sm'
            aria-pressed={depth === null}
            onClick={() => onDepth(null)}
            className={cn(
              'min-w-0 justify-start',
              depth === null ? 'text-foreground' : 'text-muted-foreground'
            )}
          >
            <Mountain aria-hidden='true' className='size-icon-xs shrink-0' />
            <Text
              as='span'
              variant='caption'
              weight={depth === null ? 'semibold' : 'normal'}
              truncate
            >
              Surface
            </Text>
          </Button>
        </li>
        {undergroundStratumValues.map((stratum) => {
          const option = ordered.find((item) => item.stratum === stratum)
          if (!option) return null
          const look = STRATUM_LOOK[option.stratum]
          const current = option.stratum === depth
          return (
            <li key={option.stratum} className='flex min-w-0'>
              <Button
                variant='ghost'
                size='sm'
                aria-pressed={current}
                onClick={() => onDepth(option.stratum)}
                className={cn(
                  'min-w-0 justify-start',
                  current ? 'text-foreground' : 'text-muted-foreground'
                )}
              >
                <span
                  aria-hidden='true'
                  className={cn(
                    'flex shrink-0 rounded-sm',
                    current ? 'ring-2 ring-foreground' : 'opacity-70'
                  )}
                >
                  <StratumSwatch fill={look.fill} glow={look.glow} />
                </span>
                <Text
                  as='span'
                  variant='caption'
                  weight={current ? 'semibold' : 'normal'}
                  truncate
                >
                  {STRATUM[option.stratum].label}
                </Text>
              </Button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
