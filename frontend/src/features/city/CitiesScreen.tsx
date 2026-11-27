import { useCallback, useEffect, useMemo } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { ArrowDownToLine, BookOpen, Building2, Mountain } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { EmptyState, PageHeader } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { useGlobalWorld } from '@/components/layout/worldFilter'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useEntitiesOfType, useWorldState } from '@/features/entity/api/queries'
import { type EntitySummary } from '@/features/entity/api/types'
import { STRATUM } from '@/features/entity/environment/geologyLabels'
import { StratumSwatch } from '@/features/map/SwatchMarker'
import { STRATUM_LOOK } from '@/features/map/deepLooks'
import { CityPlane } from './CityPlane'
import { LandPlane } from './LandPlane'
import { useBelow } from './api'
import { type CitiesSearch, type CityView } from './citiesSearch'
import { CITY_ICON } from './labels'

const CANON = 'canon'

function ranked(
  entities: EntitySummary[],
  type: string,
  world: number | null
): EntitySummary[] {
  return entities
    .filter(
      (entity) =>
        entity.entity_type === type &&
        (world === null || entity.world_id === world)
    )
    .sort(
      (left, right) =>
        (right.importance ?? 0) - (left.importance ?? 0) ||
        left.name.localeCompare(right.name)
    )
}

export function CitiesScreen() {
  const search = useSearch({ from: '/_app/cities' })
  const navigate = useNavigate({ from: '/cities' })
  const change = useCallback(
    (patch: CitiesSearch) =>
      void navigate({
        search: (previous) => ({ ...previous, ...patch }),
        replace: true,
      }),
    [navigate]
  )
  return <CitiesView search={search} onSearch={change} />
}

export function CitiesView({
  search,
  onSearch,
}: {
  search: CitiesSearch
  onSearch: (patch: CitiesSearch) => void
}) {
  const settlements = useEntitiesOfType(CANON, 'settlement', true)
  const lands = useEntitiesOfType(CANON, 'region', true)
  const failed = settlements.error ?? lands.error
  const below = useBelow()
  const state = useWorldState()
  const world = useGlobalWorld()
  const entryStack = useEntryStack()
  const view: CityView = search.view ?? 'city'
  const towns = useMemo(
    () => ranked(settlements.data ?? [], 'settlement', world),
    [settlements.data, world]
  )
  const regions = useMemo(
    () => ranked(lands.data ?? [], 'region', world),
    [lands.data, world]
  )
  const town = towns.find((item) => item.id === search.town) ?? towns[0]
  const region =
    regions.find((item) => item.id === search.region) ??
    regions.find((item) => item.id === town?.location_id) ??
    regions[0]
  useEffect(() => {
    if (search.town === undefined && town) onSearch({ town: town.id })
  }, [search.town, town, onSearch])
  const blocked = state.data?.read_only ? READ_ONLY_REASON : null
  const list = view === 'city' ? towns : regions
  const current = view === 'city' ? town : region
  const beneath = new Map((below.data ?? []).map((row) => [row.region_id, row]))
  const options = list.map((item) => {
    const deep = item.stratum
    const under = beneath.get(item.id)
    return {
      value: String(item.id),
      label: item.name,
      hint: deep
        ? STRATUM[deep].label
        : under
          ? `${plural(under.strata.length, 'depth', 'depths')} below${under.towns > 0 ? `, ${plural(under.towns, 'town', 'towns')}` : ''}`
          : (item.subtype ?? undefined),
      adornment: deep ? (
        <StratumSwatch
          fill={STRATUM_LOOK[deep].fill}
          glow={STRATUM_LOOK[deep].glow}
        />
      ) : under ? (
        <ArrowDownToLine aria-hidden='true' className='text-primary' />
      ) : undefined,
    }
  })
  const deepTowns = towns.filter((item) => item.stratum).length
  return (
    <div data-surface='CitiesScreen' className='flex min-w-0 flex-1 flex-col'>
      <div className='flex min-w-0 flex-col gap-4 border-b p-4 md:px-6'>
        <PageHeader
          title='Cities and lands'
          icon={CITY_ICON}
          description='Every town on its hexes and every land on its tiles, drawn from what the engine reckons: zones, districts, buildings at their stage, homes, walls, water, cover and deposits. Rule any of it from the scene.'
          meta={
            <>
              <Badge variant='outline'>{`${plural(towns.length, 'town', 'towns')}`}</Badge>
              <Badge variant='outline'>{`${plural(regions.length, 'land', 'lands')}`}</Badge>
              {deepTowns > 0 && (
                <Badge variant='outline'>
                  <ArrowDownToLine />
                  {`${plural(deepTowns, 'town', 'towns')} below the surface`}
                </Badge>
              )}
            </>
          }
        />
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <ToggleGroup
            type='single'
            size='sm'
            variant='outline'
            value={view}
            aria-label='What to draw'
            onValueChange={(value) =>
              value && onSearch({ view: value as CityView })
            }
          >
            <ToggleGroupItem value='city'>
              <Building2 />
              City
            </ToggleGroupItem>
            <ToggleGroupItem value='land'>
              <Mountain />
              Land
            </ToggleGroupItem>
          </ToggleGroup>
          <div className='w-full max-w-sm min-w-0'>
            <RecordCombobox
              size='sm'
              options={options}
              value={current ? String(current.id) : null}
              placeholder={view === 'city' ? 'Choose a town' : 'Choose a land'}
              searchPlaceholder={
                view === 'city' ? 'Find a town…' : 'Find a land…'
              }
              emptyText={view === 'city' ? 'No such town' : 'No such land'}
              disabled={list.length === 0}
              disabledReason={
                list.length === 0
                  ? view === 'city'
                    ? 'No town stands in this world yet'
                    : 'No land is surveyed in this world yet'
                  : undefined
              }
              onChange={(value) =>
                value &&
                onSearch(
                  view === 'city'
                    ? { town: Number(value) }
                    : { region: Number(value) }
                )
              }
            />
          </div>
          <Button
            size='sm'
            variant='outline'
            disabled={!current}
            disabledReason={current ? undefined : 'Choose one first'}
            onClick={() =>
              current &&
              entryStack.open({ kind: 'entity', id: String(current.id) })
            }
          >
            <BookOpen />
            Open its record
          </Button>
        </div>
      </div>
      {settlements.isPending || lands.isPending ? (
        <div className='p-4 md:p-6'>
          <Skeleton className='h-scene w-full lg:h-scene-lg' />
        </div>
      ) : failed ? (
        <div className='p-4 md:p-6'>
          <EmptyState
            icon={CITY_ICON}
            title='The towns could not be read'
            description={failed.message}
          />
        </div>
      ) : !current ? (
        <div className='p-4 md:p-6'>
          <EmptyState
            icon={CITY_ICON}
            title={
              view === 'city' ? 'No town stands yet' : 'No land is known yet'
            }
            description='Towns and lands appear here as the world raises them.'
          />
        </div>
      ) : view === 'city' ? (
        <CityPlane
          key={current.id}
          settlementId={current.id}
          blocked={blocked}
        />
      ) : (
        <LandPlane key={current.id} regionId={current.id} blocked={blocked} />
      )}
    </div>
  )
}
