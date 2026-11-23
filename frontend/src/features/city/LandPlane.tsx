import { Suspense, lazy, useRef, useState } from 'react'
import {
  Droplets,
  Gem,
  Mountain,
  Pickaxe,
  Sprout,
  Trees,
  Wheat,
} from 'lucide-react'
import { agree, plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { OrnateFrame } from '@/components/ui/ornate'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, KpiTile, PagedList } from '@/components/domain'
import { Text } from '@/components/typography'
import { Facts, RecordRow } from '@/features/cosmography/parts'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import {
  COAST_WORDS,
  TEMPERATURE_WORDS,
  TERRAIN_WORDS,
} from '@/features/entity/affairs/labels'
import { COMMODITY } from '@/features/entity/economy/labels'
import { TERRAIN } from '@/features/entity/environment/labels'
import { RIVER_SPEC } from '@/features/entity/happenings/labels'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import {
  LandForge,
  PlacePanel,
  ResourcePanel,
  TilePanel,
  WorkPanel,
} from './LandControls'
import { LandPlan2D } from './LandPlan2D'
import { type LandPick } from './LandScene3D'
import { Dot } from './ZoneDot'
import { type LandScene, useLandScene } from './api'
import { COVERS, COVER_FILL, STATES } from './labels'
import { SHARE_LABEL } from './landShares'

const LandScene3D = lazy(() => import('./LandScene3D'))

type Cover = LandScene['tiles'][number]['cover']

function Legend({ scene }: { scene: LandScene }) {
  const counts = scene.tiles.reduce<Map<Cover, number>>(
    (found, tile) => found.set(tile.cover, (found.get(tile.cover) ?? 0) + 1),
    new Map()
  )
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1'>
      {[...counts.entries()].map(([cover, count]) => (
        <span key={cover} className='flex items-center gap-1.5'>
          <Dot fill={COVER_FILL[cover]} />
          <Text as='span' variant='caption'>
            {`${COVERS[cover]} · ${count} of ${plural(scene.tiles.length, 'tile', 'tiles')}`}
          </Text>
        </span>
      ))}
      <Text as='span' variant='caption' tone='muted'>
        {`River: ${RIVER_SPEC[scene.river].label.toLowerCase()} · coast: ${COAST_WORDS[scene.coast].toLowerCase()}`}
      </Text>
    </div>
  )
}

function LandBody({
  scene,
  blocked,
}: {
  scene: LandScene
  blocked: string | null
}) {
  const [selected, setSelected] = useState<LandPick>(null)
  const stage = useRef<HTMLElement>(null)
  const show = (next: Parameters<typeof setSelected>[0]) => {
    setSelected(next)
    stage.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const [tab, setTab] = useState('deposits')
  const plan = (
    <LandPlan2D scene={scene} selected={selected} onPick={setSelected} fill />
  )
  const pickId = selected !== null && 'id' in selected ? selected.id : null
  const tile =
    selected?.kind === 'tile'
      ? scene.tiles.find(
          (item) => item.q === selected.q && item.r === selected.r
        )
      : undefined
  const resource =
    selected?.kind === 'resource'
      ? scene.resources.find((item) => item.node.id === pickId)
      : undefined
  const work =
    selected?.kind === 'work'
      ? scene.works.find((item) => item.node.id === pickId)
      : undefined
  const town =
    selected?.kind === 'settlement'
      ? scene.settlements.find((item) => item.node.id === pickId)
      : undefined
  const place =
    selected?.kind === 'place'
      ? scene.places.find((item) => item.node.id === pickId)
      : undefined
  const close = () => setSelected(null)
  return (
    <>
      <section
        ref={stage}
        aria-label={`Land of ${scene.region.name}`}
        className='relative flex min-w-0 scroll-mt-16 flex-col'
      >
        <div className='scene-frame relative h-scene min-w-0 overflow-hidden bg-card lg:h-scene-lg'>
          {hasWebGL2() ? (
            <Suspense
              fallback={<Skeleton className='h-full w-full rounded-none' />}
            >
              <LandScene3D
                scene={scene}
                selected={selected}
                onPick={setSelected}
                fallback={plan}
              />
            </Suspense>
          ) : (
            <div className='h-full w-full p-6'>{plan}</div>
          )}
          <div className='pointer-events-none absolute top-3 bottom-3 left-3 flex w-full max-w-md min-w-0 flex-col gap-2 overflow-y-auto'>
            {[
              tile && (
                <TilePanel
                  key='tile'
                  scene={scene}
                  tile={tile}
                  blocked={blocked}
                  onClose={close}
                />
              ),
              resource && (
                <ResourcePanel
                  key={`resource-${resource.node.id}`}
                  resource={resource}
                  blocked={blocked}
                  onClose={close}
                />
              ),
              work && (
                <WorkPanel
                  key='work'
                  work={work}
                  blocked={blocked}
                  onClose={close}
                />
              ),
              town && (
                <PlacePanel
                  key='town'
                  item={town}
                  kind='settlement'
                  onClose={close}
                />
              ),
              place && (
                <PlacePanel
                  key='place'
                  item={place}
                  kind='place'
                  onClose={close}
                />
              ),
            ]
              .filter(Boolean)
              .map((panel, index) => (
                <div
                  key={index}
                  className='pointer-events-auto rounded-xl bg-popover/95 shadow-lg backdrop-blur-sm'
                >
                  {panel}
                </div>
              ))}
          </div>
          <div className='pointer-events-none absolute right-3 bottom-3 hidden max-w-sm md:block'>
            <Text variant='caption' tone='muted'>
              Click a tile, a town or a deposit to rule it · drag: turn · wheel:
              zoom
            </Text>
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-1 bg-card px-4 py-3 md:px-6'>
          <Legend scene={scene} />
        </div>
      </section>
      <div className='p-4 md:p-6'>
        <OrnateFrame
          footCrest
          className='flex min-w-0 flex-col gap-4 px-6 py-8'
        >
          <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6'>
            <KpiTile
              label='Elevation'
              value={scene.elevation}
              icon={Mountain}
              tone='muted'
            />
            <KpiTile
              label='Forest'
              value={`${scene.forest_cover}%`}
              icon={Trees}
              tone='success'
            />
            <KpiTile
              label='Farmed'
              value={`${scene.farmed}%`}
              icon={Wheat}
              tone='gold'
            />
            <KpiTile
              label='Mined'
              value={`${scene.mined}%`}
              icon={Pickaxe}
              tone='warning'
            />
            <KpiTile
              label='Moisture'
              value={scene.moisture}
              icon={Droplets}
              tone='info'
            />
            <KpiTile
              label='Deposits'
              value={scene.resources.length}
              icon={Gem}
              tone='verdigris'
            />
          </div>
          <Facts
            items={[
              [
                'Terrain',
                TERRAIN[scene.terrain]?.label ?? TERRAIN_WORDS[scene.terrain],
              ],
              ['Climate', TEMPERATURE_WORDS[scene.temperature]],
              ['Roughness', scene.roughness],
              ['Soil fertility', scene.soil_fertility],
              ['Magic density', scene.magic_density],
              [SHARE_LABEL.grazed, `${scene.grazed}%`],
              [SHARE_LABEL.wetland, `${scene.wetland}%`],
              [SHARE_LABEL.cleared, `${scene.cleared}%`],
              [SHARE_LABEL.built, `${scene.built}%`],
            ]}
          />
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList aria-label='Land panel' className='w-full'>
              <TabsTrigger value='deposits'>{`Deposits · ${scene.resources.length}`}</TabsTrigger>
              <TabsTrigger value='works'>{`Works · ${scene.works.length}`}</TabsTrigger>
              <TabsTrigger value='towns'>{`Towns · ${scene.settlements.length}`}</TabsTrigger>
              <TabsTrigger value='shape'>Shape</TabsTrigger>
            </TabsList>
            <TabsContent
              value='deposits'
              className='flex min-w-0 flex-col gap-2'
            >
              {scene.resources.length === 0 && (
                <Text variant='caption' tone='muted'>
                  No deposit lies in this land yet; lay one from the Shape tab.
                </Text>
              )}
              <PagedList
                items={scene.resources}
                initial={8}
                noun={['deposit', 'deposits']}
                className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
                itemKey={(row) => row.node.id}
              >
                {(row) => (
                  <RecordRow
                    icon={COMMODITY[row.commodity].icon}
                    tone='gold'
                    title={<Ref node={row.node} />}
                    caption={`${COMMODITY[row.commodity].label} · richness ${row.richness} · ${row.reserve} of ${row.initial_reserve} left`}
                    aside={
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() =>
                          show({ kind: 'resource', id: row.node.id })
                        }
                      >
                        Rule the resource
                      </Button>
                    }
                  />
                )}
              </PagedList>
            </TabsContent>
            <TabsContent value='works' className='flex min-w-0 flex-col gap-2'>
              {scene.works.length === 0 && (
                <Text variant='caption' tone='muted'>
                  No work stands in the open land; mines and quarries are raised
                  here by the towns that work it.
                </Text>
              )}
              <PagedList
                items={scene.works}
                initial={8}
                noun={['work', 'works']}
                className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
                itemKey={(row) => row.node.id}
              >
                {(row) => (
                  <RecordRow
                    icon={KIND_SPEC[row.kind].icon}
                    tone={KIND_SPEC[row.kind].tone ?? 'muted'}
                    title={<Ref node={row.node} />}
                    caption={`${KIND_SPEC[row.kind].label} · ${STATES[row.state]}`}
                    aside={
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() => show({ kind: 'work', id: row.node.id })}
                      >
                        Rule the work
                      </Button>
                    }
                  />
                )}
              </PagedList>
            </TabsContent>
            <TabsContent value='towns' className='flex min-w-0 flex-col gap-2'>
              {scene.settlements.length === 0 && (
                <Text variant='caption' tone='muted'>
                  No town stands in this land yet.
                </Text>
              )}
              <PagedList
                items={scene.settlements}
                initial={8}
                noun={['town', 'towns']}
                className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
                itemKey={(row) => row.node.id}
              >
                {(row) => (
                  <RecordRow
                    icon={Sprout}
                    tone='info'
                    title={<Ref node={row.node} />}
                    caption={`${row.detail} ${agree(Number(row.detail), 'person', 'people')}`}
                    aside={
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() =>
                          show({ kind: 'settlement', id: row.node.id })
                        }
                      >
                        Show
                      </Button>
                    }
                  />
                )}
              </PagedList>
            </TabsContent>
            <TabsContent value='shape' className='flex min-w-0 flex-col gap-2'>
              <LandForge scene={scene} blocked={blocked} />
            </TabsContent>
          </Tabs>
        </OrnateFrame>
      </div>
    </>
  )
}

export function LandPlane({
  regionId,
  blocked,
}: {
  regionId: number
  blocked: string | null
}) {
  const query = useLandScene(regionId)
  if (query.isPending)
    return (
      <div className='flex min-w-0 flex-col gap-4 p-4 md:p-6'>
        <Skeleton className='h-scene w-full lg:h-scene-lg' />
      </div>
    )
  if (query.isError)
    return (
      <div className='p-4 md:p-6'>
        <EmptyState
          icon={Mountain}
          title='The land could not be drawn'
          description={query.error.message}
        />
      </div>
    )
  return <LandBody scene={query.data} blocked={blocked} />
}
