import { useId, useState } from 'react'
import { Lock, Plus, Trash2, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components, seasonOnsetValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { EntityLink, FieldTile, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NumberField } from '@/features/entity/wilds/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { SEASON_ONSET } from './seasonLabels'

type WorldSeasons = components['schemas']['WorldSeasonsView']
type Onset = components['schemas']['SeasonOnsetView']
type OnsetKind = Onset['onset']

const WORKING = 'Working on it.'

function seasonNamed(data: WorldSeasons, position: number): string {
  return (
    data.seasons.find((season) => season.position === position)?.name ??
    `Season ${position + 1}`
  )
}

function OnsetPicker({
  value,
  onChange,
  label,
}: {
  value: OnsetKind
  onChange: (value: OnsetKind) => void
  label: string
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Select
        value={value}
        onValueChange={(next) => onChange(next as OnsetKind)}
      >
        <SelectTrigger id={id} aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {seasonOnsetValues.map((onset) => (
            <SelectItem key={onset} value={onset}>
              {SEASON_ONSET[onset].label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldTile>
  )
}

function OnsetRow({
  data,
  onset,
  blocked,
}: {
  data: WorldSeasons
  onset: Onset
  blocked: string | null
}) {
  const shown = SEASON_ONSET[onset.onset]
  const Icon = shown.icon
  const set = useGodAction({
    run: (value: OnsetKind) =>
      unwrap(
        api.POST('/api/actions/seasons:onset', {
          body: {
            world_id: data.world_id,
            year: onset.year,
            season_position: onset.season_position,
            onset: value,
          },
        })
      ),
    success: 'The season keeps the onset you set',
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:onset_release', {
          body: { onset_id: onset.id },
        })
      ),
    success: 'The onset is no longer held',
  })
  const clear = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:onset_clear', {
          body: { onset_id: onset.id },
        })
      ),
    success: 'The season comes on time that year',
  })
  const busy =
    blocked ??
    (set.isPending || release.isPending || clear.isPending ? WORKING : null)
  const releaseReason =
    busy ?? (onset.locked ? null : 'This onset is not held.')
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-md surface-sheen p-2'>
      <div className='flex min-w-0 flex-1 items-center gap-2'>
        <Badge size='sm' variant='secondary'>
          <Icon aria-hidden='true' />
          {shown.label}
        </Badge>
        <Text weight='medium' truncate>
          {seasonNamed(data, onset.season_position)}
        </Text>
        <Muted variant='caption'>{`Year ${onset.year}`}</Muted>
        {onset.by_node_id !== null && onset.by_name && (
          <>
            <Muted variant='caption'>set by</Muted>
            <EntityLink kind='entity' id={String(onset.by_node_id)} showIcon>
              {onset.by_name}
            </EntityLink>
          </>
        )}
        {onset.locked && (
          <Badge size='sm' variant='info'>
            <Lock aria-hidden='true' />
            Held
          </Badge>
        )}
      </div>
      <OnsetPicker
        value={onset.onset}
        label='Onset that year'
        onChange={(value) => {
          if (busy === null) set.mutate(value)
        }}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={releaseReason !== null}
        disabledReason={releaseReason ?? undefined}
        onClick={() => release.mutate()}
      >
        <Unlock />
        Release
      </Button>
      <Button
        size='sm'
        variant='ghost'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => clear.mutate()}
      >
        <Trash2 />
        Clear
      </Button>
    </li>
  )
}

function NewOnset({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | null
}) {
  const seasonId = useId()
  const [year, setYear] = useState('')
  const [position, setPosition] = useState(
    String(data.seasons[0]?.position ?? 0)
  )
  const [onset, setOnset] = useState<OnsetKind>('failed')
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:onset', {
          body: {
            world_id: data.world_id,
            year: Number(year),
            season_position: Number(position),
            onset,
          },
        })
      ),
    success: 'The season will keep that onset',
    onDone: () => setYear(''),
  })
  const reason =
    blocked ??
    (data.seasons.length <= 1
      ? 'A world with one season has no onset to move.'
      : null) ??
    (!/^-?\d+$/.test(year.trim())
      ? 'Write the year as a whole number.'
      : null) ??
    (add.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md p-2 sealed-well'>
      <Text weight='semibold'>Set the onset of a season in a year</Text>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/year:grid-cols-3'>
        <NumberField label='Year' value={year} onChange={setYear} />
        <FieldTile id={seasonId} label='Season of the year'>
          <Select value={position} onValueChange={setPosition}>
            <SelectTrigger id={seasonId} aria-label='Season of the year'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {data.seasons.map((season) => (
                <SelectItem key={season.id} value={String(season.position)}>
                  {season.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldTile>
        <OnsetPicker value={onset} label='Onset' onChange={setOnset} />
      </div>
      <Button
        className='self-start'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => add.mutate()}
      >
        <Plus />
        Hold this onset
      </Button>
    </div>
  )
}

export function SeasonOnsets({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | null
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      {data.onsets.length === 0 ? (
        <Muted>Every season has come on time in the years drawn so far.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={data.onsets} as='li'>
            {(onset) => (
              <OnsetRow
                key={`${onset.id}-${onset.onset}-${onset.locked}`}
                data={data}
                onset={onset}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
      )}
      <NewOnset data={data} blocked={blocked} />
    </div>
  )
}
