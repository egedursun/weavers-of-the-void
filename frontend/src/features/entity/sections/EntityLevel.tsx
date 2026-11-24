import { Layers } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Muted } from '@/components/typography'
import { STRATUM } from '@/features/entity/environment/geologyLabels'
import { useLoreMutation } from '../api/mutations'
import { type EntityDetail } from '../api/types'

const SURFACE = 'surface'

type Level = NonNullable<EntityDetail['level']>

function levelText(level: Level): string {
  if (level.stratum === null) return `On the surface of ${level.region.name}`
  return `Beneath ${level.region.name} · ${STRATUM[level.stratum].label}`
}

export function EntityLevel({
  entityId,
  locationId,
  level,
  readOnlyReason,
}: {
  entityId: number
  locationId: number
  level: Level
  readOnlyReason: string | null
}) {
  const move = useLoreMutation({
    run: (next: string) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/location', {
          params: { path: { entity_id: entityId } },
          body: {
            location_id: locationId,
            stratum:
              next === SURFACE
                ? null
                : (next as Level['choices'][0]['stratum']),
          },
        })
      ),
    success: (_result, next) =>
      next === SURFACE
        ? 'Brought to the surface'
        : `Placed in the ${STRATUM[next as Level['choices'][0]['stratum']].label.toLowerCase()}`,
  })
  const Icon = level.stratum === null ? Layers : STRATUM[level.stratum].icon
  const noCells = level.choices.length === 0
  const reason =
    readOnlyReason ??
    (noCells ? `Nothing lies beneath ${level.region.name}` : null)
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <Badge variant='secondary' size='sm'>
        <Icon aria-hidden='true' />
        {levelText(level)}
      </Badge>
      {level.held && (
        <Badge variant='outline' size='sm'>
          Level held
        </Badge>
      )}
      <Select
        value={level.stratum ?? SURFACE}
        onValueChange={(next) => move.mutate(next)}
        disabled={reason !== null || move.isPending}
      >
        <SelectTrigger
          aria-label='Level beneath the land'
          title={reason ?? undefined}
          className='w-auto min-w-0'
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SURFACE}>Surface</SelectItem>
          {level.choices.map((choice) => (
            <SelectItem key={choice.stratum} value={choice.stratum}>
              {choice.name
                ? `${STRATUM[choice.stratum].label}: ${choice.name}`
                : STRATUM[choice.stratum].label}
              {choice.reason ? ' (no one dwells here)' : ''}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {reason !== null && <Muted variant='caption'>{reason}</Muted>}
      {level.choices.some((choice) => choice.reason) && reason === null && (
        <Muted variant='caption'>
          A dweller placed where no one can dwell has its level held
        </Muted>
      )}
    </div>
  )
}
