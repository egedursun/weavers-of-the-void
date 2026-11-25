import { useState } from 'react'
import {
  CloudSun,
  Hourglass,
  Link2Off,
  Plus,
  Scroll,
  Undo2,
  Waypoints,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormRow, Medallion, TimelineItem, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { NOTABLE, WEATHER, named } from './labels'

type RegionEnvironment = components['schemas']['RegionEnvironmentView']
type WeatherKind = components['schemas']['WeatherKind']
type NotableYearKind = components['schemas']['NotableYearKind']

const WORKING = 'Working…'
const ALL_SEASONS = 'all'
const DEFAULT_STRENGTH = 75
const DEFAULT_MAGNITUDE = 50
const MAX_PERCENT = 100

const WEATHER_CHOICES: Record<string, string> = Object.fromEntries(
  Object.entries(WEATHER).map(([key, item]) => [key, item.label])
)
const NOTABLE_CHOICES: Record<string, string> = Object.fromEntries(
  Object.entries(NOTABLE).map(([key, item]) => [key, item.label])
)

function clampPercent(raw: string): number {
  const value = Number(raw)
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(MAX_PERCENT, Math.round(value)))
}

export function ForgeLey({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const [other, setOther] = useState('')
  const [strength, setStrength] = useState(String(DEFAULT_STRENGTH))
  const forge = useGodAction({
    writes: [{ lever: 'ley:forge' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/ley:forge', {
          body: {
            first_region_id: regionId,
            second_region_id: Number(other),
            strength: clampPercent(strength),
          },
        })
      ),
    success: 'The ley line is forged',
  })
  const unforge = useGodAction({
    writes: [{ lever: 'ley:unforge' }],
    run: (lineId: number) =>
      unwrap(
        api.POST('/api/actions/ley:unforge', { body: { line_id: lineId } })
      ),
    success: 'The line is left to the land',
  })
  const busy =
    reason() ?? (forge.isPending || unforge.isPending ? WORKING : null)
  const choices = Object.fromEntries(
    ground.neighbours.map((item) => [String(item.id), item.name])
  )
  const forged = ground.ley_lines.filter((line) => line.forged)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {forged.map((line) => (
        <div
          key={line.id}
          className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'
        >
          <Medallion icon={Waypoints} tone='verdigris' size='sm' />
          <Text className='min-w-0 flex-1'>
            {`Forged to ${line.other_region_name}`}
          </Text>
          <Badge size='sm' variant='info'>
            Held by your hand
          </Badge>
          <Button
            act={unforge}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => unforge.mutate(line.id)}
          >
            <Link2Off />
            Leave it to the land
          </Button>
        </div>
      ))}
      {ground.neighbours.length === 0 && (
        <Muted>No neighbouring land to join a line to.</Muted>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-48 flex-1'>
          <MindPicker
            label='Join to'
            value={other}
            table={choices}
            blocked={busy}
            placeholder='Choose a neighbour'
            onPick={setOther}
          />
        </div>
        <div className='w-24'>
          <FormRow label='Strength'>
            {(id) => (
              <Input
                id={id}
                type='number'
                min={0}
                max={MAX_PERCENT}
                value={strength}
                className='w-24'
                onChange={(event) => setStrength(event.target.value)}
              />
            )}
          </FormRow>
        </div>
        <Button
          act={forge}
          size='sm'
          disabled={busy !== null || other === ''}
          disabledReason={
            busy ??
            (ground.neighbours.length === 0
              ? 'No neighbouring land to join a line to'
              : other === ''
                ? 'Choose a neighbour'
                : undefined)
          }
          onClick={() => forge.mutate(undefined)}
        >
          <Plus />
          Forge a ley line
        </Button>
      </div>
    </div>
  )
}

export function HoldWeather({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const [kind, setKind] = useState<string>('clear')
  const [epochs, setEpochs] = useState('1')
  const [season, setSeason] = useState(ALL_SEASONS)
  const hold = useGodAction({
    writes: [{ lever: 'weather:force' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/weather:force', {
          body: {
            region_id: regionId,
            kind: kind as WeatherKind,
            epochs: Math.max(1, Math.round(Number(epochs) || 1)),
            season_position: season === ALL_SEASONS ? null : Number(season),
          },
        })
      ),
    success: 'The weather is held',
  })
  const release = useGodAction({
    writes: [{ lever: 'weather:release' }],
    run: (forcedId: number) =>
      unwrap(
        api.POST('/api/actions/weather:release', {
          body: { forced_id: forcedId },
        })
      ),
    success: 'The sky goes its own way again',
  })
  const busy =
    reason() ?? (hold.isPending || release.isPending ? WORKING : null)
  const seasons: Record<string, string> = {
    [ALL_SEASONS]: 'Every season',
    ...Object.fromEntries(
      ground.forecast.map((item, index) => [
        String(index),
        item.season_name ?? `Season ${index + 1}`,
      ])
    ),
  }
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Paged items={ground.forced_weather}>
        {(item) => (
          <div
            key={item.id}
            className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'
          >
            <Medallion
              icon={named(WEATHER, item.kind).icon}
              tone='info'
              size='sm'
            />
            <div className='flex min-w-0 flex-1 flex-col'>
              <Text weight='semibold'>{item.label}</Text>
              <Muted variant='caption'>
                {`${item.season_position === null ? 'Every season' : (seasons[String(item.season_position)] ?? 'One season')}, epochs ${item.from_epoch} to ${item.until_epoch}${item.son_id !== null ? ', held by a son' : ''}`}
              </Muted>
            </div>
            <Button
              act={release}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(item.id)}
            >
              <Undo2 />
              Release
            </Button>
          </div>
        )}
      </Paged>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Weather'
            value={kind}
            table={WEATHER_CHOICES}
            blocked={busy}
            onPick={setKind}
          />
        </div>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Season'
            value={season}
            table={seasons}
            blocked={busy}
            onPick={setSeason}
          />
        </div>
        <div className='w-20'>
          <FormRow label='Epochs'>
            {(id) => (
              <Input
                id={id}
                type='number'
                min={1}
                value={epochs}
                className='w-20'
                onChange={(event) => setEpochs(event.target.value)}
              />
            )}
          </FormRow>
        </div>
        <Button
          act={hold}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => hold.mutate(undefined)}
        >
          <CloudSun />
          Hold this weather
        </Button>
      </div>
    </div>
  )
}

export function NotableYears({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const [kind, setKind] = useState<string>('plenty')
  const [magnitude, setMagnitude] = useState(String(DEFAULT_MAGNITUDE))
  const [name, setName] = useState('')
  const [weather, setWeather] = useState<string>('storm')
  const write = useGodAction({
    writes: [{ lever: 'year:force_notable' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/year:force_notable', {
          body: {
            region_id: regionId,
            kind: kind as NotableYearKind,
            magnitude: clampPercent(magnitude),
            name: name.trim() || null,
            weather: kind === 'weather' ? (weather as WeatherKind) : null,
          },
        })
      ),
    success: 'The year is remembered',
  })
  const busy = reason() ?? (write.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {ground.notable_years.length === 0 ? (
        <Muted>This land remembers no year above the others.</Muted>
      ) : (
        <div className='flex min-w-0 flex-col'>
          <Paged items={ground.notable_years}>
            {(year, index) => {
              const item = named(NOTABLE, year.kind)
              return (
                <TimelineItem
                  key={year.id}
                  icon={item.icon}
                  tone={
                    item.tone === 'danger'
                      ? 'destructive'
                      : item.tone === 'success'
                        ? 'success'
                        : 'warning'
                  }
                  title={year.name}
                  timestamp={`Year ${year.year} · epoch ${year.epoch}`}
                  last={index === ground.notable_years.length - 1}
                >
                  <Muted variant='caption'>
                    {year.legend_id !== null
                      ? `${item.label}; told as a legend`
                      : item.label}
                  </Muted>
                </TimelineItem>
              )
            }}
          </Paged>
        </div>
      )}
      <Label variant='overline'>Set down a year</Label>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-36 flex-1'>
          <MindPicker
            label='Kind'
            value={kind}
            table={NOTABLE_CHOICES}
            blocked={busy}
            onPick={setKind}
          />
        </div>
        {kind === 'weather' && (
          <div className='min-w-36 flex-1'>
            <MindPicker
              label='Weather'
              value={weather}
              table={WEATHER_CHOICES}
              blocked={busy}
              onPick={setWeather}
            />
          </div>
        )}
        <div className='w-20'>
          <FormRow label='Weight'>
            {(id) => (
              <Input
                id={id}
                type='number'
                min={0}
                max={MAX_PERCENT}
                value={magnitude}
                className='w-20'
                onChange={(event) => setMagnitude(event.target.value)}
              />
            )}
          </FormRow>
        </div>
        <div className='min-w-48 flex-1'>
          <FormRow label='Name'>
            {(id) => (
              <Input
                id={id}
                value={name}
                placeholder='Named by the land if empty'
                className='w-full'
                onChange={(event) => setName(event.target.value)}
              />
            )}
          </FormRow>
        </div>
        <Button
          act={write}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => write.mutate(undefined)}
        >
          <Scroll />
          Remember this year
        </Button>
      </div>
      <Muted variant='caption'>
        <Hourglass className='inline size-icon-xs' aria-hidden='true' />{' '}
        Remembered years can become legends once they are old enough.
      </Muted>
    </div>
  )
}
