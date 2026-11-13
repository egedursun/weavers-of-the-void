import { Suspense, lazy, useCallback, useRef, useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import {
  CloudFog,
  Crown,
  Eye,
  Gem,
  History,
  Layers,
  Maximize2,
  Orbit,
  Plus,
  RefreshCw,
  Skull,
  Sparkles,
  Workflow,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, KpiTile, PagedList, PageHeader } from '@/components/domain'
import { Text } from '@/components/typography'
import { useCosmos } from '@/features/cosmos/api'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import { HeavensPhysicsPanel } from '@/features/physics/HeavensPhysicsPanel'
import { ApocalypseVariantPanel } from './ApocalypseVariantPanel'
import { BeingsPanel } from './BeingsPanel'
import { EventsPanel } from './EventsPanel'
import { PhenomenaPanel } from './PhenomenaPanel'
import { RiftsPanel } from './RiftsPanel'
import { ScaleNavigator } from './ScaleNavigator'
import { SelectedScale } from './SelectedScale'
import {
  type CosmographyCatalog,
  useCosmography,
  useCosmographyCatalog,
} from './api'
import {
  CreateClusterStudio,
  CreateDimensionStudio,
  CreateGalaxyStudio,
} from './create/CreateStudio'
import {
  type HeavensSearch,
  type HeavensTab,
  type ScaleKind,
} from './heavensSearch'
import { type Ladder, ladderOf } from './ladder'
import { GalaxyThumb } from './visual/GalaxyThumb'
import { type ScalePick } from './visual/UniverseScene3D'
import { DIMENSION_TOKEN } from './visual/galaxyForm'
import { cssColor } from './visual/palette'

const UniverseScene3D = lazy(() => import('./visual/UniverseScene3D'))
const OPEN_RIFTS = new Set(['opening', 'open', 'closing'])

function StillUniverse({
  ladder,
  catalog,
  onPick,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog
  onPick: (pick: ScalePick) => void
}) {
  return (
    <div className='grid h-full min-w-0 auto-rows-min grid-cols-2 gap-3 overflow-y-auto p-4 sm:grid-cols-3'>
      {ladder.data.galaxies.map((galaxy) => (
        <Button
          key={galaxy.id}
          variant='ghost'
          size='card'
          onClick={() => onPick({ kind: 'galaxy', id: galaxy.id })}
        >
          <GalaxyThumb
            galaxy={galaxy}
            shape={catalog.shape}
            label={galaxy.name}
            points={2400}
            className='aspect-square w-full'
          />
          <Text as='span' variant='caption' tone='inherit' truncate>
            {galaxy.name}
          </Text>
        </Button>
      ))}
    </div>
  )
}

function Legend({
  ladder,
  selectedId,
  onPick,
}: {
  ladder: Ladder
  selectedId: number | null
  onPick: (id: number) => void
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <PagedList
        items={ladder.data.dimensions}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap items-center gap-1'
        itemKey={(dimension) => dimension.id}
      >
        {(dimension) => (
          <Button
            key={dimension.id}
            variant={dimension.id === selectedId ? 'secondary' : 'ghost'}
            size='sm'
            aria-pressed={dimension.id === selectedId}
            title={`Fly to ${dimension.name}`}
            onClick={() => onPick(dimension.id)}
          >
            <svg
              aria-hidden='true'
              viewBox='0 0 10 10'
              className='size-icon-xs'
            >
              <circle
                cx='5'
                cy='5'
                r='4'
                fill={cssColor(DIMENSION_TOKEN[dimension.dimension_kind])}
              />
            </svg>
            <Text as='span' variant='caption' tone='inherit'>
              {dimension.name}
            </Text>
          </Button>
        )}
      </PagedList>
      <div className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1'>
        <Text as='span' variant='caption' tone='inherit' className='opacity-70'>
          Layers: dimensions with clusters of their own · orbs on the dashed
          ring: dimensions that hold none · dashed arcs: routes between galaxies
          · beams: open rifts between dimensions
        </Text>
      </div>
    </div>
  )
}

export function HeavensScreen() {
  const search = useSearch({ from: '/_app/heavens' })
  const navigate = useNavigate({ from: '/heavens' })
  const change = useCallback(
    (patch: HeavensSearch) =>
      void navigate({
        search: (previous) => ({ ...previous, ...patch }),
        replace: true,
      }),
    [navigate]
  )
  return <HeavensView search={search} onSearch={change} />
}

export function HeavensView({
  search,
  onSearch,
}: {
  search: HeavensSearch
  onSearch: (patch: HeavensSearch) => void
}) {
  const view = useCosmography()
  const catalog = useCosmographyCatalog()
  const cosmos = useCosmos()
  const select = useCallback(
    (kind: ScaleKind | undefined, id: number | undefined) =>
      onSearch({ layer: kind, node: id }),
    [onSearch]
  )
  const setTab = (tab: HeavensTab) => onSearch({ pane: tab })
  const [overview, setOverview] = useState(0)
  const showWhole = () => {
    select(undefined, undefined)
    setOverview((count) => count + 1)
  }
  const panes = useRef<HTMLDivElement>(null)
  const openStudio = () => {
    setTab('create')
    requestAnimationFrame(() => {
      panes.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      panes.current
        ?.querySelector<HTMLElement>(
          '[role=tabpanel] [role=radio], [role=tabpanel] input'
        )
        ?.focus({ preventScroll: true })
    })
  }
  const pick = useCallback(
    (next: ScalePick) => select(next?.kind, next?.id),
    [select]
  )
  if (view.isError)
    return (
      <div className='p-4 md:p-6'>
        <EmptyState
          icon={Layers}
          title='The heavens could not be read'
          description={view.error.message}
          action={
            <Button variant='outline' onClick={() => void view.refetch()}>
              <RefreshCw />
              Try again
            </Button>
          }
        />
      </div>
    )
  if (view.isPending || !catalog.data)
    return (
      <div className='flex flex-col gap-4 p-4 md:p-6'>
        <Skeleton className='h-control-lg w-1/3' />
        <Skeleton className='h-scene-lg w-full' />
      </div>
    )
  const data = view.data
  const shape = catalog.data
  const ladder = ladderOf(data)
  const selection =
    search.layer && search.node ? { kind: search.layer, id: search.node } : null
  const openRifts = data.rifts.filter((row) => OPEN_RIFTS.has(row.state)).length
  const tab = search.pane ?? 'scale'
  const still = <StillUniverse ladder={ladder} catalog={shape} onPick={pick} />
  return (
    <div
      data-surface='CosmographyScreen'
      className='flex min-w-0 flex-1 flex-col'
    >
      <div className='flex min-w-0 flex-col gap-4 border-b p-4 md:px-6'>
        <PageHeader
          title='The Heavens'
          icon={Layers}
          description='The one cosmos above the stars: its dimensions, clusters and galaxies, and the rifts, beings and phenomena between them.'
          actions={
            <Button onClick={openStudio}>
              <Plus />
              Shape the heavens
            </Button>
          }
          meta={
            <>
              <Badge variant='outline'>{`Epoch ${data.epoch}`}</Badge>
              <Badge variant='outline'>{`${plural(data.dimensions.length, 'dimension')}`}</Badge>
              <Badge variant='outline'>{`${plural(data.clusters.length, 'cluster')}`}</Badge>
              <Badge variant='outline'>{`${plural(data.galaxies.length, 'galaxy', 'galaxies')}`}</Badge>
              {openRifts > 0 && (
                <Badge variant='destructive'>{`${plural(openRifts, 'open rift')}`}</Badge>
              )}
            </>
          }
        />
      </div>
      <section
        aria-label='Map of the heavens'
        className='relative flex min-w-0 flex-col border-b'
      >
        <div className='relative h-scene min-w-0 bg-cosmos-void text-cosmos-label lg:h-scene-lg'>
          {data.dimensions.length === 0 ? (
            <div className='flex h-full items-center justify-center p-6'>
              <EmptyState
                icon={Layers}
                title='The cosmos is not laid out yet'
                description='The first epoch lays the prime dimension, a home group and a home galaxy around the stars; you can bring a dimension into being now.'
              />
            </div>
          ) : hasWebGL2() ? (
            <Suspense
              fallback={<Skeleton className='h-full w-full rounded-none' />}
            >
              <UniverseScene3D
                ladder={ladder}
                catalog={shape}
                routes={cosmos.data?.routes ?? []}
                selected={selection}
                onPick={pick}
                overview={overview}
                fallback={still}
              />
            </Suspense>
          ) : (
            still
          )}
          {selection && (
            <div className='absolute top-3 left-3 w-full max-w-sm'>
              <SelectedScale
                ladder={ladder}
                catalog={shape}
                kind={selection.kind}
                id={selection.id}
                onClear={() => select(undefined, undefined)}
              />
            </div>
          )}
          {data.dimensions.length > 0 && hasWebGL2() && (
            <div className='absolute top-3 right-3'>
              <Button
                variant='outline'
                size='sm'
                title='Bring the whole of the heavens back into view'
                onClick={showWhole}
              >
                <Maximize2 />
                Whole heavens
              </Button>
            </div>
          )}
          <div className='pointer-events-none absolute right-3 bottom-3 hidden max-w-sm md:block'>
            <Text variant='caption' tone='inherit' className='opacity-70'>
              Click a dimension, cluster or galaxy to read it · drag: turn ·
              wheel: zoom
            </Text>
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-2 bg-cosmos-void px-4 py-3 text-cosmos-label md:px-6'>
          <Legend
            ladder={ladder}
            selectedId={selection?.kind === 'dimension' ? selection.id : null}
            onPick={(id) => select('dimension', id)}
          />
        </div>
      </section>
      <div className='flex min-w-0 flex-col gap-4 p-4 md:p-6'>
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6'>
          <KpiTile
            label='Dimensions'
            value={data.dimensions.length}
            icon={Layers}
            tone='info'
          />
          <KpiTile
            label='Clusters'
            value={data.clusters.length}
            icon={Workflow}
            tone='verdigris'
          />
          <KpiTile
            label='Galaxies'
            value={data.galaxies.length}
            icon={Orbit}
            tone='gold'
          />
          <KpiTile
            label='Open rifts'
            value={openRifts}
            icon={Eye}
            tone='danger'
            harmful
          />
          <KpiTile
            label='Cosmic beings'
            value={data.beings.length}
            icon={Crown}
            tone='warning'
          />
          <KpiTile
            label='Phenomena'
            value={data.phenomena.length}
            icon={CloudFog}
            tone='info'
          />
        </div>
        <Tabs
          ref={panes}
          id='heavens-panes'
          className='scroll-mt-4'
          value={tab}
          onValueChange={(value) => setTab(value as HeavensTab)}
        >
          <TabsList aria-label='Heavens panel' className='w-full'>
            <TabsTrigger value='scale'>
              <Layers />
              Scale
            </TabsTrigger>
            <TabsTrigger value='create'>
              <Plus />
              Create
            </TabsTrigger>
            <TabsTrigger value='rifts'>
              <Eye />
              Rifts
              {openRifts > 0 && (
                <Badge size='sm' variant='secondary'>
                  {openRifts}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value='beings'>
              <Crown />
              Beings
            </TabsTrigger>
            <TabsTrigger value='phenomena'>
              <Sparkles />
              Phenomena
            </TabsTrigger>
            <TabsTrigger value='bodies'>
              <Gem />
              Bodies
            </TabsTrigger>
            <TabsTrigger value='events'>
              <History />
              Events
            </TabsTrigger>
            <TabsTrigger value='end'>
              <Skull />
              The end
            </TabsTrigger>
          </TabsList>
          <TabsContent
            value='scale'
            id='cosmography-ladder'
            className='flex min-w-0 flex-col gap-3'
          >
            <div
              id='cosmography-dimensions'
              className='flex min-w-0 flex-col gap-3'
            >
              <div id='cosmography-galaxies'>
                <ScaleNavigator
                  ladder={ladder}
                  catalog={shape}
                  selection={selection}
                  onSelect={(kind, id) => select(kind, id)}
                />
              </div>
            </div>
          </TabsContent>
          <TabsContent value='create' className='flex min-w-0 flex-col gap-4'>
            <CreateGalaxyStudio ladder={ladder} catalog={shape} />
            <CreateClusterStudio ladder={ladder} catalog={shape} />
            <CreateDimensionStudio ladder={ladder} catalog={shape} />
          </TabsContent>
          <TabsContent value='rifts'>
            <RiftsPanel ladder={ladder} />
          </TabsContent>
          <TabsContent value='beings'>
            <BeingsPanel ladder={ladder} catalog={shape} />
          </TabsContent>
          <TabsContent value='phenomena'>
            <PhenomenaPanel data={data} catalog={shape} />
          </TabsContent>
          <TabsContent value='bodies'>
            <HeavensPhysicsPanel />
          </TabsContent>
          <TabsContent value='events'>
            <EventsPanel ladder={ladder} catalog={shape} />
          </TabsContent>
          <TabsContent value='end'>
            <ApocalypseVariantPanel
              current={data.apocalypse_variant ?? null}
              likely={data.likely_variant}
              catalog={shape}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
