import { type QueryKey } from '@tanstack/react-query'
import { Droplets, Flame, Snowflake, Sun, Waves } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useCosmographyAction } from './api'
import { CLIMATE_TURNS, CURRENTS } from './labels'
import { Chip } from './parts'

type Turn = keyof typeof CLIMATE_TURNS

const TURN_ICONS: Record<Turn, typeof Sun> = {
  warmer: Flame,
  colder: Snowflake,
  wetter: Droplets,
  drier: Sun,
}

const SHIFT_SPAN = 100

export type RegionClimate = {
  region_id: number
  leak: number
  current: keyof typeof CURRENTS
  temperature_shift: number
  rainfall_shift: number
}

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

export function RegionClimateControl({
  ground,
  refresh,
}: {
  ground: RegionClimate
  refresh: QueryKey
}) {
  const { reason } = useGodGate()
  const turn = useCosmographyAction(
    'region_climate:turn',
    (value: Turn) => ({ region_id: ground.region_id, turn: value }),
    'The climate of the land turns',
    [refresh]
  )
  const busy = reason() ?? (turn.isPending ? 'The climate is turning' : null)
  const current = CURRENTS[ground.current]
  return (
    <div
      id='section-region-climate'
      data-surface='RegionClimateControl'
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>Climate of the heavens</Text>
          <Muted variant='caption'>
            The world's distance from its star, its sea currents and the leak
            from other dimensions shape this land. Turn it by hand; set the
            exact shifts and the leak in the controls below.
          </Muted>
        </div>
        <Chip icon={current.icon ?? Waves}>{current.label}</Chip>
      </div>
      <div
        id='section-region-leak'
        className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'
      >
        <StatBar
          label='Leak from other dimensions'
          value={ground.leak}
          max={100}
          tone='destructive'
        />
        <StatBar
          label={`Heat shift ${signed(ground.temperature_shift)}`}
          value={ground.temperature_shift + SHIFT_SPAN}
          max={SHIFT_SPAN * 2}
          tone='warning'
        />
        <StatBar
          label={`Rain shift ${signed(ground.rainfall_shift)}`}
          value={ground.rainfall_shift + SHIFT_SPAN}
          max={SHIFT_SPAN * 2}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {(Object.keys(CLIMATE_TURNS) as Turn[]).map((key) => {
          const Icon = TURN_ICONS[key]
          return (
            <Button
              key={key}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => turn.mutate(key)}
            >
              <Icon />
              {`Make it ${CLIMATE_TURNS[key].toLowerCase()}`}
            </Button>
          )
        })}
      </div>
    </div>
  )
}
