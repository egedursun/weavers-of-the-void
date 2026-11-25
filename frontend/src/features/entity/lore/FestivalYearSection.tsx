import { useQuery } from '@tanstack/react-query'
import { CalendarDays, CalendarOff, Lock, PartyPopper } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { SeasonWheel } from '@/features/celestial/SeasonWheel'
import { useGodGate } from '@/features/pantheon/gate'
import { loreKeys } from '../api/keys'
import { OptionalChoice } from './CultureParts'
import { ChoicePicker, NamedChip } from './LoreFields'
import { NONE, withNone } from './cultureLabels'
import { CALENDAR_SLOTS } from './forge/forgeModel'
import {
  type LoreNamed,
  TRADITION_KINDS,
  busyOf,
  lookup,
  useLoreEdit,
} from './model'

type FestivalYear = components['schemas']['FestivalYearView']
type Festival = FestivalYear['festivals'][number]
type Season = FestivalYear['seasons'][number]

const FESTIVALS_SHOWN = 4
const HELD_LABELS: Record<string, string> = {
  season_position: 'season held',
  calendar_slot: 'time held',
}

function festivalYearKey(peopleId: number) {
  return [...loreKeys.entity(peopleId), 'festival-year'] as const
}

function seasonTable(seasons: Season[]): Record<string, LoreNamed> {
  return withNone(
    Object.fromEntries(
      seasons.map((season) => [
        String(season.position),
        {
          label: `${season.position + 1}. ${season.name}`,
          icon: CalendarDays,
          tone: 'info',
        },
      ])
    ),
    'Whenever its time comes'
  )
}

function comesLine(row: Festival): string {
  if (row.calendar_slot === null) return 'Kept whenever it falls'
  if (row.slot_open === false)
    return `Its time does not come: ${row.slot_reason ?? 'its season never arrives'}`
  if (row.in_season === true) return 'Its time comes this epoch'
  if (row.in_season === false) return 'Its time did not come this epoch'
  return 'Its time comes on this world'
}

function FestivalCard({
  row,
  seasons,
  blocked,
}: {
  row: Festival
  seasons: Season[]
  blocked: string | null
}) {
  const edit = useLoreEdit(row.id)
  const kind = lookup(TRADITION_KINDS, row.kind)
  const closed = row.slot_open === false
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-md border surface-sheen border-gild/45 p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <EntityLink kind='entity' id={String(row.id)}>
          {row.name}
        </EntityLink>
        <NamedChip spec={kind} />
        {row.calendar_slot && (
          <NamedChip spec={lookup(CALENDAR_SLOTS, row.calendar_slot)} />
        )}
        {row.held.map((key) => (
          <Badge key={key} variant='outline'>
            <Lock aria-hidden='true' />
            {HELD_LABELS[key] ?? key}
          </Badge>
        ))}
      </div>
      <Muted
        as='p'
        variant='caption'
        className={closed ? 'text-warning' : undefined}
      >
        {comesLine(row)}
      </Muted>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <ChoicePicker
          act={edit}
          label='Season it is kept in'
          value={
            row.season_position === null ? NONE : String(row.season_position)
          }
          table={seasonTable(seasons)}
          blocked={busyOf(blocked, edit.isPending)}
          onPick={(next) =>
            edit.mutate({
              values: { season_position: next === NONE ? null : Number(next) },
            })
          }
        />
        <OptionalChoice
          entityId={row.id}
          field='calendar_slot'
          label='When it is kept'
          value={row.calendar_slot}
          table={CALENDAR_SLOTS}
          noneLabel='Whenever it falls'
          blocked={blocked}
        />
      </div>
    </li>
  )
}

function SeasonColumn({
  title,
  rows,
  seasons,
  blocked,
}: {
  title: string
  rows: Festival[]
  seasons: Season[]
  blocked: string | null
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md surface-well p-3'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Label>{title}</Label>
        <Badge variant='secondary'>{rows.length}</Badge>
      </div>
      {rows.length === 0 ? (
        <Muted as='p' variant='caption'>
          No festival falls here.
        </Muted>
      ) : (
        <PagedList
          items={rows}
          initial={FESTIVALS_SHOWN}
          noun={['festival', 'festivals']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => (
            <FestivalCard row={row} seasons={seasons} blocked={blocked} />
          )}
        </PagedList>
      )}
    </div>
  )
}

export function FestivalYearSection({
  peopleId,
  readOnlyReason,
}: {
  peopleId: number
  readOnlyReason: string | null
}) {
  const { reason } = useGodGate()
  const view = useQuery({
    queryKey: festivalYearKey(peopleId),
    queryFn: () =>
      unwrap(
        api.GET('/api/peoples/{people_id}/festival-year', {
          params: { path: { people_id: peopleId } },
        })
      ),
    retry: false,
  })
  const blocked = readOnlyReason ?? reason()
  const data: FestivalYear | undefined = view.data
  return (
    <Section
      id='section-festival-year'
      title='Year of festivals'
      description="The festivals this people keeps, placed on its world's year by the season and the time each is kept in."
      icon={PartyPopper}
    >
      {view.isPending ? (
        <LoadingBlock label='Reading the year of festivals' />
      ) : view.isError || !data ? (
        <EmptyState
          icon={CalendarOff}
          title='The year of festivals could not be read'
          description='Try again after the next epoch.'
        />
      ) : data.festivals.length === 0 ? (
        <EmptyState
          icon={PartyPopper}
          title='No festival yet'
          description='This people keeps no festival; one founded or adopted by it takes its place on the year here.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-4'>
          {blocked && (
            <Muted as='p' variant='caption'>
              {blocked}
            </Muted>
          )}
          <div className='grid min-w-0 grid-cols-1 items-start gap-4 lg:grid-cols-3'>
            {data.seasons.length > 0 ? (
              <SeasonWheel
                seasons={data.seasons}
                label={`The year of ${plural(data.seasons.length, 'season')}`}
              />
            ) : (
              <Text as='p'>Its world turns through no seasons.</Text>
            )}
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:col-span-2'>
              {data.seasons.map((season) => (
                <SeasonColumn
                  key={season.id}
                  title={`${season.position + 1}. ${season.name}`}
                  rows={data.festivals.filter(
                    (row) => row.season_position === season.position
                  )}
                  seasons={data.seasons}
                  blocked={blocked}
                />
              ))}
              <SeasonColumn
                title='Whenever its time comes'
                rows={data.festivals.filter(
                  (row) =>
                    row.season_position === null ||
                    !data.seasons.some(
                      (season) => season.position === row.season_position
                    )
                )}
                seasons={data.seasons}
                blocked={blocked}
              />
            </div>
          </div>
        </div>
      )}
    </Section>
  )
}
