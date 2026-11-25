import { useState } from 'react'
import { Lock, RotateCcw, Scale, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  type components,
  deathCauseValues,
  deathReadingValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { FieldTile, Medallion, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { DEATHS, READINGS } from '../mortal/labels'
import { IconPicker, Panel } from './parts'
import { WORKING } from './tones'

type Culture = components['schemas']['CultureView']
type Cause = components['schemas']['DeathCause']
type Reading = components['schemas']['DeathReading']

const READING_TABLE = Object.fromEntries(
  deathReadingValues.map((value) => [value, READINGS[value]])
)

function ReadingRow({
  peopleId,
  cause,
  row,
  blocked,
}: {
  peopleId: number
  cause: Cause
  row: Culture['death_readings'][number] | undefined
  blocked: string | null
}) {
  const [hold, setHold] = useState(row?.held ?? true)
  const set = useGodAction({
    writes: [
      { lever: 'death_reading:create' },
      { lever: 'death_reading:edit' },
    ],
    run: (reading: Reading) =>
      unwrap(
        row
          ? api.POST('/api/actions/death_reading:edit', {
              body: { people_id: peopleId, cause, reading, hold },
            })
          : api.POST('/api/actions/death_reading:create', {
              body: { people_id: peopleId, cause, reading, hold },
            })
      ),
    success: 'Their reading of that death is set',
  })
  const reset = useGodAction({
    writes: [{ lever: 'death_reading:delete' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/death_reading:delete', {
          body: { people_id: peopleId, cause },
        })
      ),
    success: 'They will read that death from their values again',
  })
  const busy = blocked ?? (set.isPending || reset.isPending ? WORKING : null)
  const death = DEATHS[cause]
  const reading = row ? READINGS[row.reading] : null
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md surface-sheen p-2 @md/folk:flex-row @md/folk:items-center'>
      <div className='flex min-w-0 flex-1 items-center gap-2'>
        <Medallion icon={death.icon} tone={death.tone} />
        <div className='flex min-w-0 flex-col'>
          <Text weight='semibold'>{death.label}</Text>
          {reading ? (
            <Badge size='sm' variant='secondary'>
              <reading.icon />
              {reading.label}
              {row?.authored ? ' · set by you' : ''}
              {row?.held ? ' · held' : ''}
            </Badge>
          ) : (
            <Muted variant='caption'>Read from their values next epoch</Muted>
          )}
        </div>
      </div>
      <IconPicker
        act={set}
        label={`How they read ${death.label.toLowerCase()}`}
        value={row?.reading ?? ''}
        table={READING_TABLE}
        blocked={busy}
        onPick={(value) => set.mutate(value as Reading)}
      />
      <FieldTile
        id={`reading-hold-${peopleId}-${cause}`}
        label='Hold'
        className='items-center'
      >
        <Switch
          permission='lock_canon'
          id={`reading-hold-${peopleId}-${cause}`}
          checked={hold}
          disabled={busy !== null}
          onCheckedChange={setHold}
          aria-label={`Hold their reading of ${death.label.toLowerCase()}`}
        />
        {hold ? <Lock aria-hidden='true' /> : <Unlock aria-hidden='true' />}
      </FieldTile>
      <Button
        act={reset}
        size='sm'
        variant='outline'
        disabled={busy !== null || !row}
        disabledReason={
          busy ?? (!row ? 'They hold no reading of it yet' : undefined)
        }
        onClick={() => reset.mutate(undefined)}
      >
        <RotateCcw />
        Read from values
      </Button>
    </li>
  )
}

export function DeathReadingsPanel({
  peopleId,
  culture,
  blocked,
}: {
  peopleId: number
  culture: Culture
  blocked: string | null
}) {
  const known = new Map(culture.death_readings.map((row) => [row.cause, row]))
  return (
    <Panel
      title='Deaths'
      icon={Scale}
      tone='gold'
      hint='How these folk read each way of dying, from glory to a curse; it weighs on funerals, the grief of kin, the renown of the dead and the standing of their house'
      wide
    >
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={[...deathCauseValues]} as='li'>
          {(cause) => (
            <ReadingRow
              key={cause}
              peopleId={peopleId}
              cause={cause}
              row={known.get(cause)}
              blocked={blocked}
            />
          )}
        </Paged>
      </ul>
    </Panel>
  )
}
