import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  CalendarDays,
  Clock,
  CloudSun,
  Droplets,
  Footprints,
  Moon,
  Orbit,
  Sprout,
  Sun,
  Swords,
  Thermometer,
  Anchor,
  Trash2,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ChangeChip,
  KpiTile,
  LoadingBlock,
  Medallion,
  MiniStat,
  Paged,
  PagedList,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
  FieldTile,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import {
  CLIMATE_AGE,
  NOTABLE,
  named,
} from '@/features/entity/environment/labels'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { SeasonCalendarPanel } from './SeasonCalendarPanel'
import { SEASON_WARMTH, SEASON_WATER } from './seasonLabels'

type WorldSeasons = components['schemas']['WorldSeasonsView']
type Season = components['schemas']['SeasonView']
type Calendar = components['schemas']['CalendarView']
type ClimateEra = components['schemas']['ClimateEra']

const PERCENT = 100
const SHIFT = 100
const TILT_MAX = 90
const WORKING = 'Working on it.'
const FIRST = 'This season already opens the year.'
const LAST = 'This season already closes the year.'
const PICK_RECORD = 'Pick an astronomy record first.'
const ERAS = Object.keys(CLIMATE_AGE) as ClimateEra[]
const YEAR_KEY = 'year:'
const SEASON_KEY = 'season:'

function seasonsKey(worldId: number) {
  return ['world', 'seasons', worldId] as const
}

function moved(seasons: Season[], index: number, step: number): number[] {
  const order = seasons.map((season) => season.position)
  const target = index + step
  ;[order[index], order[target]] = [order[target], order[index]]
  return order
}

function ClimateAge({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | null
}) {
  const [era, setEra] = useState<ClimateEra>(data.climate?.era ?? 'temperate')
  const [epochs, setEpochs] = useState('')
  const parsed = epochs.trim() === '' ? undefined : Number(epochs)
  const command = useGodAction({
    run: () =>
      unwrap(
        api.PUT('/api/climate', {
          body: {
            era,
            world_id: data.world_id,
            ...(parsed === undefined ? {} : { epochs: parsed }),
          },
        })
      ),
    success: 'A new climate age was laid on this world',
  })
  const age = data.climate ? named(CLIMATE_AGE, data.climate.era) : null
  const invalid =
    parsed !== undefined && (!Number.isInteger(parsed) || parsed < 1)
  const reason =
    blocked ??
    (invalid ? 'Write a whole number of epochs.' : null) ??
    (command.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={age?.icon ?? CloudSun} tone={age?.tone ?? 'muted'} />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Text weight='semibold'>
              {data.climate?.label ?? 'No climate age yet'}
            </Text>
            {data.climate?.imposed && (
              <Badge size='sm' variant='warning'>
                Laid by a god
              </Badge>
            )}
          </div>
          <Muted variant='caption'>
            {data.climate
              ? `${data.climate.description} Since epoch ${data.climate.since_epoch ?? '—'}, ${plural(data.climate.epochs_left ?? 0, 'epoch', 'epochs')} left.`
              : 'The first age begins with the next epoch.'}
          </Muted>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <FieldTile label='New age'>
          <Select
            value={era}
            onValueChange={(value) => setEra(value as ClimateEra)}
          >
            <SelectTrigger aria-label='New climate age'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ERAS.map((item) => (
                <SelectItem key={item} value={item}>
                  {named(CLIMATE_AGE, item).label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldTile>
        <FieldTile
          id={`climate-epochs-${data.world_id}`}
          label='Epochs'
          className='w-32'
        >
          <Input
            id={`climate-epochs-${data.world_id}`}
            inputMode='numeric'
            placeholder='Default'
            value={epochs}
            onChange={(event) => setEpochs(event.target.value)}
          />
        </FieldTile>
        <Button
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => command.mutate()}
        >
          <CloudSun />
          Lay this age
        </Button>
      </div>
    </div>
  )
}

function YearTiles({ data }: { data: WorldSeasons }) {
  return (
    <div className='grid min-w-0 grid-cols-2 gap-2 @lg/year:grid-cols-3 @4xl/year:grid-cols-6'>
      <MiniStat
        icon={Orbit}
        label='Axial tilt'
        value={data.axial_tilt ?? '—'}
        tone='gold'
        hint='0 means no seasons; 90 the fullest swing'
      />
      <MiniStat
        icon={Sun}
        label='Days a year'
        value={data.year_length_days ?? '—'}
        tone='gold'
        hint='More days, more holy days a calendar can keep'
      />
      <MiniStat
        icon={Clock}
        label='Hours a day'
        value={data.day_length_hours ?? '—'}
        tone='info'
        hint='Longer days bring more battles by night'
      />
      <MiniStat
        icon={CalendarDays}
        label='Seasons'
        value={data.season_count ?? data.seasons.length}
        tone='verdigris'
      />
      <MiniStat
        icon={Moon}
        label='Moons'
        value={data.moon_count ?? 0}
        tone='info'
        hint='Counted from the moons that orbit this world'
      />
      <MiniStat
        icon={Anchor}
        label='Tides'
        value={data.tidal_strength ?? 0}
        tone='info'
        hint='Raised by moons; tides flood coasts and slow boats'
      />
    </div>
  )
}

function SeasonCard({
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
  blocked: string | null
}) {
  const reorder = useGodAction({
    run: (order: number[]) =>
      unwrap(
        api.POST('/api/actions/seasons:reorder', {
          body: { world_id: worldId, order },
        })
      ),
    success: 'The year turns in a new order',
  })
  const busy = blocked ?? (reorder.isPending ? WORKING : null)
  const WarmthIcon = SEASON_WARMTH[season.warmth].icon
  const WaterIcon = SEASON_WATER[season.water].icon
  const earlier = busy ?? (index === 0 ? FIRST : null)
  const later = busy ?? (index === seasons.length - 1 ? LAST : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <span className='flex size-control-sm shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/12 text-primary'>
          <Text as='span' weight='semibold'>
            {index + 1}
          </Text>
        </span>
        <Text weight='semibold' className='flex-1' truncate>
          {season.name}
        </Text>
        {season.edited && (
          <Badge size='sm' variant='info'>
            Shaped by hand
          </Badge>
        )}
        <Button
          size='icon'
          variant='ghost'
          aria-label={`Move ${season.name} earlier`}
          disabled={earlier !== null}
          disabledReason={earlier ?? undefined}
          onClick={() => reorder.mutate(moved(seasons, index, -1))}
        >
          <ArrowUp />
        </Button>
        <Button
          size='icon'
          variant='ghost'
          aria-label={`Move ${season.name} later`}
          disabled={later !== null}
          disabledReason={later ?? undefined}
          onClick={() => reorder.mutate(moved(seasons, index, 1))}
        >
          <ArrowDown />
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='secondary'>
          <WarmthIcon aria-hidden='true' />
          {SEASON_WARMTH[season.warmth].label}
        </Badge>
        <Badge size='sm' variant='secondary'>
          <WaterIcon aria-hidden='true' />
          {SEASON_WATER[season.water].label}
        </Badge>
        <ChangeChip
          value={season.temperature_shift}
          icon={Thermometer}
          label='Warmth'
        />
        <ChangeChip value={season.rain_shift} icon={Droplets} label='Rain' />
      </div>
      <StatBar
        label='Share of the year'
        value={season.share_pct}
        max={PERCENT}
        icon={CalendarDays}
        tone='warning'
      />
      <StatBar
        label='Crop growth'
        value={season.growth}
        max={PERCENT}
        icon={Sprout}
        tone='success'
      />
      <StatBar
        label='Fit for war'
        value={season.campaign}
        max={PERCENT}
        icon={Swords}
        tone='destructive'
      />
      <StatBar
        label='Ease of travel'
        value={season.travel}
        max={PERCENT}
        icon={Footprints}
        tone='info'
      />
    </div>
  )
}

function CalendarCard({
  calendar,
  blocked,
}: {
  calendar: Calendar
  blocked: string | null
}) {
  const [names, setNames] = useState(calendar.month_names.join(', '))
  const rename = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:rename', {
          body: {
            knowledge_id: calendar.knowledge_id,
            names: names.split(',').map((name) => name.trim()),
          },
        })
      ),
    success: 'The months were renamed',
  })
  const drop = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:drop', {
          body: { knowledge_id: calendar.knowledge_id },
        })
      ),
    success: 'The calendar was let go',
  })
  const busy = blocked ?? (rename.isPending || drop.isPending ? WORKING : null)
  const renameReason =
    busy ??
    (names === calendar.month_names.join(', ')
      ? 'These are the present names.'
      : null)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={BookOpen} tone='verdigris' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {calendar.name}
          </Text>
          <Muted variant='caption'>
            {`Kept since epoch ${calendar.adopted_epoch}, counted from year ${calendar.anchor_year}`}
          </Muted>
        </div>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => drop.mutate()}
        >
          <Trash2 />
          Let go
        </Button>
      </div>
      <PagedList
        items={calendar.month_names}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(month) => month}
      >
        {(month) => (
          <Badge key={month} size='sm' variant='secondary'>
            {month}
          </Badge>
        )}
      </PagedList>
      {calendar.holy_days.length > 0 && (
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Paged items={calendar.holy_days}>
            {(day) => (
              <Badge key={day.name} size='sm' variant='warning'>
                {day.name}
              </Badge>
            )}
          </Paged>
        </div>
      )}
      <div className='flex min-w-0 items-end gap-2'>
        <FieldTile
          id={`months-${calendar.knowledge_id}`}
          label='Month names, in order'
          className='flex-1'
        >
          <Input
            id={`months-${calendar.knowledge_id}`}
            value={names}
            onChange={(event) => setNames(event.target.value)}
          />
        </FieldTile>
        <Button
          variant='outline'
          disabled={renameReason !== null}
          disabledReason={renameReason ?? undefined}
          onClick={() => rename.mutate()}
        >
          Rename
        </Button>
      </div>
    </div>
  )
}

function Calendars({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | null
}) {
  const [record, setRecord] = useState('')
  const adopt = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:adopt', {
          body: { knowledge_id: Number(record) },
        })
      ),
    success: 'A calendar began to count the year',
    onDone: () => setRecord(''),
  })
  const reason =
    blocked ??
    (record === '' ? PICK_RECORD : null) ??
    (adopt.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {data.calendars.length === 0 ? (
        <Muted>
          No people counts the year yet; astronomy records become calendars.
        </Muted>
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/year:grid-cols-2'>
          <Paged items={data.calendars}>
            {(calendar) => (
              <CalendarCard
                key={`${calendar.knowledge_id}-${calendar.month_names.join()}`}
                calendar={calendar}
                blocked={blocked}
              />
            )}
          </Paged>
        </div>
      )}
      {data.astronomy_records.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <FieldTile label='Make a record keep a calendar'>
            <Select value={record} onValueChange={setRecord}>
              <SelectTrigger aria-label='Astronomy record'>
                <SelectValue placeholder='Astronomy record' />
              </SelectTrigger>
              <SelectContent>
                {data.astronomy_records.map((item) => (
                  <SelectItem key={item.id} value={String(item.id)}>
                    {item.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FieldTile>
          <Button
            variant='outline'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => adopt.mutate()}
          >
            <BookOpen />
            Keep a calendar
          </Button>
        </div>
      )}
    </div>
  )
}

function controlGroups(data: WorldSeasons): AdjustGroup[] {
  return [
    {
      title: 'The year',
      fields: [
        {
          key: `${YEAR_KEY}axial_tilt`,
          label: 'Axial tilt',
          value: data.axial_tilt ?? 0,
          min: 0,
          max: TILT_MAX,
        },
        {
          key: `${YEAR_KEY}year_length_days`,
          label: 'Days a year',
          value: data.year_length_days ?? 1,
          min: 1,
        },
        {
          key: `${YEAR_KEY}day_length_hours`,
          label: 'Hours a day',
          value: data.day_length_hours ?? 1,
          min: 1,
        },
      ],
    },
    ...data.seasons.map((season) => ({
      title: season.name,
      fields: [
        {
          key: `${SEASON_KEY}${season.id}:share_pct`,
          label: 'Share of the year',
          value: season.share_pct,
          min: 1,
          max: PERCENT,
        },
        {
          key: `${SEASON_KEY}${season.id}:temperature_shift`,
          label: 'Warmth',
          value: season.temperature_shift,
          min: -SHIFT,
          max: SHIFT,
        },
        {
          key: `${SEASON_KEY}${season.id}:rain_shift`,
          label: 'Rain',
          value: season.rain_shift,
          min: -SHIFT,
          max: SHIFT,
        },
        {
          key: `${SEASON_KEY}${season.id}:growth`,
          label: 'Crop growth',
          value: season.growth,
          min: 0,
          max: PERCENT,
        },
        {
          key: `${SEASON_KEY}${season.id}:campaign`,
          label: 'Fit for war',
          value: season.campaign,
          min: 0,
          max: PERCENT,
        },
        {
          key: `${SEASON_KEY}${season.id}:travel`,
          label: 'Ease of travel',
          value: season.travel,
          min: 0,
          max: PERCENT,
        },
      ],
    })),
  ]
}

function SeasonNames({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | null
}) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/year:grid-cols-2 @xl/year:grid-cols-3'>
      {data.seasons.map((season) => (
        <SeasonName
          key={`${season.id}-${season.name}`}
          season={season}
          blocked={blocked}
        />
      ))}
    </div>
  )
}

function SeasonName({
  season,
  blocked,
}: {
  season: Season
  blocked: string | null
}) {
  const [name, setName] = useState(season.name)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:edit', {
          body: { season_id: season.id, name: name.trim() },
        })
      ),
    success: 'The season was renamed',
  })
  const reason =
    blocked ??
    (name.trim() === '' ? 'Write a name.' : null) ??
    (name.trim() === season.name ? 'This is the present name.' : null) ??
    (save.isPending ? WORKING : null)
  return (
    <form
      className='flex min-w-0 items-end gap-2'
      onSubmit={(event) => {
        event.preventDefault()
        if (reason === null) save.mutate()
      }}
    >
      <FieldTile
        id={`season-name-${season.id}`}
        label={`Name of season ${season.position + 1}`}
        className='flex-1'
      >
        <Input
          id={`season-name-${season.id}`}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </FieldTile>
      <Button
        type='submit'
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
      >
        Rename
      </Button>
    </form>
  )
}

function YearControls({ data }: { data: WorldSeasons }) {
  const { reason } = useGodGate()
  const run = ({ key, value }: { key: string; value: number }) => {
    if (key.startsWith(YEAR_KEY)) {
      const field = key.slice(YEAR_KEY.length)
      return unwrap(
        api.POST('/api/actions/seasons:calendar', {
          body: {
            world_id: data.world_id,
            [field]: value,
            regenerate_seasons: field === 'axial_tilt',
          },
        })
      )
    }
    const [seasonId, field] = key.slice(SEASON_KEY.length).split(':')
    return unwrap(
      api.POST('/api/actions/seasons:edit', {
        body: { season_id: Number(seasonId), [field]: value },
      })
    )
  }
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-md p-3 sealed-well'>
      <div className='flex min-w-0 flex-col gap-0.5'>
        <Text weight='semibold'>Shape the year</Text>
        <Muted variant='caption'>
          Every value above can be set here. A new axial tilt redraws the
          seasons from the sky; every change goes into the ledger and can be
          undone.
        </Muted>
      </div>
      <SeasonNames data={data} blocked={reason()} />
      <AdjustStats
        id={`world-${data.world_id}-year`}
        groups={controlGroups(data)}
        run={run}
      />
    </div>
  )
}

export function WorldSeasonsSection({ worldId }: { worldId: number }) {
  const { reason } = useGodGate()
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
  const blocked = reason()
  return (
    <Section
      id='section-seasons'
      title='Climate and seasons'
      description='The age the sky has laid on this world, how its year turns, the calendars its peoples keep and the years they remember.'
      icon={CalendarDays}
    >
      {!data ? (
        <LoadingBlock label='Reading the sky' />
      ) : (
        <div className='@container/year flex min-w-0 flex-col gap-4'>
          <ClimateAge
            key={data.climate?.era ?? 'none'}
            data={data}
            blocked={blocked}
          />
          <YearTiles data={data} />
          <KpiTileRow data={data} />
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>The year, in order</Label>
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/year:grid-cols-2 @2xl/year:grid-cols-3'>
              {data.seasons.map((season, index) => (
                <SeasonCard
                  key={season.id}
                  season={season}
                  index={index}
                  seasons={data.seasons}
                  worldId={worldId}
                  blocked={blocked}
                />
              ))}
            </div>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Calendars</Label>
            <Calendars data={data} blocked={blocked} />
          </div>
          <SeasonCalendarPanel data={data} />
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Years remembered</Label>
            {data.notable_years.length === 0 ? (
              <Muted>
                No year stands out yet; hungry, plentiful and wild years are
                written here.
              </Muted>
            ) : (
              <Timeline label='Years remembered'>
                <Paged items={data.notable_years} as='li'>
                  {(year, index) => {
                    const kind = named(NOTABLE, year.kind)
                    return (
                      <TimelineItem
                        key={year.id}
                        icon={kind.icon}
                        tone={
                          kind.tone === 'danger'
                            ? 'destructive'
                            : kind.tone === 'success'
                              ? 'success'
                              : 'warning'
                        }
                        title={year.name}
                        timestamp={`Year ${year.year} · epoch ${year.epoch}`}
                        last={index === data.notable_years.length - 1}
                      >
                        <Muted variant='caption'>{kind.label}</Muted>
                      </TimelineItem>
                    )
                  }}
                </Paged>
              </Timeline>
            )}
          </div>
          <YearControls data={data} />
        </div>
      )}
    </Section>
  )
}

function KpiTileRow({ data }: { data: WorldSeasons }) {
  const growing = data.seasons.reduce<Season | null>(
    (best, season) =>
      best === null || season.growth > best.growth ? season : best,
    null
  )
  const campaign = data.seasons.reduce<Season | null>(
    (best, season) =>
      best === null || season.campaign > best.campaign ? season : best,
    null
  )
  if (!growing || !campaign) return null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/year:grid-cols-2'>
      <KpiTile
        label='Growing season'
        value={growing.name}
        icon={Sprout}
        tone='success'
        hint='The harvest of every sampled year is read in this season'
      />
      <KpiTile
        label='Campaign season'
        value={campaign.name}
        icon={Swords}
        tone='danger'
        hint='Armies meet most often in this season'
      />
    </div>
  )
}
