import { useCallback, useMemo, useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import { Compass, Loader2, Map as MapIcon, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { useIsMobile } from '@/hooks/useIsMobile'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Medallion, PageHeader } from '@/components/domain'
import { useThemeColors } from '@/components/domain/useThemeColors'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { useGlobalWorld } from '@/components/layout/worldFilter'
import { Text } from '@/components/typography'
import { EpochStarChip } from '@/features/cosmos/EpochStarChip'
import {
  MapCanvas,
  type MapViewport,
  type ScreenPoint,
  type ZoomCommand,
} from './MapCanvas'
import { MapHoverOverlay } from './MapHoverOverlay'
import { MapLegend } from './MapLegend'
import { type NotePopup, MapNoteOverlay } from './MapNoteOverlay'
import { MapScaleOverlay } from './MapScaleOverlay'
import { type StackPopup, MapStackOverlay } from './MapStackOverlay'
import { MapStatusLine } from './MapStatusLine'
import { MapTimeSlider } from './MapTimeSlider'
import { MapToolbar, type WorldOption } from './MapToolbar'
import { PastEpochBanner } from './PastEpochBanner'
import {
  type MapView as MapViewData,
  ruleValue,
  useAddMapNote,
  useCatalogue,
  useCosmos,
  useLanguages,
  useMoveMarker,
  useRegenerateMap,
  useRemoveMapNote,
  useRules,
  useSons,
  useWorldMap,
} from './api'
import {
  type LayerMode,
  type Overlay,
  LAYER_MODES,
  OVERLAYS,
  positionedPoints,
  tierOf,
} from './mapModel'
import { type MapSearch } from './mapRouteSearch'
import { type HitTarget, type MarkerFilter, type Thresholds } from './mapScene'
import { entityStack, eventStack, warStack } from './mapStacks'
import { type HoverText, hoverText } from './mapText'
import { useLayerPalette } from './useLayerPalette'
import {
  isBoolean,
  isNumber,
  isStringList,
  oneOf,
  usePersistentState,
} from './usePersistentState'
import { useReducedMotion } from './useReducedMotion'

const ITEM = navItem('map')
const STORAGE = {
  world: 'aerona.map.world',
  mode: 'aerona.map.layer',
  overlays: 'aerona.map.overlays',
  legend: 'aerona.map.legend',
  hidden: 'aerona.map.hidden-types',
  fallen: 'aerona.map.fallen',
}
const DEFAULT_OVERLAYS: Record<Overlay, boolean> = {
  roads: true,
  trade: true,
  ties: true,
  wars: true,
  events: true,
  labels: true,
  fog: true,
}
const NARROW_LEGEND_PX = 600
const isOverlays = (value: unknown) =>
  typeof value === 'object' &&
  value !== null &&
  OVERLAYS.every((key) => {
    const found = (value as Record<string, unknown>)[key]
    return found === undefined || typeof found === 'boolean'
  })
const CREATOR_NAME = 'The Creator'
const FALLBACK = {
  town: 2000,
  city: 10000,
  greatCity: 50000,
  trend: 5,
  leakFirst: 30,
  leakSecond: 60,
}

function MapLoading() {
  return (
    <div
      role='status'
      className='flex min-h-120 min-w-0 flex-1 flex-col items-center justify-center gap-3 rounded-xl border bg-card'
    >
      <Medallion icon={Compass} />
      <Text as='span' weight='medium'>
        Drawing the map…
      </Text>
      <Skeleton className='h-badge-md w-48' />
    </div>
  )
}

function useMapSettings() {
  const rules = useRules()
  return useMemo(() => {
    const data = rules.data
    const thresholds: Thresholds = {
      town: ruleValue(data, 'politics', 'town_population', FALLBACK.town),
      city: ruleValue(data, 'politics', 'city_population', FALLBACK.city),
      greatCity: ruleValue(
        data,
        'politics',
        'metropolis_population',
        FALLBACK.greatCity
      ),
    }
    return {
      thresholds,
      trendPct: ruleValue(
        data,
        'ui',
        'map_population_trend_min_pct',
        FALLBACK.trend
      ),
      leakFirst: ruleValue(
        data,
        'cosmic_horror',
        'warning_1',
        FALLBACK.leakFirst
      ),
      leakSecond: ruleValue(
        data,
        'cosmic_horror',
        'warning_2',
        FALLBACK.leakSecond
      ),
    }
  }, [rules.data])
}

export function MapView() {
  const search = useSearch({ strict: false }) as MapSearch
  const globalWorld = useGlobalWorld()
  const navigate = useNavigate()
  const mobile = useIsMobile()
  const cosmos = useCosmos()
  const [storedWorld, setStoredWorld] = usePersistentState<number>(
    STORAGE.world,
    0,
    isNumber
  )
  const worlds: WorldOption[] = useMemo(
    () =>
      (cosmos.data?.worlds ?? []).map((item) => ({
        id: item.world.id,
        name: item.world.name,
        typeLabel: item.type_label,
      })),
    [cosmos.data]
  )
  const worldId =
    worlds.find((world) => world.id === search.world)?.id ??
    worlds.find((world) => world.id === globalWorld)?.id ??
    worlds.find((world) => world.id === storedWorld)?.id ??
    worlds[0]?.id ??
    null
  const map = useWorldMap(worldId, search.epoch ?? null)

  const setSearch = useCallback(
    (patch: Partial<MapSearch>) =>
      navigate({
        to: '.',
        search: (previous: MapSearch) => {
          const next: Record<string, unknown> = { ...previous, ...patch }
          for (const key of Object.keys(next))
            if (next[key] === undefined) delete next[key]
          return next
        },
      }),
    [navigate]
  )

  let body
  if (cosmos.isPending || (worldId !== null && map.isPending))
    body = <MapLoading />
  else if (cosmos.error || map.error)
    body = (
      <Alert variant='destructive'>
        <AlertTitle>The map could not be drawn</AlertTitle>
        <AlertDescription className='flex flex-wrap items-center gap-3'>
          <span className='min-w-0 flex-1'>
            {(cosmos.error ?? map.error)?.message}
          </span>
          <Button
            size='sm'
            variant='outline'
            onClick={() =>
              void (cosmos.error ? cosmos.refetch() : map.refetch())
            }
          >
            <RefreshCw />
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  else if (worldId === null || !map.data)
    body = (
      <EmptyState
        icon={MapIcon}
        title='No land to map yet'
        description='The first land is shaped at genesis. Its regions, peoples and roads are drawn here.'
      />
    )
  else
    body = (
      <MapScreen
        view={map.data}
        loadingEpoch={map.isPlaceholderData ? (search.epoch ?? 'today') : null}
        worlds={worlds}
        mobile={mobile}
        focusId={search.focus ?? null}
        onWorld={(id) => {
          setStoredWorld(id)
          setSearch({ world: id, epoch: undefined, focus: undefined })
        }}
        onEpoch={(epoch) => setSearch({ epoch: epoch ?? undefined })}
        onFocus={(id) => setSearch({ focus: id })}
      />
    )
  return (
    <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4 p-4 md:p-6'>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        meta={<EpochStarChip />}
      />
      {body}
    </div>
  )
}

type MapScreenProps = {
  view: MapViewData
  loadingEpoch: number | 'today' | null
  worlds: WorldOption[]
  mobile: boolean
  focusId: number | null
  onWorld: (id: number) => void
  onEpoch: (epoch: number | null) => void
  onFocus: (id: number) => void
}

function MapScreen({
  view,
  loadingEpoch,
  worlds,
  mobile,
  focusId,
  onWorld,
  onEpoch,
  onFocus,
}: MapScreenProps) {
  const tokens = useThemeColors()
  const reducedMotion = useReducedMotion()
  const settings = useMapSettings()
  const drawer = useDrawerStack()
  const sons = useSons()
  const languages = useLanguages()
  const catalogue = useCatalogue()
  const [mode, setMode] = usePersistentState<LayerMode>(
    STORAGE.mode,
    'terrain',
    oneOf(LAYER_MODES)
  )
  const [storedOverlays, setOverlays] = usePersistentState<
    Partial<Record<Overlay, boolean>>
  >(STORAGE.overlays, DEFAULT_OVERLAYS, isOverlays)
  const overlays = useMemo(
    () => ({ ...DEFAULT_OVERLAYS, ...storedOverlays }),
    [storedOverlays]
  )
  const [legendOpen, setLegendOpen] = usePersistentState<boolean>(
    STORAGE.legend,
    () => window.innerWidth > NARROW_LEGEND_PX,
    isBoolean
  )
  const [hiddenTypes, setHiddenTypes] = usePersistentState<string[]>(
    STORAGE.hidden,
    [],
    isStringList
  )
  const [fallen, setFallen] = usePersistentState<boolean>(
    STORAGE.fallen,
    true,
    isBoolean
  )
  const filter: MarkerFilter = useMemo(
    () => ({ hiddenTypes: new Set(hiddenTypes), fallen }),
    [hiddenTypes, fallen]
  )
  const [noteMode, setNoteMode] = useState(false)
  const [popup, setPopup] = useState<NotePopup | null>(null)
  const [stack, setStack] = useState<StackPopup | null>(null)
  const [hover, setHover] = useState<{
    text: HoverText
    x: number
    y: number
  } | null>(null)
  const [viewport, setViewport] = useState<MapViewport | null>(null)
  const [command, setCommand] = useState<ZoomCommand | null>(null)

  const addNote = useAddMapNote()
  const removeNote = useRemoveMapNote()
  const moveMarker = useMoveMarker()
  const regenerate = useRegenerateMap()

  const past = view.time.shown < view.time.current
  const activeNoteMode = noteMode && !past
  const typeLabels = useMemo(
    () =>
      new Map(
        (catalogue.data?.entity_types ?? []).map((type) => [
          type.key,
          type.label,
        ])
      ),
    [catalogue.data]
  )
  const names = useMemo(
    () => ({
      sons: new Map(
        (sons.data ?? []).map((item) => [item.son.id, item.son.name])
      ),
      languages: new Map(
        (languages.data ?? []).map((item) => [
          item.language.id,
          item.language.name,
        ])
      ),
      creatorName: CREATOR_NAME,
    }),
    [sons.data, languages.data]
  )
  const palette = useLayerPalette(view, mode, names, tokens)
  const points = useMemo(() => positionedPoints(view), [view])
  const pointById = useMemo(
    () => new Map(points.map((point) => [point.id, point])),
    [points]
  )
  const findable = useMemo(
    () => points.map((point) => ({ id: point.id, name: point.name })),
    [points]
  )
  const leak = view.world.leakage
  const leakLevel: 0 | 1 | 2 =
    leak >= settings.leakSecond ? 2 : leak >= settings.leakFirst ? 1 : 0
  const starId = view.world.epoch_star_entity_id
  const starName =
    !past && starId ? (pointById.get(starId)?.name ?? null) : null
  const regionIds = new Set(view.geometry.regions.map((region) => region.id))
  const markerCount = points.filter((point) => !regionIds.has(point.id)).length
  const world = worlds.find((item) => item.id === view.world.id)

  const openRecord = (id: number) =>
    drawer.open({ kind: 'entity', id: String(id) })

  const onActivate = (hit: HitTarget, screen: ScreenPoint) => {
    setStack(null)
    if (hit.kind === 'note') {
      const note = view.notes.find((item) => item.id === hit.id)
      if (note) setPopup({ kind: 'read', x: screen.x, y: screen.y, note })
      return
    }
    setPopup(null)
    if (hit.kind === 'line') return
    if ((hit.members?.length ?? 0) > 1) {
      const built =
        hit.kind === 'war'
          ? warStack(hit, view, pointById, screen)
          : hit.kind === 'event'
            ? eventStack(hit, view, pointById, screen)
            : entityStack(
                hit,
                view,
                pointById,
                typeLabels,
                settings.thresholds,
                screen
              )
      if (built) {
        setStack(built)
        return
      }
    }
    openRecord(hit.id)
  }

  const onEmptyClick = (at: ScreenPoint, screen: ScreenPoint) => {
    setStack(null)
    if (!activeNoteMode) {
      setPopup(null)
      return
    }
    setPopup({ kind: 'new', x: screen.x, y: screen.y, mapX: at.x, mapY: at.y })
  }

  const onMove = (hit: HitTarget, at: ScreenPoint) =>
    moveMarker.mutate(
      { entityId: hit.id, x: at.x, y: at.y },
      {
        onSuccess: () =>
          toast.success('Moved. The map is redrawn around its new place.'),
        onError: (error) => toast.error(error.message),
      }
    )

  const onSaveNote = (text: string, color: string) => {
    if (popup?.kind !== 'new') return
    if (!text) {
      toast.error('A note must have text.')
      return
    }
    addNote.mutate(
      { world_id: view.world.id, x: popup.mapX, y: popup.mapY, text, color },
      {
        onSuccess: () => {
          toast.success('Note pinned')
          setPopup(null)
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }

  const onDeleteNote = (noteId: number) =>
    removeNote.mutate(noteId, {
      onSuccess: () => {
        toast.success('Note deleted')
        setPopup(null)
      },
      onError: (error) => toast.error(error.message),
    })

  const onRegenerate = () =>
    regenerate.mutate(view.world.id, {
      onSuccess: (result) =>
        toast.success(result.message || 'The map was redrawn.'),
      onError: (error) => toast.error(error.message),
    })

  return (
    <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4'>
      <MapToolbar
        mode={mode}
        onMode={setMode}
        overlays={overlays}
        onOverlay={(overlay, on) =>
          setOverlays((current) => ({ ...current, [overlay]: on }))
        }
        worlds={worlds}
        worldId={view.world.id}
        onWorld={onWorld}
        legendOpen={legendOpen}
        onLegend={setLegendOpen}
        noteMode={activeNoteMode}
        onNoteMode={(on) => {
          setPopup(null)
          setNoteMode(on)
        }}
        past={past}
        findable={findable}
        onFind={onFocus}
        onZoom={(kind) => setCommand({ kind, nonce: Date.now() })}
        onRegenerate={onRegenerate}
        regenerating={regenerate.isPending}
        mobile={mobile}
      />
      {past && (
        <PastEpochBanner
          epoch={view.time.shown}
          snapshot={view.time.snapshots.includes(view.time.shown)}
          onToday={() => onEpoch(null)}
        />
      )}
      <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4 lg:flex-row'>
        <div
          data-map-frame
          className='relative min-h-120 min-w-0 flex-1 overflow-hidden rounded-lg border md:min-h-160'
        >
          <MapCanvas
            view={view}
            tokens={tokens}
            palette={palette}
            mode={mode}
            overlays={overlays}
            filter={filter}
            past={past}
            noteMode={activeNoteMode}
            thresholds={settings.thresholds}
            trendPct={settings.trendPct}
            leakLevel={leakLevel}
            focusId={focusId}
            reducedMotion={reducedMotion}
            command={command}
            label={`Map of ${view.world.name}. Use the arrow keys to pan and plus or minus to zoom.`}
            onActivate={onActivate}
            onHover={(hit, at) => {
              const text = hit
                ? hoverText(
                    hit,
                    view,
                    pointById,
                    typeLabels,
                    settings.thresholds,
                    names
                  )
                : null
              setHover(text ? { text, x: at.x, y: at.y } : null)
            }}
            onEmptyClick={onEmptyClick}
            onMove={onMove}
            onViewport={setViewport}
          />
          {loadingEpoch !== null && (
            <div
              role='status'
              className='absolute inset-x-0 top-3 flex justify-center'
            >
              <Badge variant='solid'>
                <Loader2 className='animate-spin' />
                {loadingEpoch === 'today'
                  ? 'Loading the world today…'
                  : `Loading Epoch ${loadingEpoch}…`}
              </Badge>
            </div>
          )}
          <MapScaleOverlay
            scale={viewport?.transform.k ?? 0}
            starName={starName}
          />
          {hover && viewport && !popup && !stack && (
            <MapHoverOverlay
              hover={hover.text}
              x={hover.x}
              y={hover.y}
              width={viewport.size.width}
            />
          )}
          {stack && viewport && (
            <MapStackOverlay
              key={`${stack.title}-${stack.x}-${stack.y}`}
              popup={stack}
              width={viewport.size.width}
              height={viewport.size.height}
              onOpen={openRecord}
              onZoom={(centre) => {
                setStack(null)
                setCommand({ kind: 'at', ...centre, nonce: Date.now() })
              }}
              onClose={() => setStack(null)}
            />
          )}
          {popup && viewport && (
            <MapNoteOverlay
              key={
                popup.kind === 'read'
                  ? `read-${popup.note.id}`
                  : `new-${popup.x}-${popup.y}`
              }
              popup={popup}
              width={viewport.size.width}
              height={viewport.size.height}
              saving={addNote.isPending || removeNote.isPending}
              onSave={onSaveNote}
              onDelete={(note) => onDeleteNote(note.id)}
              onClose={() => setPopup(null)}
            />
          )}
        </div>
        {legendOpen && (
          <Card className='min-w-0 lg:w-80 lg:shrink-0'>
            <CardContent className='flex min-w-0 flex-col gap-3'>
              <MapLegend
                view={view}
                mode={mode}
                overlays={overlays}
                palette={palette}
                points={points}
                filter={filter}
                onToggleType={(type, shown) =>
                  setHiddenTypes((current) =>
                    shown
                      ? current.filter((item) => item !== type)
                      : [...new Set([...current, type])]
                  )
                }
                onFallen={setFallen}
                thresholds={settings.thresholds}
                trendPct={settings.trendPct}
                typeLabels={typeLabels}
                tierOfPoint={(id) => tierOf(view, id, settings.thresholds)}
              />
            </CardContent>
          </Card>
        )}
      </div>
      <MapTimeSlider
        current={view.time.current}
        shown={view.time.shown}
        onShow={onEpoch}
      />
      <MapStatusLine
        worldName={view.world.name}
        typeLabel={world?.typeLabel ?? view.world.world_type}
        multiWorld={worlds.length > 1}
        knownCells={view.geometry.extent.known_cells}
        regions={view.geometry.regions.length}
        markers={markerCount}
        past={past}
        noteMode={activeNoteMode}
      />
    </div>
  )
}
