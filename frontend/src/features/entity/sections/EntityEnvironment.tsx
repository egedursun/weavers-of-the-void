import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Lock, Mountain, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
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
import { Switch } from '@/components/ui/switch'
import { Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { loreKeys } from '../api/keys'
import { useLoreMutation } from '../api/mutations'

type RegionEnvironment = components['schemas']['RegionEnvironmentView']
type PlaceEnvironment = components['schemas']['PlaceEnvironmentView']

const REGION_FIELDS = [
  'dominant_terrain',
  'soil',
  'river_class',
  'coast_kind',
  'temperature',
  'rainfall',
  'soil_fertility',
  'soil_base',
  'forest_cover',
  'wetland',
  'disease_load',
  'defensibility',
  'elevation_mean',
  'roughness',
  'latitude',
  'moisture',
  'cleared',
  'farmed',
  'grazed',
  'mined',
  'built',
] as const
const PLACE_FIELDS = [
  'terrain',
  'cover',
  'water_source',
  'height_advantage',
  'soil_fertility',
  'chokepoint',
] as const
const SCARS = [
  'battlefield',
  'plague_ground',
  'salted_earth',
  'burned',
  'crater',
  'haunted',
  'blighted',
  'leak_wound',
] as const
const MATERIALS = [
  'stone',
  'flint',
  'obsidian',
  'copper',
  'tin',
  'iron',
  'silver',
  'gold',
  'crystal',
  'salt',
  'amber',
  'lead',
  'sulfur',
  'clay',
  'gems',
  'star_metal',
  'void_glass',
] as const
const BUSY_REASON = 'Another change is being applied.'
const ENTER_VALUE = 'Enter a value first.'

function words(value: string): string {
  return value.replaceAll('_', ' ')
}

function valueOf(raw: string): number | string | boolean {
  if (raw === 'true' || raw === 'false') return raw === 'true'
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) && String(parsed) === raw.trim() ? parsed : raw
}

function environmentKey(kind: 'region' | 'place', id: number) {
  return [...loreKeys.entity(id), 'environment', kind] as const
}

function Facts({ items }: { items: [string, string | number][] }) {
  return (
    <div className='grid min-w-0 grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3'>
      {items.map(([label, value]) => (
        <Text key={label}>
          <Muted as='span'>{label}: </Muted>
          {typeof value === 'string' ? words(value) : value}
        </Text>
      ))}
    </div>
  )
}

function RegionFacts({ ground }: { ground: RegionEnvironment }) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Facts
        items={[
          ['Terrain', ground.dominant_terrain],
          ['Soil', ground.soil],
          ['Climate', `${ground.temperature_band} (${ground.temperature})`],
          ['Rainfall', ground.rainfall],
          ['Seasonality', ground.seasonality],
          ['River', ground.river_class],
          ['Coast', ground.coast_kind],
          ['Fertility', ground.fertility ?? '—'],
          [
            'Soil fertility',
            `${ground.soil_fertility} of ${ground.soil_base} natural`,
          ],
          ['Forest', `${ground.forest_cover} of ${ground.base_forest}`],
          ['Wetland', ground.wetland],
          ['Disease load', ground.disease_load],
          ['Magic density', ground.magic_density],
          ['Defensibility', ground.defensibility],
          ['Erosion', ground.erosion],
          ['Last harvest', `${ground.harvest_pct}%`],
        ]}
      />
      <div className='flex min-w-0 flex-col gap-1'>
        <Label variant='overline'>Passability</Label>
        <Facts items={Object.entries(ground.passability)} />
      </div>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label variant='overline'>Land use</Label>
        <Facts items={Object.entries(ground.land_use)} />
      </div>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label variant='overline'>Mineral seams</Label>
        {Object.keys(ground.mineral_layers).length === 0 ? (
          <Muted>No seams known.</Muted>
        ) : (
          <Facts items={Object.entries(ground.mineral_layers)} />
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label variant='overline'>Scars</Label>
        {Object.keys(ground.scars).length === 0 && <Muted>Unscarred.</Muted>}
        {Object.entries(ground.scars).map(([kind, depth]) => (
          <Badge key={kind} size='sm' variant='warning'>
            {words(kind)} {depth}
          </Badge>
        ))}
      </div>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label variant='overline'>Weather this epoch</Label>
        {ground.forecast.map((item) => (
          <Text key={item.season_id ?? 'all'}>
            {item.season_name ?? 'All year'}: {item.label}
          </Text>
        ))}
      </div>
    </div>
  )
}

function LeyLines({
  regionId,
  ground,
  readOnlyReason,
}: {
  regionId: number
  ground: RegionEnvironment
  readOnlyReason: string | null
}) {
  const invalidate = [environmentKey('region', regionId)]
  const sever = useLoreMutation({
    run: (lineId: number) =>
      unwrap(api.POST('/api/actions/ley:sever', { body: { line_id: lineId } })),
    invalidate,
  })
  const restore = useLoreMutation({
    run: (lineId: number) =>
      unwrap(
        api.POST('/api/actions/ley:restore', { body: { line_id: lineId } })
      ),
    invalidate,
  })
  const blocked =
    readOnlyReason ??
    (sever.isPending || restore.isPending ? BUSY_REASON : undefined)
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label variant='overline'>Ley lines</Label>
      {ground.ley_lines.length === 0 && <Muted>No ley line runs here.</Muted>}
      {ground.ley_lines.map((line) => (
        <div
          key={line.id}
          className='flex min-w-0 flex-wrap items-center gap-2'
        >
          <Text>
            #{line.id} to {line.other_region_name}, strength {line.strength}
          </Text>
          {line.severed && (
            <Badge size='sm' variant='warning'>
              cut
              {line.severed_until_epoch !== null &&
                ` until epoch ${line.severed_until_epoch}`}
            </Badge>
          )}
          <Button
            size='sm'
            variant='outline'
            disabled={blocked !== undefined}
            disabledReason={blocked}
            onClick={() =>
              line.severed ? restore.mutate(line.id) : sever.mutate(line.id)
            }
          >
            {line.severed ? 'Let it flow' : 'Cut it'}
          </Button>
        </div>
      ))}
    </div>
  )
}

function RegionLevers({
  regionId,
  ground,
  readOnlyReason,
}: {
  regionId: number
  ground: RegionEnvironment
  readOnlyReason: string | null
}) {
  const invalidate = [environmentKey('region', regionId)]
  const [field, setField] = useState<string>(REGION_FIELDS[0])
  const [value, setValue] = useState('')
  const [lock, setLock] = useState(true)
  const [scar, setScar] = useState<(typeof SCARS)[number]>(SCARS[0])
  const [depth, setDepth] = useState('')
  const [material, setMaterial] = useState<(typeof MATERIALS)[number]>(
    MATERIALS[0]
  )
  const [richness, setRichness] = useState('')
  const set = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:set', {
          body: {
            region_id: regionId,
            field,
            value: valueOf(value) as number | string,
            lock,
          },
        })
      ),
    invalidate,
  })
  const unlock = useLoreMutation({
    run: (key: string) =>
      unwrap(
        api.POST('/api/actions/environment:unlock', {
          body: { region_id: regionId, field: key },
        })
      ),
    invalidate,
  })
  const scarIt = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:scar', {
          body: {
            region_id: regionId,
            kind: scar,
            depth: Number.parseInt(depth, 10),
          },
        })
      ),
    invalidate,
  })
  const seam = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:mineral', {
          body: {
            region_id: regionId,
            material,
            richness: Number.parseInt(richness, 10),
          },
        })
      ),
    invalidate,
  })
  const busy =
    set.isPending || unlock.isPending || scarIt.isPending || seam.isPending
  const blocked = readOnlyReason ?? (busy ? BUSY_REASON : undefined)
  const needs = (missing: boolean) =>
    blocked ?? (missing ? ENTER_VALUE : undefined)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {ground.locked.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {ground.locked.map((key) => (
            <Button
              key={key}
              size='sm'
              variant='outline'
              disabled={needs(false) !== undefined}
              disabledReason={needs(false)}
              onClick={() => unlock.mutate(key)}
            >
              <Unlock />
              Release {words(key)}
            </Button>
          ))}
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select value={field} onValueChange={setField}>
          <SelectTrigger aria-label='Environment field'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {REGION_FIELDS.map((item) => (
              <SelectItem key={item} value={item}>
                {words(item)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label='Value'
          placeholder='Value'
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <Switch
          aria-label='Hold the value'
          checked={lock}
          onCheckedChange={setLock}
        />
        <Muted>hold</Muted>
        <Button
          size='sm'
          disabled={needs(value === '') !== undefined}
          disabledReason={needs(value === '')}
          onClick={() => set.mutate()}
        >
          <Lock />
          Set
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select
          value={scar}
          onValueChange={(item) => setScar(item as (typeof SCARS)[number])}
        >
          <SelectTrigger aria-label='Scar'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SCARS.map((item) => (
              <SelectItem key={item} value={item}>
                {words(item)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label='Scar depth'
          inputMode='numeric'
          placeholder='Depth (0 heals)'
          value={depth}
          onChange={(event) => setDepth(event.target.value)}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={needs(depth === '') !== undefined}
          disabledReason={needs(depth === '')}
          onClick={() => scarIt.mutate()}
        >
          Scar or heal
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select
          value={material}
          onValueChange={(item) =>
            setMaterial(item as (typeof MATERIALS)[number])
          }
        >
          <SelectTrigger aria-label='Mineral'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MATERIALS.map((item) => (
              <SelectItem key={item} value={item}>
                {words(item)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label='Richness'
          inputMode='numeric'
          placeholder='Richness (0 removes)'
          value={richness}
          onChange={(event) => setRichness(event.target.value)}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={needs(richness === '') !== undefined}
          disabledReason={needs(richness === '')}
          onClick={() => seam.mutate()}
        >
          Set seam
        </Button>
      </div>
    </div>
  )
}

function RegionEnvironmentSection({
  regionId,
  readOnlyReason,
}: {
  regionId: number
  readOnlyReason: string | null
}) {
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
  return (
    <Section
      id='section-environment'
      title='Environment'
      description='Terrain, soil, climate, water, land use, seams, scars and this epoch’s weather.'
      icon={Mountain}
    >
      {view.data ? (
        <div className='flex min-w-0 flex-col gap-4'>
          <RegionFacts ground={view.data} />
          <LeyLines
            regionId={regionId}
            ground={view.data}
            readOnlyReason={readOnlyReason}
          />
          <RegionLevers
            regionId={regionId}
            ground={view.data}
            readOnlyReason={readOnlyReason}
          />
        </div>
      ) : (
        <Muted>Not surveyed yet: the next epoch surveys it.</Muted>
      )}
      {readOnlyReason && <Muted variant='caption'>{readOnlyReason}</Muted>}
    </Section>
  )
}

function PlaceEnvironmentSection({
  placeId,
  readOnlyReason,
}: {
  placeId: number
  readOnlyReason: string | null
}) {
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
  const [field, setField] = useState<string>(PLACE_FIELDS[0])
  const [value, setValue] = useState('')
  const set = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:place', {
          body: { place_id: placeId, field, value: valueOf(value) },
        })
      ),
    invalidate: [environmentKey('place', placeId)],
  })
  const ground: PlaceEnvironment | undefined = view.data
  const blocked = readOnlyReason ?? (set.isPending ? BUSY_REASON : undefined)
  const reason = blocked ?? (value === '' ? ENTER_VALUE : undefined)
  return (
    <Section
      id='section-environment'
      title='Environment'
      description='The ground of this place: its own terrain, cover, water, height and whether it is a chokepoint.'
      icon={Mountain}
    >
      {ground ? (
        <Facts
          items={[
            ['Terrain', ground.terrain ?? 'as its region'],
            ['Cover', ground.cover],
            ['Water', ground.water_source],
            ['Height advantage', ground.height_advantage],
            ['Chokepoint', ground.chokepoint ? 'yes' : 'no'],
            ['Ley nexus', ground.nexus ? 'yes' : 'no'],
            ['Soil fertility', ground.soil_fertility],
          ]}
        />
      ) : (
        <Muted>Not surveyed yet: the next epoch surveys it.</Muted>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Select value={field} onValueChange={setField}>
          <SelectTrigger aria-label='Place field'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PLACE_FIELDS.map((item) => (
              <SelectItem key={item} value={item}>
                {words(item)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label='Value'
          placeholder='Value'
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <Button
          size='sm'
          disabled={reason !== undefined}
          disabledReason={reason}
          onClick={() => set.mutate()}
        >
          Set
        </Button>
      </div>
      {readOnlyReason && <Muted variant='caption'>{readOnlyReason}</Muted>}
    </Section>
  )
}

export function EntityEnvironment({
  entityId,
  entityType,
  readOnlyReason,
}: {
  entityId: number
  entityType: string
  readOnlyReason: string | null
}) {
  if (entityType === 'region')
    return (
      <RegionEnvironmentSection
        regionId={entityId}
        readOnlyReason={readOnlyReason}
      />
    )
  if (entityType === 'place')
    return (
      <PlaceEnvironmentSection
        placeId={entityId}
        readOnlyReason={readOnlyReason}
      />
    )
  return null
}
