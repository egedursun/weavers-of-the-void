import { useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bed,
  CalendarDays,
  CalendarPlus,
  Clock,
  Moon,
  Plus,
  Save,
  Sprout,
  Trash2,
  Unlock,
  Waves,
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
  FieldTile,
  KpiTile,
  MiniStat,
  Paged,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { NOTABLE, named } from '@/features/entity/environment/labels'
import {
  AdjustPanel,
  Card,
  Held,
  Name,
  NumberField,
  SwitchField,
  Tile,
} from '@/features/entity/wilds/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { SeasonOnsets } from './SeasonOnsets'
import { SeasonWheel } from './SeasonWheel'
import { TRADITION, fieldLabel } from './calendarLabels'

type WorldSeasons = components['schemas']['WorldSeasonsView']
type CalendarView = components['schemas']['WorldCalendarView']
type CalendarDetail = components['schemas']['CalendarDetail']
type HolyDay = components['schemas']['HolyDayDetail']
type Tradition = components['schemas']['SeasonTradition']
type Season = components['schemas']['SeasonView']
type NotableYear = components['schemas']['NotableYearView']

const WORKING = 'Working on it.'
const ALL_YEAR = 'all'
const NONE = 'none'
const PERCENT = 100
const SHOWN = 6

function calendarKey(worldId: number) {
  return ['world', 'calendar', worldId] as const
}

function wholeOrNull(text: string): number | null {
  const value = Number(text)
  return text.trim() !== '' && Number.isInteger(value) ? value : null
}

function seasonName(seasons: Season[], position: number | null | undefined) {
  if (position === null || position === undefined) return 'All year'
  return (
    seasons.find((season) => season.position === position)?.name ??
    `Season ${position + 1}`
  )
}

function keeping(tradition: Tradition): string {
  const parts = [named(TRADITION, tradition.kind).label]
  if (tradition.calendar_name)
    parts.push(`date fixed by ${tradition.calendar_name}`)
  if (tradition.in_season === false) parts.push('drifted off its season')
  if (tradition.in_season === true) parts.push('kept in its season')
  return parts.join(' · ')
}

function TraditionTile({ tradition }: { tradition: Tradition }) {
  const kind = named(TRADITION, tradition.kind)
  return (
    <Tile
      spec={{ label: tradition.name, icon: kind.icon, tone: kind.tone }}
      caption={keeping(tradition)}
      dim={tradition.in_season === false}
      aside={
        tradition.held.length > 0 ? (
          <Badge size='sm' variant='default'>
            Held
          </Badge>
        ) : undefined
      }
    />
  )
}

function TraditionList({ items }: { items: Tradition[] }) {
  const more = useShowMore(items, SHOWN)
  return (
    <>
      {more.visible.map((item) => (
        <TraditionTile key={item.id} tradition={item} />
      ))}
      <ShowMore state={more} noun={['tradition', 'traditions']} />
    </>
  )
}

function FestivalWheel({
  data,
  view,
}: {
  data: WorldSeasons
  view: CalendarView
}) {
  const loose = view.traditions.filter((item) => item.season_position === null)
  return (
    <div
      data-surface='TraditionSeasonBinding'
      className='grid min-w-0 grid-cols-1 gap-3 @md/year:grid-cols-2 @2xl/year:grid-cols-3'
    >
      {data.seasons.map((season) => {
        const kept = view.traditions.filter(
          (item) => item.season_position === season.position
        )
        return (
          <Card
            key={season.id}
            title={season.name}
            icon={Sprout}
            tone={season.growth >= PERCENT / 2 ? 'success' : 'muted'}
            hint={`Growth ${season.growth} · a feast here costs less in plenty`}
          >
            {kept.length === 0 ? (
              <Muted variant='caption'>No tradition is kept in it.</Muted>
            ) : (
              <TraditionList items={kept} />
            )}
          </Card>
        )
      })}
      {loose.length > 0 && (
        <Card
          title='All year'
          icon={CalendarDays}
          tone='muted'
          hint='Customs with no season of their own'
        >
          <TraditionList items={loose} />
        </Card>
      )}
    </div>
  )
}

function DayAndNight({ view }: { view: CalendarView }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/year:grid-cols-3'>
      <MiniStat
        icon={Clock}
        label='Hours a day'
        value={view.day_length_hours ?? '—'}
        tone='info'
        hint={`From ${plural(view.long_day_hours, 'hour', 'hours')} folk rest at noon or keep vigil at night`}
      />
      <KpiTile
        label='Long days'
        value={view.long_days ? 'Yes' : 'No'}
        icon={view.long_days ? Moon : Clock}
        tone={view.long_days ? 'warning' : 'muted'}
        hint={
          view.long_days
            ? 'Communities found a midday rest or a night vigil'
            : 'Days are short enough for a single sleep'
        }
      />
      <KpiTile
        label='Sleep customs'
        value={String(view.sleep_customs)}
        icon={Bed}
        tone='verdigris'
        hint='Rest takes unrest away; vigils keep the night watch against crime'
      />
    </div>
  )
}

function HolyDayRow({
  day,
  calendar,
  seasons,
  blocked,
}: {
  day: HolyDay
  calendar: CalendarDetail
  seasons: Season[]
  blocked: string | null
}) {
  const [name, setName] = useState(day.name)
  const [season, setSeason] = useState(
    day.season_position === null ? ALL_YEAR : String(day.season_position)
  )
  const save = useGodAction({
    writes: [{ lever: 'calendar:holy_day' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:holy_day', {
          body: {
            knowledge_id: calendar.knowledge_id,
            index: day.index,
            name: name.trim(),
            season_position: season === ALL_YEAR ? null : Number(season),
            found_tradition: false,
          },
        })
      ),
    success: 'The holy day was rewritten',
  })
  const remove = useGodAction({
    writes: [{ lever: 'calendar:holy_day_remove' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:holy_day_remove', {
          body: { knowledge_id: calendar.knowledge_id, index: day.index },
        })
      ),
    success: 'The holy day is no longer kept',
  })
  const busy = blocked ?? (save.isPending || remove.isPending ? WORKING : null)
  const unchanged =
    name.trim() === day.name &&
    season ===
      (day.season_position === null ? ALL_YEAR : String(day.season_position))
  const saveReason =
    busy ??
    (name.trim() === '' ? 'Write a name.' : null) ??
    (unchanged ? 'Nothing has changed.' : null)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Text weight='medium' className='flex-1' truncate>
          {day.name}
        </Text>
        {day.year !== null && (
          <Badge size='sm' variant='secondary'>{`Year ${day.year}`}</Badge>
        )}
        <Badge size='sm' variant='info'>
          {seasonName(seasons, day.season_position)}
        </Badge>
        {day.tradition_id !== null && (
          <Name
            item={{ id: day.tradition_id, name: day.tradition_name ?? 'Fast' }}
          />
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <FieldTile
          id={`holy-${calendar.knowledge_id}-${day.index}`}
          label='Name'
          className='flex-1 basis-40'
        >
          <Input
            id={`holy-${calendar.knowledge_id}-${day.index}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </FieldTile>
        <SeasonPicker seasons={seasons} value={season} onChange={setSeason} />
        <Button
          act={save}
          variant='outline'
          disabled={saveReason !== null}
          disabledReason={saveReason ?? undefined}
          onClick={() => save.mutate()}
        >
          <Save />
          Save
        </Button>
        <Button
          act={remove}
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Remove
        </Button>
      </div>
    </li>
  )
}

function SeasonPicker({
  seasons,
  value,
  onChange,
}: {
  seasons: Season[]
  value: string
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <FieldTile id={id} label='Season'>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id={id} aria-label='Season'>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_YEAR}>All year</SelectItem>
          {seasons.map((season) => (
            <SelectItem key={season.id} value={String(season.position)}>
              {season.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldTile>
  )
}

function NewHolyDay({
  calendar,
  data,
  blocked,
}: {
  calendar: CalendarDetail
  data: WorldSeasons
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [season, setSeason] = useState(ALL_YEAR)
  const [year, setYear] = useState(NONE)
  const [fast, setFast] = useState(true)
  const add = useGodAction({
    writes: [{ lever: 'calendar:holy_day' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:holy_day', {
          body: {
            knowledge_id: calendar.knowledge_id,
            name: name.trim(),
            season_position: season === ALL_YEAR ? null : Number(season),
            notable_year_id: year === NONE ? null : Number(year),
            found_tradition: fast && year !== NONE,
          },
        })
      ),
    success: 'A new holy day is kept',
    onDone: () => setName(''),
  })
  const reason =
    blocked ??
    (name.trim() === '' ? 'Name the holy day.' : null) ??
    (add.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2 rounded-md p-2 sealed-well'>
      <FieldTile
        id={`holy-new-${calendar.knowledge_id}`}
        label='New holy day'
        className='flex-1 basis-40'
      >
        <Input
          id={`holy-new-${calendar.knowledge_id}`}
          value={name}
          placeholder='The name of the holy day'
          onChange={(event) => setName(event.target.value)}
        />
      </FieldTile>
      <SeasonPicker
        seasons={data.seasons}
        value={season}
        onChange={setSeason}
      />
      <FieldTile label='Remembers'>
        <Select value={year} onValueChange={setYear}>
          <SelectTrigger aria-label='Remembered year'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={NONE}>No year</SelectItem>
            {data.notable_years.map((item) => (
              <SelectItem key={item.id} value={String(item.id)}>
                {item.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FieldTile>
      <SwitchField label='Found its fast' checked={fast} onChange={setFast} />
      <Button
        act={add}
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => add.mutate()}
      >
        <CalendarPlus />
        Keep it
      </Button>
    </div>
  )
}

function AnchorField({
  calendar,
  blocked,
}: {
  calendar: CalendarDetail
  blocked: string | null
}) {
  const [anchor, setAnchor] = useState(String(calendar.anchor_year))
  const save = useGodAction({
    writes: [{ lever: 'calendar:anchor' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/calendar:anchor', {
          body: {
            knowledge_id: calendar.knowledge_id,
            anchor_year: wholeOrNull(anchor) ?? 0,
          },
        })
      ),
    success: 'The calendar counts from a new year',
  })
  const parsed = wholeOrNull(anchor)
  const reason =
    blocked ??
    (parsed === null || parsed < 0 ? 'Write a year of zero or more.' : null) ??
    (parsed === calendar.anchor_year ? 'This is the present year.' : null) ??
    (save.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 items-end gap-2'>
      <NumberField
        label='Counts its years from'
        value={anchor}
        min={0}
        onChange={setAnchor}
      />
      <Button
        act={save}
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Set
      </Button>
    </div>
  )
}

function HolyDays({
  data,
  view,
  blocked,
}: {
  data: WorldSeasons
  view: CalendarView
  blocked: string | null
}) {
  if (view.calendars.length === 0)
    return (
      <Muted>
        No calendar keeps holy days yet; once a people counts the year, its
        hungry years become fasts.
      </Muted>
    )
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3'>
      <Paged items={view.calendars}>
        {(calendar) => (
          <Card
            key={calendar.knowledge_id}
            title={calendar.name}
            icon={CalendarPlus}
            tone='verdigris'
            hint={`Counts from year ${calendar.anchor_year} · kept by ${calendar.keepers}`}
          >
            {calendar.holy_days.length === 0 ? (
              <Muted variant='caption'>No holy day yet.</Muted>
            ) : (
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={calendar.holy_days} as='li'>
                  {(day) => (
                    <HolyDayRow
                      key={`${day.index}-${day.name}-${day.season_position}`}
                      day={day}
                      calendar={calendar}
                      seasons={data.seasons}
                      blocked={blocked}
                    />
                  )}
                </Paged>
              </ul>
            )}
            <NewHolyDay calendar={calendar} data={data} blocked={blocked} />
            <AnchorField
              key={calendar.anchor_year}
              calendar={calendar}
              blocked={blocked}
            />
          </Card>
        )}
      </Paged>
    </div>
  )
}

function SeasonRow({
  season,
  last,
  blocked,
}: {
  season: Season
  last: boolean
  blocked: string | null
}) {
  const remove = useGodAction({
    writes: [{ lever: 'seasons:remove' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:remove', {
          body: { season_id: season.id },
        })
      ),
    success: 'The season is gone from the year',
  })
  const release = useGodAction({
    writes: [{ lever: 'seasons:release' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:release', {
          body: { season_id: season.id },
        })
      ),
    success: 'The season is no longer held',
  })
  const busy =
    blocked ?? (remove.isPending || release.isPending ? WORKING : null)
  const removeReason =
    busy ?? (last ? 'A world keeps at least one season.' : null)
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Text weight='medium' className='flex-1' truncate>
        {season.name}
      </Text>
      {season.edited ? (
        <Button
          act={release}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => release.mutate()}
        >
          <Unlock />
          Release the hold
        </Button>
      ) : (
        <Badge size='sm' variant='secondary'>
          Follows the sky
        </Badge>
      )}
      <Button
        act={remove}
        size='sm'
        variant='ghost'
        disabled={removeReason !== null}
        disabledReason={removeReason ?? undefined}
        onClick={() => remove.mutate()}
      >
        <Trash2 />
        Remove
      </Button>
    </li>
  )
}

const NEW_SEASON = {
  share_pct: '10',
  temperature_shift: '0',
  rain_shift: '0',
  growth: '50',
  travel: '50',
  campaign: '50',
}

const NEW_SEASON_LABELS: Record<keyof typeof NEW_SEASON, string> = {
  share_pct: 'Share of the year',
  temperature_shift: 'Warmth',
  rain_shift: 'Rain',
  growth: 'Crop growth',
  travel: 'Ease of travel',
  campaign: 'Fit for war',
}

function NewSeason({
  data,
  blocked,
}: {
  data: WorldSeasons
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [values, setValues] = useState(NEW_SEASON)
  const add = useGodAction({
    writes: [{ lever: 'seasons:add' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:add', {
          body: {
            world_id: data.world_id,
            name: name.trim(),
            temperature_shift: wholeOrNull(values.temperature_shift) ?? 0,
            rain_shift: wholeOrNull(values.rain_shift) ?? 0,
            growth: wholeOrNull(values.growth) ?? 0,
            travel: wholeOrNull(values.travel) ?? 0,
            campaign: wholeOrNull(values.campaign) ?? 0,
            share_pct: wholeOrNull(values.share_pct) ?? 1,
          },
        })
      ),
    success: 'A new season turns in the year',
    onDone: () => setName(''),
  })
  const reason =
    blocked ??
    (name.trim() === '' ? 'Name the season.' : null) ??
    (Object.values(values).some((value) => wholeOrNull(value) === null)
      ? 'Write whole numbers.'
      : null) ??
    (add.isPending ? WORKING : null)
  const full =
    data.seasons.length >= data.seasons_max
      ? `A world keeps at most ${plural(data.seasons_max, 'season', 'seasons')}.`
      : null
  const addReason = full ?? reason
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md p-2 sealed-well'>
      <FieldTile id={`season-new-${data.world_id}`} label='Add a season'>
        <Input
          id={`season-new-${data.world_id}`}
          value={name}
          placeholder='The name of the season'
          onChange={(event) => setName(event.target.value)}
        />
      </FieldTile>
      <div className='grid min-w-0 grid-cols-2 gap-2 @lg/year:grid-cols-6'>
        {(Object.keys(NEW_SEASON) as (keyof typeof NEW_SEASON)[]).map((key) => (
          <NumberField
            key={key}
            label={NEW_SEASON_LABELS[key]}
            value={values[key]}
            onChange={(value) =>
              setValues((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
      </div>
      <Button
        act={add}
        className='self-start'
        disabled={addReason !== null}
        disabledReason={addReason ?? undefined}
        onClick={() => add.mutate()}
      >
        <Plus />
        Add the season
      </Button>
    </div>
  )
}

function MoonsAndTides({
  data,
  view,
  blocked,
}: {
  data: WorldSeasons
  view: CalendarView
  blocked: string | null
}) {
  const [moons, setMoons] = useState(String(data.moon_count ?? 0))
  const [tides, setTides] = useState(String(data.tidal_strength ?? 0))
  const save = useGodAction({
    writes: [{ lever: 'seasons:moons' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:moons', {
          body: {
            world_id: data.world_id,
            moon_count: wholeOrNull(moons),
            tidal_strength: wholeOrNull(tides),
          },
        })
      ),
    success: 'The moons and tides are set and held',
  })
  const release = useGodAction({
    writes: [{ lever: 'seasons:calendar_release' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/seasons:calendar_release', {
          body: { world_id: data.world_id, fields: view.calendar_locked },
        })
      ),
    success: 'The heavens decide again',
  })
  const busy = blocked ?? (save.isPending || release.isPending ? WORKING : null)
  const reason =
    busy ??
    (wholeOrNull(moons) === null || wholeOrNull(tides) === null
      ? 'Write whole numbers.'
      : null)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField label='Moons' value={moons} min={0} onChange={setMoons} />
        <NumberField
          label='Tides'
          value={tides}
          min={0}
          max={PERCENT}
          onChange={setTides}
        />
        <Button
          act={save}
          variant='outline'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => save.mutate()}
        >
          <Waves />
          Set and hold
        </Button>
      </div>
      <Held
        act={release}
        keys={view.calendar_locked}
        label={fieldLabel}
        busy={busy}
        onRelease={() => release.mutate()}
      />
    </div>
  )
}

function NotableRow({
  year,
  blocked,
}: {
  year: NotableYear
  blocked: string | null
}) {
  const [name, setName] = useState(year.name)
  const [magnitude, setMagnitude] = useState(String(year.magnitude))
  const save = useGodAction({
    writes: [{ lever: 'year:edit' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/year:edit', {
          body: {
            notable_id: year.id,
            name: name.trim(),
            magnitude: wholeOrNull(magnitude) ?? year.magnitude,
          },
        })
      ),
    success: 'The year is remembered anew',
  })
  const remove = useGodAction({
    writes: [{ lever: 'year:delete' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/year:delete', {
          body: { notable_id: year.id },
        })
      ),
    success: 'The year is struck from memory',
  })
  const busy = blocked ?? (save.isPending || remove.isPending ? WORKING : null)
  const parsed = wholeOrNull(magnitude)
  const reason =
    busy ??
    (name.trim() === '' ? 'Write a name.' : null) ??
    (parsed === null || parsed < 0 || parsed > PERCENT
      ? 'Magnitude runs from 0 to 100.'
      : null) ??
    (name.trim() === year.name && parsed === year.magnitude
      ? 'Nothing has changed.'
      : null)
  const kind = named(NOTABLE, year.kind)
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Badge
        size='sm'
        variant='secondary'
      >{`${kind.label} · ${year.year}`}</Badge>
      <FieldTile
        id={`notable-${year.id}`}
        label='Name'
        className='flex-1 basis-40'
      >
        <Input
          id={`notable-${year.id}`}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </FieldTile>
      <NumberField
        label='Magnitude'
        value={magnitude}
        min={0}
        max={PERCENT}
        onChange={setMagnitude}
      />
      <Button
        act={save}
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Save
      </Button>
      <Button
        act={remove}
        variant='ghost'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => remove.mutate()}
      >
        <Trash2 />
        Forget
      </Button>
    </li>
  )
}

export function SeasonCalendarPanel({ data }: { data: WorldSeasons }) {
  const { reason } = useGodGate()
  const blocked = reason()
  const query = useQuery({
    queryKey: calendarKey(data.world_id),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/calendar', {
          params: { path: { world_id: data.world_id } },
        })
      ),
  })
  const view = query.data
  if (!view) return null
  return (
    <div
      data-surface='SeasonCalendarPanel'
      className='flex min-w-0 flex-col gap-4'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>The wheel of the year</Label>
        <SeasonWheel
          seasons={data.seasons}
          label={`${plural(data.seasons.length, 'season', 'seasons')} of at most ${data.seasons_max}, sized by their share of the year`}
        />
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Festivals through the year</Label>
        <FestivalWheel data={data} view={view} />
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Day and night</Label>
        <DayAndNight view={view} />
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Holy days</Label>
        <HolyDays data={data} view={view} blocked={blocked} />
      </div>
      <AdjustPanel
        writes={[
          { lever: 'seasons:add' },
          { lever: 'seasons:release' },
          { lever: 'seasons:remove' },
        ]}
        title='Add, remove and hold seasons'
        note='A season shaped by hand is held when the year is redrawn from a new tilt. Adding a season takes its share from the others in proportion; removing one gives it back.'
        label='Seasons and moons'
      >
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={data.seasons} as='li'>
            {(season) => (
              <SeasonRow
                key={season.id}
                season={season}
                last={data.seasons.length <= 1}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
        <NewSeason data={data} blocked={blocked} />
      </AdjustPanel>
      <AdjustPanel
        writes={[
          { lever: 'seasons:onset' },
          { lever: 'seasons:onset_clear' },
          { lever: 'seasons:onset_release' },
        ]}
        title='Early, late and failed seasons'
        note='Each year the engine draws whether a season comes early, on time, late or fails; a failed season does not bring its water. Set one and it is held.'
        label='Season onsets'
      >
        <SeasonOnsets data={data} blocked={blocked} />
      </AdjustPanel>
      <AdjustPanel
        writes={[
          { lever: 'seasons:calendar_release' },
          { lever: 'seasons:moons' },
        ]}
        title='Moons and tides'
        note='Moons and tides set here are held until released.'
        label='Moons and tides'
      >
        <MoonsAndTides
          key={`${data.moon_count}-${data.tidal_strength}`}
          data={data}
          view={view}
          blocked={blocked}
        />
      </AdjustPanel>
      <AdjustPanel
        writes={[{ lever: 'year:delete' }, { lever: 'year:edit' }]}
        title='Rewrite remembered years'
        note='Rename a year, change how strongly it is remembered, or strike it from memory; holy days that kept it lose their year.'
        label='Remembered years'
      >
        {data.notable_years.length === 0 ? (
          <Muted>No year is remembered yet.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={data.notable_years} as='li'>
              {(year) => (
                <NotableRow
                  key={`${year.id}-${year.name}-${year.magnitude}`}
                  year={year}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
      </AdjustPanel>
    </div>
  )
}
