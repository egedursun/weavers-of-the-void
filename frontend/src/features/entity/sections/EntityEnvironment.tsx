import { type ReactNode, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Biohazard,
  CloudSun,
  Droplets,
  Gauge,
  Gem,
  Link2,
  Lock,
  Mountain,
  Scissors,
  Shield,
  Sparkles,
  Sprout,
  Trees,
  Unlock,
  Waypoints,
  Wheat,
  type LucideIcon,
  Scroll,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'
import {
  ForgeLey,
  HoldWeather,
  NotableYears,
} from '../environment/RegionPowers'
import { BiomeMix, SeamForge } from '../environment/RegionSeams'
import { RegionTerrainSection } from '../environment/RegionTerrain'
import {
  BAND,
  COAST,
  COVER,
  LAND_USE,
  MINERALS,
  MODES,
  RIVER,
  SCARS,
  SEASONALITY_ICON,
  SOIL,
  TERRAIN,
  THERMOMETER_ICON,
  WATER,
  WEATHER,
  WEATHER_EFFECTS,
  fieldLabel,
  named,
  plain,
} from '../environment/labels'
import { seamLabel, useSeamNames } from '../environment/seams'

type RegionEnvironment = components['schemas']['RegionEnvironmentView']
type PlaceEnvironment = components['schemas']['PlaceEnvironmentView']
type Forecast = components['schemas']['WeatherForecast']
type ScarKind = components['schemas']['ScarKind']
type MaterialKind = components['schemas']['MaterialKind']
type Change = { key: string; value: number | string | boolean }

const PERCENT = 100
const HARVEST_MAX = 200
const SCAR_PREFIX = 'scar:'
const SEAM_PREFIX = 'seam:'
const WORKING = 'Working on it.'
const TERRAIN_NAMES = Object.fromEntries(
  Object.entries(TERRAIN).map(([key, value]) => [key, value.label])
)
const REGION_CHOICES: {
  key: keyof RegionEnvironment
  table: Record<string, string>
}[] = [
  { key: 'dominant_terrain', table: TERRAIN_NAMES },
  { key: 'soil', table: SOIL },
  { key: 'river_class', table: RIVER },
  { key: 'coast_kind', table: COAST },
  {
    key: 'temperature_band',
    table: Object.fromEntries(
      Object.entries(BAND).map(([key, value]) => [key, value.label])
    ),
  },
]
const PLACE_CHOICES: {
  key: 'terrain' | 'cover' | 'water_source'
  label: string
  table: Record<string, string>
}[] = [
  {
    key: 'terrain',
    label: 'Terrain',
    table: { inherit: 'As its region', ...TERRAIN_NAMES },
  },
  { key: 'cover', label: 'Cover', table: COVER },
  { key: 'water_source', label: 'Water', table: WATER },
]
const YES_NO = { yes: 'Yes', no: 'No' }

function environmentKey(kind: 'region' | 'place', id: number) {
  return [...loreKeys.entity(id), 'environment', kind] as const
}

function percentField(key: string, value: number, max = PERCENT) {
  return { key, label: fieldLabel(key), value, min: 0, max }
}

function Card({
  title,
  icon,
  children,
}: {
  title: string
  icon: LucideIcon
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} size='sm' />
        <Label variant='overline'>{title}</Label>
      </div>
      {children}
    </div>
  )
}

function LandHero({ ground }: { ground: RegionEnvironment }) {
  const terrain = named(TERRAIN, ground.dominant_terrain)
  const band = named(BAND, ground.temperature_band)
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={terrain.icon} tone={terrain.tone ?? 'gold'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <Text weight='semibold'>{terrain.label}</Text>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='secondary'>
            {plain(SOIL, ground.soil)}
          </Badge>
          <Badge size='sm' variant='info'>
            {band.label}
          </Badge>
          <Badge size='sm' variant='secondary'>
            {plain(RIVER, ground.river_class)}
          </Badge>
          <Badge size='sm' variant='secondary'>
            {plain(COAST, ground.coast_kind)}
          </Badge>
          {ground.ley_lines.length > 0 && (
            <Badge size='sm' variant='default'>
              {`${ground.ley_lines.length} ley ${ground.ley_lines.length === 1 ? 'line' : 'lines'}`}
            </Badge>
          )}
          {!ground.surveyed && (
            <Badge size='sm' variant='warning'>
              Not yet on the map
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}

function Vitals({ ground }: { ground: RegionEnvironment }) {
  const band = named(BAND, ground.temperature_band)
  const meter = (value: number, label: string) => ({
    value,
    max: PERCENT,
    label,
  })
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/env:grid-cols-2 @3xl/env:grid-cols-4'>
      <KpiTile
        label='Fertility'
        value={ground.fertility ?? '—'}
        icon={Sprout}
        tone='success'
        hint={`Soil ${ground.soil_fertility} of ${ground.soil_base} natural, shaped by rain, warmth, river and scars`}
        meter={meter(ground.fertility ?? 0, 'Fertility')}
      />
      <KpiTile
        label='Last harvest'
        value={`${ground.harvest_pct}%`}
        icon={Wheat}
        tone='gold'
        change={ground.harvest_pct - PERCENT}
        hint='Against a normal year; it fills or empties the granaries'
      />
      <KpiTile
        label='Temperature'
        value={band.label}
        icon={THERMOMETER_ICON}
        tone={band.tone ?? 'info'}
        hint={`${ground.temperature} on a scale of 100`}
        meter={meter(ground.temperature, 'Temperature')}
      />
      <KpiTile
        label='Rainfall'
        value={ground.rainfall}
        icon={Droplets}
        tone='info'
        meter={meter(ground.rainfall, 'Rainfall')}
      />
      <KpiTile
        label='Seasonality'
        value={ground.seasonality}
        icon={SEASONALITY_ICON}
        tone='verdigris'
        hint='How strongly the seasons swing here'
        meter={meter(ground.seasonality, 'Seasonality')}
      />
      <KpiTile
        label='Disease load'
        value={ground.disease_load}
        icon={Biohazard}
        tone='danger'
        hint='Warmth, wetland, crowding and plague ground raise it; medicine lowers it'
        meter={meter(ground.disease_load, 'Disease load')}
      />
      <KpiTile
        label='Magic density'
        value={ground.magic_density}
        icon={Sparkles}
        tone='verdigris'
        hint='Raised by ley lines; above 60 magic storms can break'
        meter={meter(ground.magic_density, 'Magic density')}
      />
      <KpiTile
        label='Defensibility'
        value={ground.defensibility}
        icon={Shield}
        tone='gold'
        hint='Rough ground, forest, rivers and chokepoints favour defenders'
        meter={meter(ground.defensibility, 'Defensibility')}
      />
    </div>
  )
}

function WeatherTile({ item }: { item: Forecast }) {
  const weather = named(WEATHER, item.kind)
  const effects = Object.entries(item.effects).filter(
    ([, value]) => value !== 0
  )
  const season = item.season_name ?? 'All year'
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          tabIndex={0}
          aria-label={`${season}: ${weather.label}`}
          className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-2'
        >
          <Medallion
            icon={weather.icon}
            tone={weather.tone ?? 'muted'}
            size='sm'
          />
          <div className='flex min-w-0 flex-col'>
            <Text weight='medium' truncate>
              {weather.label}
            </Text>
            <Muted variant='caption' truncate>
              {season}
            </Muted>
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent className='flex flex-col gap-0.5'>
        {effects.length === 0 ? (
          <Text as='span'>A calm season</Text>
        ) : (
          effects.map(([key, value]) => (
            <Text key={key} as='span'>
              {`${WEATHER_EFFECTS[key] ?? key} ${value > 0 ? '+' : ''}${value}`}
            </Text>
          ))
        )}
      </TooltipContent>
    </Tooltip>
  )
}

function LeyLines({
  ground,
  blocked,
}: {
  ground: RegionEnvironment
  blocked: string | null
}) {
  const sever = useGodAction({
    run: (lineId: number) =>
      unwrap(api.POST('/api/actions/ley:sever', { body: { line_id: lineId } })),
    success: 'The ley line is cut',
  })
  const restore = useGodAction({
    run: (lineId: number) =>
      unwrap(
        api.POST('/api/actions/ley:restore', { body: { line_id: lineId } })
      ),
    success: 'The ley line flows again',
  })
  const reason =
    blocked ?? (sever.isPending || restore.isPending ? WORKING : null)
  if (ground.ley_lines.length === 0)
    return <Muted>No ley line runs through this land.</Muted>
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      {ground.ley_lines.map((line) => (
        <li
          key={line.id}
          className='flex min-w-0 flex-wrap items-center gap-3 rounded-lg border bg-muted/30 p-2'
        >
          <Medallion
            icon={Waypoints}
            tone={line.severed ? 'muted' : 'verdigris'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <EntityLink
                kind='entity'
                id={String(line.other_region_id)}
                showIcon
              >
                {line.other_region_name}
              </EntityLink>
              {line.severed && (
                <Badge size='sm' variant='warning'>
                  {line.severed_until_epoch !== null
                    ? `Cut until epoch ${line.severed_until_epoch}`
                    : 'Cut by scarred land'}
                </Badge>
              )}
            </div>
            <StatBar
              label='Strength'
              value={line.strength}
              max={PERCENT}
              tone='verdigris'
            />
          </div>
          <Button
            size='sm'
            variant='outline'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() =>
              line.severed ? restore.mutate(line.id) : sever.mutate(line.id)
            }
          >
            {line.severed ? <Link2 /> : <Scissors />}
            {line.severed ? 'Let it flow' : 'Cut it'}
          </Button>
        </li>
      ))}
    </ul>
  )
}

function regionGroups(ground: RegionEnvironment): AdjustGroup[] {
  return [
    {
      title: 'Climate',
      fields: [
        percentField('temperature', ground.temperature),
        percentField('rainfall', ground.rainfall),
        percentField('seasonality', ground.seasonality),
        percentField('magic_density', ground.magic_density),
      ],
    },
    {
      title: 'Soil, harvest and health',
      fields: [
        percentField('soil_fertility', ground.soil_fertility),
        percentField('soil_base', ground.soil_base),
        percentField('harvest_pct', ground.harvest_pct, HARVEST_MAX),
        percentField('erosion', ground.erosion),
        percentField('disease_load', ground.disease_load),
        percentField('defensibility', ground.defensibility),
        percentField('sacredness', ground.sacredness),
        percentField('derived_fertility', ground.derived_fertility ?? 0),
      ],
    },
    {
      title: 'Shape of the land',
      fields: [
        percentField('elevation_mean', ground.elevation_mean),
        percentField('roughness', ground.roughness),
        percentField('latitude', ground.latitude),
        percentField('moisture', ground.moisture),
        percentField('base_forest', ground.base_forest),
        percentField('forest_cover', ground.forest_cover),
        percentField('base_wetland', ground.base_wetland),
        percentField('wetland', ground.wetland),
      ],
    },
    {
      title: 'Land use',
      fields: Object.keys(LAND_USE).map((key) =>
        percentField(key, ground.land_use[key] ?? 0)
      ),
    },
    {
      title: 'Getting around',
      fields: Object.keys(MODES).map((mode) =>
        percentField(`passability.${mode}`, ground.passability[mode] ?? 0)
      ),
    },
    {
      title: 'Scars (0 heals)',
      fields: Object.entries(SCARS).map(([key, scar]) => ({
        key: `${SCAR_PREFIX}${key}`,
        label: scar.label,
        value: ground.scars[key] ?? 0,
        min: 0,
        max: PERCENT,
      })),
    },
    {
      title: 'Mineral seams (0 removes)',
      fields: Object.entries(MINERALS).map(([key, label]) => ({
        key: `${SEAM_PREFIX}${key}`,
        label,
        value: ground.mineral_layers[key] ?? 0,
        min: 0,
        max: PERCENT,
      })),
    },
  ]
}

function ChoiceRow({
  label,
  value,
  table,
  blocked,
  onPick,
}: {
  label: string
  value: string
  table: Record<string, string>
  blocked: string | null
  onPick: (value: string) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{label}</Label>
      <Select value={value} onValueChange={onPick} disabled={blocked !== null}>
        <SelectTrigger aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(table).map(([key, text]) => (
            <SelectItem key={key} value={key}>
              {text}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function RegionControls({
  regionId,
  ground,
}: {
  regionId: number
  ground: RegionEnvironment
}) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const run = ({ key, value }: Change) => {
    if (key.startsWith(SCAR_PREFIX))
      return unwrap(
        api.POST('/api/actions/environment:scar', {
          body: {
            region_id: regionId,
            kind: key.slice(SCAR_PREFIX.length) as ScarKind,
            depth: Number(value),
            lock: hold,
          },
        })
      )
    if (key.startsWith(SEAM_PREFIX))
      return unwrap(
        api.POST('/api/actions/environment:mineral', {
          body: {
            region_id: regionId,
            material: key.slice(SEAM_PREFIX.length) as MaterialKind,
            richness: Number(value),
            lock: hold,
          },
        })
      )
    return unwrap(
      api.POST('/api/actions/environment:set', {
        body: {
          region_id: regionId,
          field: key,
          value: typeof value === 'boolean' ? Number(value) : value,
          lock: hold,
        },
      })
    )
  }
  const choose = useGodAction({
    run,
    success: (_result, change: Change) => `${fieldLabel(change.key)} set`,
  })
  const release = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/environment:unlock', {
          body: { region_id: regionId, field },
        })
      ),
    success: (_result, field: string) =>
      `${fieldLabel(field)} follows the world again`,
  })
  const busy =
    reason() ?? (choose.isPending || release.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-4 rounded-lg border border-dashed bg-muted/20 p-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text weight='semibold'>Shape this land</Text>
          <Muted variant='caption'>
            Every value above can be set here. A held value stops following the
            world until you release it. Every change goes into the ledger and
            can be undone.
          </Muted>
        </div>
        <label className='flex shrink-0 items-center gap-2'>
          <Switch
            checked={hold}
            onCheckedChange={setHold}
            aria-label='Hold what I set'
          />
          <Text as='span'>Hold what I set</Text>
        </label>
      </div>
      {ground.locked.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Lock aria-hidden='true' className='size-icon-xs text-primary' />
          {ground.locked.map((key) => (
            <Button
              key={key}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(key)}
            >
              <Unlock />
              {`Release ${fieldLabel(key).toLowerCase()}`}
            </Button>
          ))}
        </div>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/env:grid-cols-2 @3xl/env:grid-cols-4'>
        {REGION_CHOICES.map((item) => (
          <ChoiceRow
            key={item.key}
            label={fieldLabel(item.key)}
            value={String(ground[item.key])}
            table={item.table}
            blocked={busy}
            onPick={(value) => choose.mutate({ key: item.key, value })}
          />
        ))}
      </div>
      <AdjustStats
        id={`region-${regionId}-environment`}
        groups={regionGroups(ground)}
        note='Scars heal and seams vanish at 0. Fertility itself is a stat: set or pin it in the Stats and Mechanics sections.'
        run={run}
      />
    </div>
  )
}

function RegionEnvironmentSection({ regionId }: { regionId: number }) {
  const { reason } = useGodGate()
  const view = useQuery({
    queryKey: environmentKey('region', regionId),
    queryFn: () =>
      unwrap(
        api.GET('/api/regions/{region_id}/environment', {
          params: { path: { region_id: regionId } },
        })
      ),
    retry: false,
  })
  const ground = view.data
  const seamNames = useSeamNames(ground?.world_id ?? 0)
  return (
    <Section
      id='section-environment'
      title='Environment'
      description='The land itself: what grows, how the seasons and weather fall, how armies and travellers cross it, and what it remembers.'
      icon={Mountain}
    >
      {!ground ? (
        <EmptyState
          icon={Mountain}
          title='Not surveyed yet'
          description='The next epoch surveys this region from the map.'
        />
      ) : (
        <div className='@container/env flex min-w-0 flex-col gap-4'>
          <LandHero ground={ground} />
          <Vitals ground={ground} />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/env:grid-cols-2'>
            <Card title='The land' icon={Trees}>
              <StatBar
                label='Forest cover'
                value={ground.forest_cover}
                max={ground.base_forest || PERCENT}
                icon={Trees}
                tone='success'
              />
              <StatBar
                label='Wetland'
                value={ground.wetland}
                max={PERCENT}
                icon={Droplets}
                tone='info'
              />
              <StatBar
                label='Soil fertility'
                value={ground.soil_fertility}
                max={ground.soil_base || PERCENT}
                icon={Sprout}
                tone='success'
              />
              <StatBar
                label='Erosion'
                value={ground.erosion}
                max={PERCENT}
                icon={Mountain}
                tone='warning'
              />
            </Card>
            <Card title='Land use' icon={Gauge}>
              {Object.entries(LAND_USE).map(([key, use]) => (
                <StatBar
                  key={key}
                  label={use.label}
                  value={ground.land_use[key] ?? 0}
                  max={PERCENT}
                  icon={use.icon}
                  tone='warning'
                />
              ))}
            </Card>
            <Card title='Getting around' icon={Waypoints}>
              {Object.entries(MODES).map(([mode, item]) => (
                <StatBar
                  key={mode}
                  label={item.label}
                  value={ground.passability[mode] ?? 0}
                  max={PERCENT}
                  icon={item.icon}
                  tone='info'
                />
              ))}
            </Card>
            <Card title='Mineral seams' icon={Gem}>
              {Object.keys(ground.mineral_layers).length === 0 ? (
                <Muted>No seam is known in this land.</Muted>
              ) : (
                Object.entries(ground.mineral_layers)
                  .sort(([, left], [, right]) => right - left)
                  .map(([key, richness]) => (
                    <StatBar
                      key={key}
                      label={seamLabel(key, seamNames)}
                      value={richness}
                      max={PERCENT}
                      icon={Gem}
                      tone='verdigris'
                    />
                  ))
              )}
            </Card>
          </div>
          <Card title="This epoch's weather" icon={CloudSun}>
            <div className='grid min-w-0 grid-cols-1 gap-2 @md/env:grid-cols-2 @xl/env:grid-cols-3'>
              {ground.forecast.map((item) => (
                <WeatherTile key={item.season_id ?? 'all'} item={item} />
              ))}
            </div>
          </Card>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/env:grid-cols-2'>
            <Card title='Scars' icon={Shield}>
              {Object.keys(ground.scars).length === 0 ? (
                <Muted>The land is unscarred.</Muted>
              ) : (
                Object.entries(ground.scars).map(([key, depth]) => {
                  const scar = named(SCARS, key)
                  return (
                    <StatBar
                      key={key}
                      label={scar.label}
                      value={depth}
                      max={PERCENT}
                      icon={scar.icon}
                      tone='destructive'
                    />
                  )
                })
              )}
            </Card>
            <Card title='Ley lines' icon={Waypoints}>
              <LeyLines ground={ground} blocked={reason()} />
              <ForgeLey regionId={regionId} ground={ground} />
            </Card>
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/env:grid-cols-2'>
            <Card title='Weather held over this land' icon={CloudSun}>
              <HoldWeather regionId={regionId} ground={ground} />
            </Card>
            <Card title='Years remembered' icon={Scroll}>
              <NotableYears regionId={regionId} ground={ground} />
            </Card>
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/env:grid-cols-2'>
            <Card title='Seams of any material' icon={Gem}>
              <SeamForge regionId={regionId} ground={ground} />
            </Card>
            <Card title='Biomes of the land' icon={Mountain}>
              <BiomeMix regionId={regionId} ground={ground} />
            </Card>
          </div>
          <RegionControls regionId={regionId} ground={ground} />
        </div>
      )}
    </Section>
  )
}

function PlaceEnvironmentSection({ placeId }: { placeId: number }) {
  const { reason } = useGodGate()
  const view = useQuery({
    queryKey: environmentKey('place', placeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/places/{place_id}/environment', {
          params: { path: { place_id: placeId } },
        })
      ),
    retry: false,
  })
  const run = ({ key, value }: Change) =>
    unwrap(
      api.POST('/api/actions/environment:place', {
        body: { place_id: placeId, field: key, value },
      })
    )
  const set = useGodAction({
    run,
    success: (_result, change: Change) =>
      `${change.key === 'nexus' ? 'Ley nexus' : fieldLabel(change.key)} set`,
  })
  const ground: PlaceEnvironment | undefined = view.data
  const busy = reason() ?? (set.isPending ? WORKING : null)
  const terrain = ground?.terrain ? named(TERRAIN, ground.terrain) : null
  return (
    <Section
      id='section-environment'
      title='Environment'
      description='The ground of this place: its own terrain, cover, water and height, and whether it holds a pass or a ley nexus.'
      icon={Mountain}
    >
      {!ground ? (
        <EmptyState
          icon={Mountain}
          title='Not surveyed yet'
          description='The next epoch surveys this place.'
        />
      ) : (
        <div className='@container/env flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/env:grid-cols-2 @3xl/env:grid-cols-4'>
            <KpiTile
              label='Terrain'
              value={terrain?.label ?? 'As its region'}
              icon={terrain?.icon ?? Mountain}
              tone={terrain?.tone ?? 'gold'}
            />
            <KpiTile
              label='Cover'
              value={plain(COVER, ground.cover)}
              icon={Trees}
              tone='success'
            />
            <KpiTile
              label='Water'
              value={plain(WATER, ground.water_source)}
              icon={Droplets}
              tone='info'
            />
            <KpiTile
              label='Height advantage'
              value={ground.height_advantage}
              icon={Mountain}
              tone='warning'
              hint='Defenders on high ground fight harder'
              meter={{
                value: ground.height_advantage,
                max: PERCENT,
                label: 'Height advantage',
              }}
            />
            <KpiTile
              label='Soil fertility'
              value={ground.soil_fertility}
              icon={Sprout}
              tone='success'
              meter={{
                value: ground.soil_fertility,
                max: PERCENT,
                label: 'Soil fertility',
              }}
            />
            <KpiTile
              label='Chokepoint'
              value={ground.chokepoint ? 'Yes' : 'No'}
              icon={Shield}
              tone={ground.chokepoint ? 'gold' : 'muted'}
              hint='Defenders holding a chokepoint fight far harder'
            />
            <KpiTile
              label='Ley nexus'
              value={ground.nexus ? 'Yes' : 'No'}
              icon={Waypoints}
              tone={ground.nexus ? 'verdigris' : 'muted'}
              hint='Where ley lines meet; works here gain power fastest'
            />
          </div>
          <div className='flex min-w-0 flex-col gap-4 rounded-lg border border-dashed bg-muted/20 p-3'>
            <div className='flex min-w-0 flex-col gap-0.5'>
              <Text weight='semibold'>Shape this place</Text>
              <Muted variant='caption'>
                Every value above can be set here; every change goes into the
                ledger.
              </Muted>
            </div>
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/env:grid-cols-2 @3xl/env:grid-cols-5'>
              {PLACE_CHOICES.map((item) => (
                <ChoiceRow
                  key={item.key}
                  label={item.label}
                  value={ground[item.key] ?? 'inherit'}
                  table={item.table}
                  blocked={busy}
                  onPick={(value) => set.mutate({ key: item.key, value })}
                />
              ))}
              <ChoiceRow
                label='Chokepoint'
                value={ground.chokepoint ? 'yes' : 'no'}
                table={YES_NO}
                blocked={busy}
                onPick={(value) =>
                  set.mutate({ key: 'chokepoint', value: value === 'yes' })
                }
              />
              <ChoiceRow
                label='Ley nexus'
                value={ground.nexus ? 'yes' : 'no'}
                table={YES_NO}
                blocked={busy}
                onPick={(value) =>
                  set.mutate({ key: 'nexus', value: value === 'yes' })
                }
              />
            </div>
            <AdjustStats
              id={`place-${placeId}-environment`}
              groups={[
                {
                  title: 'Ground',
                  fields: [
                    percentField('height_advantage', ground.height_advantage),
                    percentField('soil_fertility', ground.soil_fertility),
                  ],
                },
              ]}
              run={run}
            />
          </div>
        </div>
      )}
    </Section>
  )
}

export function EntityEnvironment({
  entityId,
  entityType,
}: {
  entityId: number
  entityType: string
}) {
  if (entityType === 'region')
    return (
      <>
        <RegionEnvironmentSection regionId={entityId} />
        <RegionTerrainSection regionId={entityId} />
      </>
    )
  if (entityType === 'place')
    return <PlaceEnvironmentSection placeId={entityId} />
  return null
}
