import {
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Orbit, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/domain'
import { Text } from '@/components/typography'
import {
  CosmosGalaxyPanel,
  GalaxySwitcher,
} from '@/features/cosmography/CosmosGalaxyPanel'
import {
  useCosmography,
  useCosmographyCatalog,
} from '@/features/cosmography/api'
import {
  chooseGalaxy,
  cosmosInGalaxy,
  leavingRoutes,
} from '@/features/cosmography/cosmosGalaxy'
import { Cosmos2D } from './Cosmos2D'
import { CosmosLegend } from './CosmosLegend'
import { CosmosSidePanel } from './CosmosSidePanel'
import { CosmosTopBar } from './CosmosTopBar'
import { useCosmos, useCosmosState } from './api'
import { homeWorldId, indexCosmos } from './model/cosmosModel'
import { useRuleBook } from './model/rules'
import { type FocusRequest } from './scene3d/CameraRig'
import { useCosmosSelection } from './useCosmosSelection'
import {
  useCosmosViewSettings,
  useReducedMotion,
} from './useCosmosViewSettings'

const CosmosScene3D = lazy(() => import('./scene3d/CosmosScene3D'))

const DESCEND_DELAY_MS = 650

type FocusTarget =
  | { kind: 'world'; id: number }
  | { kind: 'star'; id: number }
  | { kind: 'overview' }

export function CosmosView() {
  const navigate = useNavigate()
  const cosmos = useCosmos()
  const heavens = useCosmography()
  const catalog = useCosmographyCatalog()
  const { data: state } = useCosmosState()
  const rules = useRuleBook()
  const selection = useCosmosSelection()
  const settings = useCosmosViewSettings()
  const reducedMotion = useReducedMotion()
  const galaxyId = chooseGalaxy(
    heavens.data,
    selection.galaxyId,
    selection.worldId,
    state?.world?.primary_world_id ?? undefined
  )
  const index = useMemo(
    () =>
      cosmos.data
        ? indexCosmos(cosmosInGalaxy(cosmos.data, heavens.data, galaxyId))
        : undefined,
    [cosmos.data, heavens.data, galaxyId]
  )
  const galaxy = heavens.data?.galaxies.find((row) => row.id === galaxyId)
  const leaving = cosmos.data
    ? leavingRoutes(cosmos.data, heavens.data, galaxyId)
    : 0
  const home = index
    ? homeWorldId(index, state?.world?.primary_world_id)
    : undefined
  const worldId = index?.world(selection.worldId) ? selection.worldId : home
  const [focus, setFocus] = useState<FocusRequest>({
    kind: 'overview',
    nonce: 0,
  })
  const [highlightedRouteId, setHighlightedRouteId] = useState<
    number | undefined
  >()
  const descendTimer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(descendTimer.current), [])
  const requestFocus = useCallback(
    (target: FocusTarget) =>
      setFocus((current) => ({ ...target, nonce: current.nonce + 1 })),
    []
  )
  const { selectWorld, selectStar, openPanel } = selection
  const chooseWorld = useCallback(
    (id: number) => {
      selectWorld(id)
      if (settings.view === '3d') requestFocus({ kind: 'world', id })
    },
    [selectWorld, settings.view, requestFocus]
  )
  const descend = useCallback(
    (id: number) => {
      const go = () => void navigate({ href: `/map?world=${id}` })
      window.clearTimeout(descendTimer.current)
      if (settings.view !== '3d' || reducedMotion) {
        go()
        return
      }
      requestFocus({ kind: 'world', id })
      descendTimer.current = window.setTimeout(go, DESCEND_DELAY_MS)
    },
    [navigate, settings.view, reducedMotion, requestFocus]
  )
  const pickRoute = useCallback(
    (routeId: number) => {
      const route = index?.route(routeId)
      if (!route) return
      const endpoint =
        worldId !== undefined &&
        (route.world_a_id === worldId || route.world_b_id === worldId)
          ? worldId
          : route.world_a_id
      selectWorld(endpoint)
      openPanel('world')
      setHighlightedRouteId(routeId)
    },
    [index, worldId, selectWorld, openPanel]
  )
  const sons = state?.sons ?? []
  const resource = state?.world?.travel_resource
  const empty = index
    ? index.data.stars.length === 0 && index.worlds.length === 0
    : false
  return (
    <div className='flex min-w-0 flex-1 flex-col'>
      <div className='flex min-w-0 flex-col gap-4 border-b p-4 md:px-6'>
        <CosmosTopBar
          index={index}
          rules={rules}
          epoch={state?.world?.epoch}
          alignmentUntil={state?.world?.alignment_until_epoch}
          resource={resource}
          view={settings.view}
          quality={settings.quality}
          failure={settings.failure}
          onView={settings.setView}
          onQuality={settings.setQuality}
          onOpenResource={() => openPanel('command', 'resource')}
          galaxySwitch={
            heavens.data && catalog.data && heavens.data.galaxies.length > 0 ? (
              <GalaxySwitcher
                heavens={heavens.data}
                catalog={catalog.data}
                value={galaxyId}
                onChange={selection.selectGalaxy}
              />
            ) : undefined
          }
        />
      </div>
      {cosmos.isLoading && (
        <div className='flex min-w-0 flex-1 flex-col lg:flex-row'>
          <Skeleton className='h-96 w-full rounded-none lg:h-svh lg:flex-1' />
          <div className='flex flex-col gap-3 p-4 lg:w-md'>
            <Skeleton className='h-control-md w-full' />
            <Skeleton className='h-textarea w-full' />
          </div>
        </div>
      )}
      {cosmos.error && (
        <div className='p-4 md:p-6'>
          <EmptyState
            icon={Orbit}
            title='The cosmos could not be read'
            description={cosmos.error.message}
            action={
              <Button variant='outline' onClick={() => void cosmos.refetch()}>
                <RefreshCw />
                Try again
              </Button>
            }
          />
        </div>
      )}
      {index && (
        <div className='flex min-w-0 flex-1 flex-col lg:flex-row lg:items-start'>
          <section
            aria-label='Cosmos view'
            className='flex min-w-0 flex-col border-b lg:sticky lg:top-topbar lg:h-svh lg:flex-1 lg:border-r lg:border-b-0 lg:pb-topbar'
          >
            <div className='relative h-96 min-w-0 sm:h-160 lg:h-auto lg:flex-1'>
              {settings.view === '3d' ? (
                <Suspense
                  fallback={<Skeleton className='h-full w-full rounded-none' />}
                >
                  <CosmosScene3D
                    index={index}
                    sons={sons}
                    selectedWorldId={worldId}
                    selectedStarId={selection.starId}
                    highlightedRouteId={highlightedRouteId}
                    quality={settings.quality}
                    reducedMotion={reducedMotion}
                    focus={focus}
                    galaxy={galaxy}
                    shape={catalog.data?.shape}
                    onFailure={settings.reportFailure}
                    onWorld={selectWorld}
                    onWorldDouble={descend}
                    onStar={selectStar}
                    onStarDouble={(id) => requestFocus({ kind: 'star', id })}
                    onRoute={pickRoute}
                    onVoyage={(journeyId) => {
                      const journey = index.data.journeys.find(
                        (item) => item.id === journeyId
                      )
                      if (journey) pickRoute(journey.route_id)
                    }}
                  />
                </Suspense>
              ) : empty ? (
                <div className='flex h-full items-center justify-center p-6'>
                  <EmptyState
                    icon={Orbit}
                    title='The void is still silent'
                    description='It will appear here when the first star ignites.'
                  />
                </div>
              ) : (
                <Cosmos2D
                  index={index}
                  selectedWorldId={worldId}
                  selectedStarId={selection.starId}
                  onSelectWorld={selectWorld}
                  onSelectStar={selectStar}
                  onDescend={descend}
                />
              )}
            </div>
            <div className='flex min-w-0 flex-col gap-2 bg-cosmos-void px-4 py-3 text-cosmos-label md:px-6'>
              <CosmosLegend index={index} />
              {settings.failure && (
                <Text variant='caption' tone='inherit' className='opacity-80'>
                  {`This browser cannot draw the 3D sky (${settings.failure}); the cosmos is drawn in 2D.`}
                </Text>
              )}
            </div>
          </section>
          <aside
            aria-label='Cosmos panel'
            className='flex min-w-0 flex-col gap-4 p-4 md:px-6 lg:w-md lg:shrink-0 xl:w-lg'
          >
            <CosmosSidePanel
              index={index}
              rules={rules}
              sons={sons}
              homeWorldId={home}
              worldId={worldId}
              starId={selection.starId}
              panel={selection.panel}
              section={selection.section}
              resource={resource}
              highlightedRouteId={highlightedRouteId}
              onSelectWorld={chooseWorld}
              onOpenPanel={openPanel}
              onDescend={descend}
              galaxyId={galaxyId}
              onSelectGalaxy={selection.selectGalaxy}
              galaxyPanel={
                heavens.data && catalog.data ? (
                  <CosmosGalaxyPanel
                    heavens={heavens.data}
                    catalog={catalog.data}
                    galaxyId={galaxyId}
                    leaving={leaving}
                    onChange={selection.selectGalaxy}
                  />
                ) : undefined
              }
            />
          </aside>
        </div>
      )}
    </div>
  )
}
