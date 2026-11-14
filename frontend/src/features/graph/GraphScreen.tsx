import {
  type ComponentType,
  type ReactNode,
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  Activity,
  CalendarDays,
  ChevronDown,
  CircleDot,
  Crosshair,
  Link2,
  type LucideIcon,
  Maximize,
  RefreshCw,
  Route,
  Shapes,
  Waypoints,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, PageHeader } from '@/components/domain'
import { useThemeColors } from '@/components/domain/useThemeColors'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { useGlobalWorld, useWorldFilter } from '@/components/layout/worldFilter'
import { Muted } from '@/components/typography'
import {
  type CosmosView,
  ruleValue,
  useCatalogue,
  useCosmos,
  useRules,
} from '@/features/map/api'
import {
  isBoolean,
  isNumber,
  isStringList,
  oneOf,
  usePersistentState,
} from '@/features/map/usePersistentState'
import { Graph3DControls } from './Graph3DControls'
import { GraphCanvas2D, type GraphPointer } from './GraphCanvas2D'
import { type Graph3DCommand, type GraphCanvas3DProps } from './GraphCanvas3D'
import { GraphHoverOverlay } from './GraphHoverOverlay'
import { GraphLegend } from './GraphLegend'
import { GraphTimeSlider } from './GraphTimeSlider'
import { GraphToolbar } from './GraphToolbar'
import { NetworkHealthPanel } from './NetworkHealthPanel'
import { NodeInfoCard } from './NodeInfoCard'
import { PathFinder } from './PathFinder'
import {
  type FullGraph,
  type LinkGroup,
  type LinkGroupInfo,
  useGraph,
  usePath,
} from './api'
import { typeLabel } from './families'
import { type PositionMemory } from './graphForces'
import {
  type GraphMode,
  type GraphNode,
  GRAPH_MODES,
  drawerKindOf,
  buildGraph,
  defaultFocus,
  filterGraph,
  linkGroupIndex,
  linkKey,
  linkLabel,
} from './graphModel'
import { type GraphSearch } from './graphRouteSearch'
import { type Highlight } from './graphStyle'
import { webglAvailable } from './webgl'

const ITEM = navItem('network')
const STORAGE = {
  mode: 'aerona.graph.mode',
  radius: 'aerona.graph.radius',
  hidden: 'aerona.graph.hidden',
  group: 'aerona.graph.group',
  whole: 'aerona.graph.whole',
  cluster: 'aerona.graph.cluster',
  cap: 'aerona.graph.cap',
}
const FALLBACK = { cap: 10000, autoFocusLinks: 50 }
const DEFAULT_RADIUS = 2
const NO_3D_LIBRARY =
  "The 3D network library couldn't be loaded; switched back to the 2D view."
const NO_WEBGL =
  "WebGL isn't enabled in this browser; the 3D network couldn't be drawn, switched back to the 2D view."

let failed3D = false
const Unavailable3D: ComponentType<GraphCanvas3DProps> = () => null

const GraphCanvas3D = lazy<ComponentType<GraphCanvas3DProps>>(() =>
  import('./GraphCanvas3D').catch(() => {
    failed3D = true
    toast.error(NO_3D_LIBRARY)
    return { default: Unavailable3D }
  })
)

function Panel({
  title,
  icon: Icon,
  description,
  defaultOpen = false,
  children,
}: {
  title: string
  icon: LucideIcon
  description: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  return (
    <Card>
      <CardContent className='flex min-w-0 flex-col gap-3'>
        <Collapsible
          defaultOpen={defaultOpen}
          className='flex min-w-0 flex-col gap-3'
        >
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm' className='group justify-between'>
              <span className='flex min-w-0 items-center gap-2'>
                <Icon className='text-primary' />
                <span className='min-w-0 truncate'>{title}</span>
              </span>
              <ChevronDown className='transition-transform group-aria-expanded:rotate-180' />
            </Button>
          </CollapsibleTrigger>
          <Muted variant='caption'>{description}</Muted>
          <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
            {children}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  )
}

function currentEpoch(full: FullGraph): number {
  let epoch = 1
  for (const node of full.nodes) epoch = Math.max(epoch, node.epoch)
  for (const link of full.links) epoch = Math.max(epoch, link.epoch)
  return epoch
}

export function GraphScreen() {
  const graph = useGraph()
  const cosmos = useCosmos()
  const catalogue = useCatalogue()
  let body
  if (graph.isPending || cosmos.isPending || catalogue.isPending)
    body = (
      <div className='flex min-h-120 min-w-0 flex-1 flex-col gap-3'>
        <Skeleton className='h-8 w-full' />
        <Skeleton className='min-h-96 w-full flex-1' />
      </div>
    )
  else if (graph.error || cosmos.error || catalogue.error)
    body = (
      <Alert variant='destructive'>
        <AlertTitle>The network could not be drawn</AlertTitle>
        <AlertDescription className='flex flex-wrap items-center gap-3'>
          <span className='min-w-0 flex-1'>
            {(graph.error ?? cosmos.error ?? catalogue.error)?.message}
          </span>
          <Button
            size='sm'
            variant='outline'
            onClick={() =>
              void (graph.error
                ? graph.refetch()
                : cosmos.error
                  ? cosmos.refetch()
                  : catalogue.refetch())
            }
          >
            <RefreshCw />
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  else if (graph.data.nodes.length === 0)
    body = (
      <EmptyState
        icon={Waypoints}
        title='No bonds to draw yet'
        description='Records and the bonds between them form a graph as history unfolds.'
      />
    )
  else
    body = (
      <GraphView
        full={graph.data}
        cosmos={cosmos.data}
        linkGroups={catalogue.data.link_groups}
      />
    )
  return (
    <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4 p-4 md:p-6'>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      {body}
    </div>
  )
}

type GraphViewProps = {
  full: FullGraph
  cosmos: CosmosView
  linkGroups: readonly LinkGroupInfo[]
}

function GraphView({ full, cosmos, linkGroups }: GraphViewProps) {
  const search = useSearch({ strict: false }) as GraphSearch
  const globalWorld = useGlobalWorld()
  const setGlobalWorld = useWorldFilter((store) => store.setWorldId)
  const navigate = useNavigate()
  const drawer = useDrawerStack()
  const tokens = useThemeColors()
  const rules = useRules()
  const catalogue = useCatalogue()
  const [mode, setMode] = usePersistentState<GraphMode>(
    STORAGE.mode,
    '2d',
    oneOf(GRAPH_MODES)
  )
  const [radius, setRadius] = usePersistentState<number>(
    STORAGE.radius,
    DEFAULT_RADIUS,
    isNumber
  )
  const [hiddenList, setHiddenList] = usePersistentState<string[]>(
    STORAGE.hidden,
    [],
    isStringList
  )
  const [group, setGroup] = usePersistentState<LinkGroup>(
    STORAGE.group,
    'all',
    oneOf(linkGroups.map((item) => item.key))
  )
  const [capOverride, setCapOverride] = usePersistentState<number>(
    STORAGE.cap,
    0,
    isNumber
  )
  const [whole, setWhole] = usePersistentState<boolean>(
    STORAGE.whole,
    false,
    isBoolean
  )
  const [cluster, setCluster] = usePersistentState<boolean>(
    STORAGE.cluster,
    false,
    isBoolean
  )
  const [epoch, setEpoch] = useState<number | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [hover, setHover] = useState<{
    node: GraphNode
    pointer: GraphPointer
  } | null>(null)
  const [hoverFamily, setHoverFamily] = useState<string | null>(null)
  const [rotate, setRotate] = useState(false)
  const [command3D, setCommand3D] = useState<Graph3DCommand | null>(null)
  const [fitNonce, setFitNonce] = useState(0)
  const [frameWidth, setFrameWidth] = useState(0)
  const frameRef = useRef<HTMLDivElement>(null)
  const [positions, setPositions] = useState<PositionMemory>(() => new Map())
  const hiddenTypes = useMemo(() => new Set(hiddenList), [hiddenList])

  const setSearch = useCallback(
    (patch: Partial<GraphSearch>) =>
      navigate({
        to: '.',
        search: (previous: GraphSearch) => {
          const next: Record<string, unknown> = { ...previous, ...patch }
          for (const key of Object.keys(next))
            if (next[key] === undefined) delete next[key]
          return next
        },
      }),
    [navigate]
  )

  useEffect(() => {
    if (mode === '3d' && !webglAvailable()) {
      toast.error(NO_WEBGL)
      setMode('2d')
    }
  }, [mode, setMode])

  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const observer = new ResizeObserver(() =>
      setFrameWidth(frame.getBoundingClientRect().width)
    )
    observer.observe(frame)
    return () => observer.disconnect()
  }, [])

  const worlds = useMemo(
    () =>
      cosmos.worlds.map((item) => ({
        id: item.world.id,
        name: item.world.name,
        createdEpoch: item.world.created_epoch,
      })),
    [cosmos.worlds]
  )
  const routes = useMemo(
    () =>
      cosmos.routes.map((route) => ({
        id: route.id,
        first: route.world_a_id,
        second: route.world_b_id,
        active: route.active,
        epoch: route.created_epoch,
        description: route.description ?? null,
      })),
    [cosmos.routes]
  )
  const groupIndex = useMemo(() => linkGroupIndex(linkGroups), [linkGroups])
  const built = useMemo(
    () => buildGraph(full, worlds, routes, groupIndex),
    [full, worlds, routes, groupIndex]
  )
  const current = useMemo(() => currentEpoch(full), [full])
  const typeLabels = useMemo(
    () =>
      new Map(
        (catalogue.data?.entity_types ?? []).map((item) => [
          item.key,
          item.label,
        ])
      ),
    [catalogue.data]
  )
  const bondLabels = useMemo(
    () =>
      new Map(
        (catalogue.data?.bond_kinds ?? []).map((item) => [item.key, item.label])
      ),
    [catalogue.data]
  )
  const ruleCap = ruleValue(
    rules.data,
    'ui',
    'graph_focus_node_cap',
    FALLBACK.cap
  )
  const cap = capOverride > 0 ? capOverride : ruleCap
  const autoLinks = ruleValue(
    rules.data,
    'ui',
    'graph_auto_focus_max_links',
    FALLBACK.autoFocusLinks
  )

  const nodeIds = useMemo(
    () => new Set(built.nodes.map((node) => node.id)),
    [built]
  )
  const explicitFocus =
    search.focus !== undefined && nodeIds.has(search.focus)
      ? search.focus
      : null
  const automatic = useMemo(
    () => defaultFocus(built, hiddenTypes, autoLinks),
    [built, hiddenTypes, autoLinks]
  )
  const focusId = explicitFocus ?? (whole ? null : automatic)

  const [layoutFocus, setLayoutFocus] = useState(focusId)
  if (layoutFocus !== focusId) {
    setLayoutFocus(focusId)
    setPositions(new Map())
  }

  const filtered = useMemo(
    () =>
      filterGraph(built, {
        group,
        epoch,
        hiddenTypes,
        worldId: search.world ?? globalWorld,
        focusId,
        radius,
        cap,
      }),
    [
      built,
      group,
      epoch,
      hiddenTypes,
      search.world,
      globalWorld,
      focusId,
      radius,
      cap,
    ]
  )

  const from = search.from ?? null
  const to = search.to ?? null
  const path = usePath(from, to)
  const pathData = from !== null && to !== null ? path.data : undefined
  const { pathNodes, pathLinks } = useMemo(() => {
    const nodes = new Set<number>()
    const links = new Set<string>()
    if (pathData?.found) {
      pathData.path.forEach((id) => nodes.add(id))
      for (const step of pathData.steps) {
        const kind = step.kind === 'in world' ? 'in_world' : step.kind
        links.add(linkKey(step.source, step.target, kind))
        links.add(linkKey(step.target, step.source, kind))
      }
    }
    return { pathNodes: nodes, pathLinks: links }
  }, [pathData])

  const hoverNeighbours = useMemo(() => {
    const found = new Set<number>()
    if (!hover) return found
    for (const link of filtered.links) {
      if (link.source === hover.node.id) found.add(link.target)
      if (link.target === hover.node.id) found.add(link.source)
    }
    return found
  }, [hover, filtered.links])

  const highlight: Highlight = useMemo(
    () => ({
      hoverId: hover?.node.id ?? null,
      hoverNeighbours,
      pathNodes,
      pathLinks,
      family: hoverFamily,
      selectedId,
      focusId,
    }),
    [
      hover,
      hoverNeighbours,
      pathNodes,
      pathLinks,
      hoverFamily,
      selectedId,
      focusId,
    ]
  )

  const linkLabels = useMemo(
    () =>
      new Map(
        filtered.links.map((link) => [link.key, linkLabel(link, bondLabels)])
      ),
    [filtered.links, bondLabels]
  )
  const pickable = useMemo(
    () =>
      built.nodes.map((node) => ({
        id: node.id,
        name: node.name,
        kind: node.kind,
      })),
    [built]
  )
  const selected = filtered.nodes.find((node) => node.id === selectedId) ?? null
  const ties = useMemo(() => {
    if (!selected) return []
    const byId = new Map(filtered.nodes.map((node) => [node.id, node]))
    return filtered.links.flatMap((link) => {
      const other =
        link.source === selected.id
          ? link.target
          : link.target === selected.id
            ? link.source
            : null
      const node = other !== null ? byId.get(other) : undefined
      return node
        ? [{ id: node.id, name: node.name, label: linkLabel(link, bondLabels) }]
        : []
    })
  }, [selected, filtered.nodes, filtered.links, bondLabels])
  const focusNode = built.nodes.find((node) => node.id === focusId) ?? null

  const openNode = (node: GraphNode) => {
    const kind = drawerKindOf(node.kind)
    if (!kind) return
    drawer.open(kind === 'creator' ? { kind } : { kind, id: String(node.id) })
  }
  const setPath = (first: number | null, second: number | null) =>
    setSearch({ from: first ?? undefined, to: second ?? undefined })
  const focusOn = (node: GraphNode) => {
    setWhole(false)
    setSearch({ focus: node.id })
  }
  const pathTo = (node: GraphNode) => {
    if (selectedId === null || selectedId === node.id) {
      setSelectedId(node.id)
      return
    }
    setPath(selectedId, node.id)
  }

  const canvasProps = {
    graph: filtered,
    tokens,
    highlight,
    positions,
    cluster: cluster && worlds.length > 1,
    focused: focusId !== null,
    label: `Knowledge network with ${plural(filtered.nodes.length, 'record', 'records')} and ${plural(filtered.links.length, 'link', 'links')}.`,
    onSelect: (node: GraphNode | null) => {
      if (node === null && pathNodes.size > 0) return
      setSelectedId(node?.id ?? null)
    },
    onOpen: openNode,
    onPathTo: pathTo,
    onFocus: focusOn,
    onHover: (node: GraphNode | null, pointer: GraphPointer) =>
      setHover(node ? { node, pointer } : null),
  }

  return (
    <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4'>
      <GraphToolbar
        groups={linkGroups}
        mode={mode}
        onMode={(next) => {
          if (next === '3d' && failed3D) {
            toast.error(NO_3D_LIBRARY)
            return
          }
          setMode(next)
        }}
        findable={pickable}
        onFind={(id) => {
          setWhole(false)
          setSearch({ focus: id })
          setSelectedId(id)
        }}
        group={group}
        onGroup={setGroup}
        radius={radius}
        onRadius={setRadius}
        shownRadius={filtered.radius}
        reduced={filtered.reduced}
        cap={cap}
        ruleCap={ruleCap}
        capOverridden={capOverride > 0}
        total={built.nodes.length}
        onCap={(next) => setCapOverride(next ?? 0)}
        worlds={worlds}
        worldId={search.world ?? globalWorld}
        onWorld={(id) => {
          setGlobalWorld(id)
          setSearch({ world: id ?? undefined })
        }}
        cluster={cluster}
        onCluster={(on) => {
          setPositions(new Map())
          setCluster(on)
        }}
        focusName={focusNode?.name ?? null}
        automaticFocus={explicitFocus === null}
        whole={whole && explicitFocus === null}
        onWhole={(next) => {
          setWhole(next)
          if (next) setSearch({ focus: undefined })
        }}
      />
      {mode === '3d' && (
        <Graph3DControls
          rotate={rotate}
          onRotate={setRotate}
          onFit={() => setCommand3D({ kind: 'fit', nonce: Date.now() })}
          onRelayout={() => {
            setPositions(new Map())
            setCommand3D({ kind: 'relayout', nonce: Date.now() })
          }}
        />
      )}
      <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-4'>
        <MiniStat
          icon={CircleDot}
          tone='info'
          label={
            focusId === null
              ? 'Records shown'
              : `Within ${filtered.radius} ${filtered.radius === 1 ? 'step' : 'steps'}`
          }
          value={`${formatInteger(filtered.nodes.length)} / ${formatInteger(built.nodes.length)}`}
        />
        <MiniStat
          icon={Link2}
          tone='verdigris'
          label='Bonds shown'
          value={formatInteger(filtered.links.length)}
        />
        <MiniStat
          icon={Crosshair}
          tone='gold'
          label={whole && explicitFocus === null ? 'Whole network' : 'Focus'}
          value={
            whole && explicitFocus === null ? 'All' : (focusNode?.name ?? '—')
          }
        />
        <MiniStat
          icon={CalendarDays}
          label={
            epoch !== null && epoch < current ? 'Looking back to' : 'Today'
          }
          value={`Epoch ${epoch ?? current}`}
        />
      </div>
      <GraphTimeSlider current={current} shown={epoch} onShow={setEpoch} />
      <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-4 lg:flex-row'>
        <div
          ref={frameRef}
          data-graph-frame
          className='relative min-h-120 min-w-0 flex-1 overflow-hidden rounded-lg border md:min-h-160'
        >
          {mode === '2d' ? (
            <GraphCanvas2D
              {...canvasProps}
              linkLabels={linkLabels}
              fitNonce={fitNonce}
            />
          ) : (
            <Suspense fallback={<Skeleton className='absolute inset-0' />}>
              <GraphCanvas3D
                {...canvasProps}
                rotate={rotate}
                command={command3D}
              />
            </Suspense>
          )}
          {mode === '2d' && (
            <div className='absolute top-3 left-3'>
              <Button
                size='sm'
                variant='outline'
                onClick={() => setFitNonce((value) => value + 1)}
              >
                <Maximize />
                Fit
              </Button>
            </div>
          )}
          {hover && (
            <GraphHoverOverlay
              node={hover.node}
              kindLabel={typeLabel(hover.node.type, typeLabels)}
              links={filtered.degree.get(hover.node.id) ?? 0}
              x={hover.pointer.x}
              y={hover.pointer.y}
              width={frameWidth}
            />
          )}
        </div>
        <aside className='flex min-w-0 flex-col gap-4 lg:w-80 lg:shrink-0'>
          {selected && (
            <NodeInfoCard
              node={selected}
              ties={ties}
              onSelect={setSelectedId}
              visibleLinks={filtered.degree.get(selected.id) ?? 0}
              typeLabels={typeLabels}
              nodes={pickable}
              onClose={() => setSelectedId(null)}
              onFocus={focusOn}
              onPathTo={(id) => setPath(selected.id, id)}
              pathTarget={from === selected.id ? to : null}
            />
          )}
          <Panel
            title='How are they connected?'
            icon={Route}
            description='Find the shortest chain of bonds between two records.'
            defaultOpen={from !== null || to !== null}
          >
            <PathFinder
              nodes={pickable}
              from={from}
              to={to}
              onChange={setPath}
              linkLabels={bondLabels}
            />
          </Panel>
          <Panel
            title='Families and types'
            icon={Shapes}
            description='Show or hide families; hover one to light it up.'
            defaultOpen
          >
            <GraphLegend
              nodes={built.nodes}
              hiddenTypes={hiddenTypes}
              onHiddenTypes={(next) => setHiddenList([...next])}
              onHoverFamily={setHoverFamily}
              typeLabels={typeLabels}
            />
          </Panel>
          <Panel
            title='Connectivity'
            icon={Activity}
            description='Islands, lonely records and the repairs Fate can make.'
            defaultOpen
          >
            <NetworkHealthPanel />
          </Panel>
        </aside>
      </div>
    </div>
  )
}
