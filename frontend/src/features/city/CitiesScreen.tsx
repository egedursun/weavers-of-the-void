import { useCallback, useEffect, useMemo } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { BookOpen, Building2, Mountain } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { EmptyState, PageHeader } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { useGlobalWorld } from '@/components/layout/worldFilter'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useAllEntities, useWorldState } from '@/features/entity/api/queries'
import { type EntitySummary } from '@/features/entity/api/types'
import { CityPlane } from './CityPlane'
import { LandPlane } from './LandPlane'
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
  const entities = useAllEntities(CANON, true)
  const state = useWorldState()
  const world = useGlobalWorld()
  const drawers = useDrawerStack()
  const view: CityView = search.view ?? 'city'
  const towns = useMemo(
    () => ranked(entities.data ?? [], 'settlement', world),
    [entities.data, world]
  )
  const regions = useMemo(
    () => ranked(entities.data ?? [], 'region', world),
    [entities.data, world]
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
  const options = list.map((item) => ({
    value: String(item.id),
    label: item.name,
    hint: item.subtype ?? undefined,
  }))
  return (
    <div data-surface='CitiesScreen' className='flex min-w-0 flex-1 flex-col'>
      <div className='flex min-w-0 flex-col gap-4 border-b p-4 md:px-6'>
        <PageHeader
          title='Cities and lands'
          icon={CITY_ICON}
          description='Every town on its hexes and every land on its tiles, drawn from what the engine reckons: zones, districts, buildings at their stage, homes, walls, water, cover and deposits. Rule any of it from the scene.'
          meta={
            <>
              <Badge variant='outline'>{`${towns.length} towns`}</Badge>
              <Badge variant='outline'>{`${regions.length} lands`}</Badge>
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
              drawers.open({ kind: 'entity', id: String(current.id) })
            }
          >
            <BookOpen />
            Open its record
          </Button>
        </div>
      </div>
      {entities.isPending ? (
        <div className='p-4 md:p-6'>
          <Skeleton className='h-scene w-full lg:h-scene-lg' />
        </div>
      ) : entities.isError ? (
        <div className='p-4 md:p-6'>
          <EmptyState
            icon={CITY_ICON}
            title='The towns could not be read'
            description={entities.error.message}
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
