import { Suspense, lazy, useRef, useState } from 'react'
import {
  Building2,
  Castle,
  Home,
  Layers,
  Map as MapIcon,
  Tag,
  Tent,
  Users,
  X,
} from 'lucide-react'
import { postAction } from '@/api/actions'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Toggle } from '@/components/ui/toggle'
import { EmptyState, KpiTile, PagedList } from '@/components/domain'
import { Text } from '@/components/typography'
import { RecordRow } from '@/features/cosmography/parts'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import { why } from '@/features/dominion/model'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { MORPHOLOGIES } from '@/features/urban/labels'
import { BuildForge, BuildingPanel, DistrictPanel } from './CityControls'
import { CityLegend } from './CityLegend'
import { CityPlan2D } from './CityPlan2D'
import { type CityPick, type Zone } from './CityScene3D'
import { ZoneDot } from './ZoneDot'
import { type CityScene, useCityScene } from './api'
import { CITY_ICON, STATES, ZONES } from './labels'

const CityScene3D = lazy(() => import('./CityScene3D'))
const ZONE_ORDER = Object.keys(ZONES) as Zone[]

function ZoneFilter({
  scene,
  shown,
  onShown,
  labels,
  onLabels,
  flat,
  onFlat,
}: {
  scene: CityScene
  shown: ReadonlySet<Zone>
  onShown: (next: ReadonlySet<Zone>) => void
  labels: boolean
  onLabels: (next: boolean) => void
  flat: boolean
  onFlat: (next: boolean) => void
}) {
  const counts = new Map(scene.zones.map((row) => [row.zone, row]))
  return (
    <div className='pointer-events-auto flex max-w-xs min-w-0 flex-col gap-2 rounded-xl border bg-popover/90 p-3 shadow-lg backdrop-blur-sm'>
      <Text variant='caption' tone='muted'>
        Zones
      </Text>
      <div
        role='group'
        aria-label='Zones shown'
        className='flex min-w-0 flex-wrap gap-1.5'
      >
        {ZONE_ORDER.map((zone) => {
          const spec = ZONES[zone]
          const row = counts.get(zone)
          return (
            <Toggle
              key={zone}
              size='sm'
              variant='outline'
              pressed={shown.has(zone)}
              aria-label={`${spec.label}: ${plural(row?.districts ?? 0, 'district', 'districts')}, ${plural(row?.buildings ?? 0, 'building', 'buildings')}`}
              onPressedChange={(pressed) => {
                const next = new Set(shown)
                if (pressed) next.add(zone)
                else next.delete(zone)
                onShown(next)
              }}
            >
              <ZoneDot spec={spec} />
              {spec.label}
            </Toggle>
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Toggle
          size='sm'
          variant='outline'
          pressed={labels}
          onPressedChange={onLabels}
        >
          <Tag />
          Names
        </Toggle>
        <Toggle
          size='sm'
          variant='outline'
          pressed={flat}
          onPressedChange={onFlat}
        >
          <MapIcon />
          Flat plan
        </Toggle>
      </div>
    </div>
  )
}

function CityBody({
  scene,
  blocked,
}: {
  scene: CityScene
  blocked: string | null
}) {
  const [selected, setSelected] = useState<CityPick>(null)
  const [moving, setMoving] = useState<number | null>(null)
  const [shown, setShown] = useState<ReadonlySet<Zone>>(new Set(ZONE_ORDER))
  const [labels, setLabels] = useState(true)
  const [flat, setFlat] = useState(!hasWebGL2())
  const stage = useRef<HTMLElement>(null)
  const show = (next: Parameters<typeof setSelected>[0]) => {
    setSelected(next)
    stage.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const [tab, setTab] = useState('districts')
  const move = useGodAction({
    run: (cell: { q: number; r: number }) =>
      postAction('district:move', {
        district_id: moving ?? 0,
        q: cell.q,
        r: cell.r,
      }),
    success: () => {
      setMoving(null)
      return 'The district is moved'
    },
  })
  const pick = (next: CityPick) => {
    if (next?.kind === 'cell') {
      if (moving !== null) move.mutate({ q: next.q, r: next.r })
      return
    }
    setSelected(next)
  }
  const district =
    selected?.kind === 'district'
      ? scene.districts.find((item) => item.id === selected.id)
      : undefined
  const building =
    selected?.kind === 'building'
      ? scene.buildings.find((item) => item.node.id === selected.id)
      : undefined
  const homes = scene.districts.reduce((sum, item) => sum + item.dwellings, 0)
  const standing = scene.buildings.filter(
    (item) => item.state === 'complete'
  ).length
  const plan = (
    <CityPlan2D
      scene={scene}
      selected={selected}
      onPick={pick}
      fill
      labels={labels}
    />
  )
  const empty = scene.districts.length === 0 && scene.buildings.length === 0
  return (
    <>
      <section
        ref={stage}
        aria-label={`City of ${scene.town.name}`}
        className='relative flex min-w-0 scroll-mt-16 flex-col border-b'
      >
        <div className='relative h-scene min-w-0 overflow-hidden bg-card lg:h-scene-lg'>
          {empty ? (
            <div className='flex h-full items-center justify-center p-6'>
              <EmptyState
                icon={CITY_ICON}
                title='Nothing is built here yet'
                description='The town raises its first districts in the next epoch, or raise one now from the Build tab below.'
              />
            </div>
          ) : flat ? (
            <div className='h-full w-full p-6'>{plan}</div>
          ) : (
            <Suspense
              fallback={<Skeleton className='h-full w-full rounded-none' />}
            >
              <CityScene3D
                scene={scene}
                selected={selected}
                moving={moving}
                onPick={pick}
                fallback={plan}
                shown={shown}
                labels={labels}
              />
            </Suspense>
          )}
          <div className='pointer-events-none absolute top-3 bottom-3 left-3 flex w-full max-w-md min-w-0 flex-col gap-2 overflow-y-auto'>
            {moving !== null && (
              <div className='pointer-events-auto flex items-center gap-2 rounded-xl border border-primary bg-popover/95 p-3 shadow-lg'>
                <Text variant='caption'>
                  Pick the hex the district moves to.
                </Text>
                <Button
                  size='sm'
                  variant='ghost'
                  onClick={() => setMoving(null)}
                >
                  <X />
                  Stop
                </Button>
              </div>
            )}
            {district && (
              <div className='pointer-events-auto rounded-xl bg-popover/95 shadow-lg backdrop-blur-sm'>
                <DistrictPanel
                  key={district.id}
                  district={district}
                  blocked={why(blocked, move.isPending)}
                  moving={moving === district.id}
                  onMove={() =>
                    setMoving(moving === district.id ? null : district.id)
                  }
                  onClose={() => setSelected(null)}
                />
              </div>
            )}
            {building && (
              <div className='pointer-events-auto rounded-xl bg-popover/95 shadow-lg backdrop-blur-sm'>
                <BuildingPanel
                  key={building.node.id}
                  building={building}
                  districts={scene.districts}
                  blocked={blocked}
                  onClose={() => setSelected(null)}
                />
              </div>
            )}
          </div>
          {!empty && (
            <div className='pointer-events-none absolute top-3 right-3 hidden md:block'>
              <ZoneFilter
                scene={scene}
                shown={shown}
                onShown={setShown}
                labels={labels}
                onLabels={setLabels}
                flat={flat}
                onFlat={setFlat}
              />
            </div>
          )}
          <div className='pointer-events-none absolute right-3 bottom-3 hidden max-w-sm md:block'>
            <Text variant='caption' tone='muted'>
              Click a district or a building to rule it · drag: turn · wheel:
              zoom
            </Text>
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-3 bg-card px-4 py-3 md:px-6'>
          {!empty && (
            <div className='md:hidden'>
              <ZoneFilter
                scene={scene}
                shown={shown}
                onShown={setShown}
                labels={labels}
                onLabels={setLabels}
                flat={flat}
                onFlat={setFlat}
              />
            </div>
          )}
          <CityLegend scene={scene} />
        </div>
      </section>
      <div className='flex min-w-0 flex-col gap-4 p-4 md:p-6'>
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6'>
          <KpiTile
            label='People'
            value={scene.population}
            icon={Users}
            tone='info'
          />
          <KpiTile label='Homes' value={homes} icon={Home} tone='success' />
          <KpiTile
            label='Homeless'
            value={scene.homeless}
            icon={Tent}
            tone='danger'
            harmful
          />
          <KpiTile
            label='Districts'
            value={scene.districts.length}
            icon={Layers}
            tone='verdigris'
          />
          <KpiTile
            label='Buildings standing'
            value={standing}
            icon={Building2}
            tone='gold'
          />
          <KpiTile
            label='Walls'
            value={scene.walls_level}
            icon={Castle}
            tone='warning'
          />
        </div>
        <Text variant='caption' tone='muted'>
          {`A ${scene.tier.replaceAll('_', ' ')}, ${MORPHOLOGIES[scene.morphology].label.toLowerCase()}; walls of level ${scene.walls_level}${scene.walls_radius ? ` ${plural(scene.walls_radius, 'hex', 'hexes')} out` : ''}; roads of level ${scene.roads}; water from ${scene.water.replaceAll('_', ' ')}. Each house drawn stands for ${plural(scene.scale, 'home', 'homes')}, each tent for ${scene.scale} homeless households.`}
        </Text>
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList aria-label='City panel' className='w-full'>
            <TabsTrigger value='districts'>{`Districts · ${scene.districts.length}`}</TabsTrigger>
            <TabsTrigger value='buildings'>{`Buildings · ${scene.buildings.length}`}</TabsTrigger>
            <TabsTrigger value='build'>Build</TabsTrigger>
          </TabsList>
          <TabsContent
            value='districts'
            className='flex min-w-0 flex-col gap-2'
          >
            {scene.districts.length === 0 && (
              <Text variant='caption' tone='muted'>
                No district stands yet; raise one from the Build tab.
              </Text>
            )}
            <PagedList
              items={scene.districts}
              initial={8}
              noun={['district', 'districts']}
              className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
              itemKey={(row) => row.id}
            >
              {(row) => {
                const spec = DISTRICT_SPEC[row.kind]
                return (
                  <RecordRow
                    icon={spec.icon}
                    tone={spec.tone ?? 'muted'}
                    title={`${spec.label} · level ${row.level}`}
                    caption={`${ZONES[row.zone].label} · ${plural(row.cells.length, 'hex', 'hexes')} · ${plural(row.dwellings, 'home', 'homes')} · desirability ${row.desirability}`}
                    aside={
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() => show({ kind: 'district', id: row.id })}
                      >
                        Rule it
                      </Button>
                    }
                  />
                )
              }}
            </PagedList>
          </TabsContent>
          <TabsContent
            value='buildings'
            className='flex min-w-0 flex-col gap-2'
          >
            {scene.buildings.length === 0 && (
              <Text variant='caption' tone='muted'>
                No building stands yet; begin one from the Build tab.
              </Text>
            )}
            <PagedList
              items={scene.buildings}
              initial={8}
              noun={['building', 'buildings']}
              className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
              itemKey={(row) => row.node.id}
            >
              {(row) => {
                const spec = KIND_SPEC[row.kind]
                return (
                  <RecordRow
                    icon={spec.icon}
                    tone={spec.tone ?? 'muted'}
                    title={<Ref node={row.node} />}
                    caption={`${spec.label} · ${ZONES[row.zone].label} · ${STATES[row.state]}`}
                    aside={
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() =>
                          show({ kind: 'building', id: row.node.id })
                        }
                      >
                        Rule it
                      </Button>
                    }
                  />
                )
              }}
            </PagedList>
          </TabsContent>
          <TabsContent value='build' className='flex min-w-0 flex-col gap-2'>
            <BuildForge scene={scene} blocked={blocked} />
          </TabsContent>
        </Tabs>
      </div>
    </>
  )
}

export function CityPlane({
  settlementId,
  blocked,
}: {
  settlementId: number
  blocked: string | null
}) {
  const query = useCityScene(settlementId)
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
          icon={CITY_ICON}
          title='The city could not be drawn'
          description={query.error.message}
        />
      </div>
    )
  return <CityBody scene={query.data} blocked={blocked} />
}
