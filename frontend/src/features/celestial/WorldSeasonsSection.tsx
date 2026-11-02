import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, CalendarDays, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useLoreMutation } from '@/features/entity/api/mutations'
import { useWorldState } from '@/features/entity/api/queries'

type WorldSeasons = components['schemas']['WorldSeasonsView']
type Season = components['schemas']['SeasonView']
type Calendar = components['schemas']['CalendarView']

const BUSY_REASON = 'Another change is being applied.'
const ENTER_VALUE = 'Enter a value first.'
const FIRST_REASON = 'This season already comes first.'
const LAST_REASON = 'This season already comes last.'

function seasonsKey(worldId: number) {
  return ['worlds', worldId, 'seasons'] as const
}

function whole(value: string): number | null {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : null
}

function moved(seasons: Season[], index: number, step: number): number[] {
  const order = seasons.map((season) => season.position)
  const target = index + step
  ;[order[index], order[target]] = [order[target], order[index]]
  return order
}

function SeasonRow({
  season,
  index,
  seasons,
  worldId,
  blocked,
}: {
  season: Season
  index: number
  seasons: Season[]
  worldId: number
  blocked: string | undefined
}) {
  const invalidate = [seasonsKey(worldId)]
  const [growth, setGrowth] = useState(String(season.growth))
  const [campaign, setCampaign] = useState(String(season.campaign))
  const reorder = useLoreMutation({
    run: (order: number[]) =>
      unwrap(
        api.POST('/api/actions/seasons:reorder', {
          body: { world_id: worldId, order },
        })
      ),
    invalidate,
  })
  const edit = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:edit', {
          body: {
            season_id: season.id,
            growth: whole(growth),
            campaign: whole(campaign),
          },
        })
      ),
    invalidate,
  })
  const busy =
    blocked ?? (reorder.isPending || edit.isPending ? BUSY_REASON : undefined)
  const up = busy ?? (index === 0 ? FIRST_REASON : undefined)
  const down = busy ?? (index === seasons.length - 1 ? LAST_REASON : undefined)
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <Text className='min-w-28'>
        {season.position + 1}. {season.name}
      </Text>
      <Muted>
        warmth {season.temperature_shift}, rain {season.rain_shift}, travel{' '}
        {season.travel}
      </Muted>
      {season.edited && (
        <Badge size='sm' variant='info'>
          edited
        </Badge>
      )}
      <Input
        aria-label={`${season.name} growth`}
        inputMode='numeric'
        className='w-20'
        value={growth}
        onChange={(event) => setGrowth(event.target.value)}
      />
      <Input
        aria-label={`${season.name} fitness for war`}
        inputMode='numeric'
        className='w-20'
        value={campaign}
        onChange={(event) => setCampaign(event.target.value)}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== undefined}
        disabledReason={busy}
        onClick={() => edit.mutate()}
      >
        Save
      </Button>
      <Button
        size='sm'
        variant='ghost'
        aria-label='Earlier in the year'
        disabled={up !== undefined}
        disabledReason={up}
        onClick={() => reorder.mutate(moved(seasons, index, -1))}
      >
        <ArrowUp />
      </Button>
      <Button
        size='sm'
        variant='ghost'
        aria-label='Later in the year'
        disabled={down !== undefined}
        disabledReason={down}
        onClick={() => reorder.mutate(moved(seasons, index, 1))}
      >
        <ArrowDown />
      </Button>
    </div>
  )
}

function CalendarRowView({
  calendar,
  worldId,
  blocked,
}: {
  calendar: Calendar
  worldId: number
  blocked: string | undefined
}) {
  const invalidate = [seasonsKey(worldId)]
  const [names, setNames] = useState(calendar.month_names.join(', '))
  const rename = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:rename', {
          body: {
            knowledge_id: calendar.knowledge_id,
            names: names.split(',').map((name) => name.trim()),
          },
        })
      ),
    invalidate,
  })
  const drop = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:drop', {
          body: { knowledge_id: calendar.knowledge_id },
        })
      ),
    invalidate,
  })
  const busy =
    blocked ?? (rename.isPending || drop.isPending ? BUSY_REASON : undefined)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Text>
        {calendar.name}: kept since epoch {calendar.adopted_epoch}, counted from
        year {calendar.anchor_year}
      </Text>
      {calendar.holy_days.length > 0 && (
        <Muted>
          Holy days: {calendar.holy_days.map((day) => day.name).join(' · ')}
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          aria-label='Month names'
          value={names}
          onChange={(event) => setNames(event.target.value)}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => rename.mutate()}
        >
          Rename months
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => drop.mutate()}
        >
          <Trash2 />
          Drop calendar
        </Button>
      </div>
    </div>
  )
}

function CalendarSettings({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | undefined
}) {
  const [tilt, setTilt] = useState(String(data.axial_tilt ?? ''))
  const [year, setYear] = useState(String(data.year_length_days ?? ''))
  const [day, setDay] = useState(String(data.day_length_hours ?? ''))
  const [knowledge, setKnowledge] = useState('')
  const invalidate = [seasonsKey(data.world_id)]
  const save = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:calendar', {
          body: {
            world_id: data.world_id,
            axial_tilt: whole(tilt),
            year_length_days: whole(year),
            day_length_hours: whole(day),
            regenerate_seasons: true,
          },
        })
      ),
    invalidate,
  })
  const adopt = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:adopt', {
          body: { knowledge_id: whole(knowledge) ?? 0 },
        })
      ),
    invalidate,
  })
  const busy =
    blocked ?? (save.isPending || adopt.isPending ? BUSY_REASON : undefined)
  const adoptReason =
    busy ?? (whole(knowledge) === null ? ENTER_VALUE : undefined)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          aria-label='Axial tilt'
          inputMode='numeric'
          className='w-24'
          placeholder='Tilt'
          value={tilt}
          onChange={(event) => setTilt(event.target.value)}
        />
        <Input
          aria-label='Days in a year'
          inputMode='numeric'
          className='w-24'
          placeholder='Days'
          value={year}
          onChange={(event) => setYear(event.target.value)}
        />
        <Input
          aria-label='Hours in a day'
          inputMode='numeric'
          className='w-24'
          placeholder='Hours'
          value={day}
          onChange={(event) => setDay(event.target.value)}
        />
        <Button
          size='sm'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => save.mutate()}
        >
          Reshape the year
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          aria-label='Astronomy record id'
          inputMode='numeric'
          className='w-40'
          placeholder='Astronomy record #'
          value={knowledge}
          onChange={(event) => setKnowledge(event.target.value)}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={adoptReason !== undefined}
          disabledReason={adoptReason}
          onClick={() => adopt.mutate()}
        >
          Keep a calendar
        </Button>
      </div>
    </div>
  )
}

export function WorldSeasonsSection({ worldId }: { worldId: number }) {
  const state = useWorldState()
  const readOnlyReason = state.data?.read_only ? READ_ONLY_REASON : null
  const view = useQuery({
    queryKey: seasonsKey(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/seasons', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
  const data = view.data
  const blocked = readOnlyReason ?? undefined
  return (
    <Section
      id='section-seasons'
      title='Seasons and calendar'
      description='How the year turns: tilt, length of year and day, moons and tides, the seasons in order, calendars kept and the years remembered.'
      icon={CalendarDays}
    >
      {data && (
        <div className='flex min-w-0 flex-col gap-4'>
          <Text>
            Axial tilt {data.axial_tilt ?? '—'}, {data.year_length_days ?? '—'}{' '}
            days a year, {data.day_length_hours ?? '—'} hours a day,{' '}
            {data.moon_count ?? 0} moons, tides {data.tidal_strength ?? 0}.
          </Text>
          <CalendarSettings
            key={`${data.axial_tilt}-${data.year_length_days}`}
            data={data}
            blocked={blocked}
          />
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>The year, in order (growth · war)</Label>
            {data.seasons.map((season, index) => (
              <SeasonRow
                key={`${season.id}-${season.growth}-${season.campaign}`}
                season={season}
                index={index}
                seasons={data.seasons}
                worldId={worldId}
                blocked={blocked}
              />
            ))}
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Calendars</Label>
            {data.calendars.length === 0 && (
              <Muted>No people counts the year yet.</Muted>
            )}
            {data.calendars.map((calendar) => (
              <CalendarRowView
                key={`${calendar.knowledge_id}-${calendar.month_names.join()}`}
                calendar={calendar}
                worldId={worldId}
                blocked={blocked}
              />
            ))}
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label variant='overline'>Years remembered</Label>
            {data.notable_years.length === 0 && (
              <Muted>No year stands out yet.</Muted>
            )}
            {data.notable_years.map((year) => (
              <Text key={year.id}>
                {year.year}: {year.name}
              </Text>
            ))}
          </div>
        </div>
      )}
      {readOnlyReason && <Muted variant='caption'>{readOnlyReason}</Muted>}
    </Section>
  )
}
