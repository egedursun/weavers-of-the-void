import { useCallback, useMemo } from 'react'
import { getRouteApi } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import { BookOpen, ChevronsDownUp, ChevronsUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { OrnateFrame } from '@/components/ui/ornate'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, PageHeader } from '@/components/domain'
import {
  type DrawerEntry,
  parseDrawerStack,
  pushDrawerEntry,
  serializeDrawerStack,
} from '@/components/layout/drawer/drawerEntries'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { useGlobalWorld } from '@/components/layout/worldFilter'
import { Text } from '@/components/typography'
import { useWorldsStructureTypes } from '@/features/city/api'
import { useCosmography } from '@/features/cosmography/api'
import {
  useAllEntities,
  useCatalogue,
  useCosmos,
  useWorldState,
} from '@/features/entity/api/queries'
import { type EntitySummary } from '@/features/entity/api/types'
import { useHealth } from '@/features/images/api'
import { useImageGenEvents } from '@/features/images/imageGenState'
import { AtlasDetail } from './AtlasDetail'
import { AtlasFilters } from './AtlasFilters'
import { AtlasList } from './AtlasList'
import { AtlasTree } from './AtlasTree'
import { TypeChips } from './TypeChips'
import {
  type AtlasFilters as Filters,
  type AtlasNode,
  INSTANCE_TYPES,
  VISIBLE_STATUS,
  allKeys,
  buildAtlasTree,
  drawerFor,
  findNode,
  isFiltering,
  matchesEntity,
  pruneTree,
  sortList,
} from './atlasModel'
import { type AtlasSearch } from './atlasSearch'
import { useOpenBranches } from './useOpenBranches'

const ITEM = navItem('atlas')
const route = getRouteApi('/_app/atlas')
const ALL_STATUSES = 'all'

export function AtlasScreen() {
  useImageGenEvents()
  const search = route.useSearch()
  const navigate = route.useNavigate()
  const drawers = useDrawerStack()
  const catalogue = useCatalogue()
  const state = useWorldState()
  const cosmos = useCosmos()
  const heavens = useCosmography()
  const health = useHealth()
  const entities = useAllEntities(ALL_STATUSES, !search.history)
  const globalWorld = useGlobalWorld()
  const branches = useOpenBranches()
  const change = useCallback(
    (patch: Partial<AtlasSearch>) =>
      void navigate({
        search: (previous) => ({ ...previous, ...patch }),
        replace: true,
      }),
    [navigate]
  )
  const filters: Filters = useMemo(
    () => ({
      q: search.q ?? '',
      type: search.type ?? null,
      status: search.status ?? VISIBLE_STATUS,
      favorites: search.favorites ?? false,
      world: search.world ?? globalWorld,
    }),
    [
      search.q,
      search.type,
      search.status,
      search.favorites,
      search.world,
      globalWorld,
    ]
  )
  const types = useMemo(
    () =>
      (catalogue.data?.entity_types ?? []).filter(
        (type) => !INSTANCE_TYPES.has(type.key)
      ),
    [catalogue.data]
  )
  const all = useMemo(
    () =>
      (entities.data ?? []).filter(
        (entity) => !INSTANCE_TYPES.has(entity.entity_type)
      ),
    [entities.data]
  )
  const worldIds = useMemo(
    () => (cosmos.data?.worlds ?? []).map((item) => item.world.id),
    [cosmos.data]
  )
  const buildings = useWorldsStructureTypes(worldIds)
  const matching = useMemo(
    () => all.filter((entity) => matchesEntity(entity, filters)),
    [all, filters]
  )
  const typeCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const entity of all)
      if (matchesEntity(entity, { ...filters, type: null }))
        counts.set(
          entity.entity_type,
          (counts.get(entity.entity_type) ?? 0) + 1
        )
    return counts
  }, [all, filters])
  const tree = useMemo(
    () =>
      buildAtlasTree({
        entities: all,
        state: state.data,
        cosmos: cosmos.data,
        heavens: heavens.data,
        types,
        buildings,
      }),
    [all, state.data, cosmos.data, heavens.data, types, buildings]
  )
  const filtering = isFiltering(filters)
  const matchIds = useMemo(
    () => new Set(matching.map((entity) => entity.id)),
    [matching]
  )
  const shownTree = useMemo(() => {
    if (!filtering) return tree
    const needle = filters.q.trim().toLowerCase()
    const onlyEntities =
      Boolean(filters.type) ||
      filters.favorites ||
      filters.status !== VISIBLE_STATUS
    return pruneTree(tree, (node: AtlasNode) =>
      node.kind === 'entity'
        ? node.id !== undefined && matchIds.has(node.id)
        : !onlyEntities &&
          needle !== '' &&
          node.label.toLowerCase().includes(needle)
    )
  }, [tree, filtering, filters, matchIds])
  const open = useMemo(
    () =>
      filtering
        ? new Set([...branches.open, ...allKeys(shownTree)])
        : branches.open,
    [filtering, branches.open, shownTree]
  )
  const view = search.view ?? 'tree'
  const sorted = useMemo(
    () => sortList(matching, search.sort ?? 'name', search.desc ?? false),
    [matching, search.sort, search.desc]
  )
  const byId = useMemo(
    () => new Map(all.map((entity) => [entity.id, entity])),
    [all]
  )
  const selected = search.select ?? null
  const selectedNode = selected ? findNode(tree, selected) : null
  const selectedGroup = selectedNode?.kind === 'group' ? selectedNode : null
  const show = (key: string, entry: DrawerEntry | null) =>
    void navigate({
      search: (previous) => ({
        ...previous,
        select: key,
        drawer: entry
          ? serializeDrawerStack(
              pushDrawerEntry(parseDrawerStack(previous.drawer), entry)
            )
          : previous.drawer,
      }),
      replace: true,
    })
  const pick = (key: string) => {
    const node = findNode(tree, key)
    show(key, node ? drawerFor(node) : null)
  }
  const activate = (node: AtlasNode) => {
    const entry = drawerFor(node)
    if (entry) drawers.open(entry)
    else if (node.children.length)
      branches.toggle(node.key, !open.has(node.key))
  }
  const typeLabel = (key: string) =>
    types.find((item) => item.key === key)?.label ?? key
  const empty = entities.isSuccess && all.length === 0
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
          view === 'tree' && !empty ? (
            <>
              <Button
                variant='outline'
                size='sm'
                onClick={() => branches.openAll(allKeys(tree))}
              >
                <ChevronsUpDown />
                Open all
              </Button>
              <Button variant='outline' size='sm' onClick={branches.closeAll}>
                <ChevronsDownUp />
                Close all
              </Button>
            </>
          ) : undefined
        }
      />
      {entities.isError && (
        <Text tone='destructive'>{entities.error.message}</Text>
      )}
      {empty ? (
        <EmptyState
          icon={BookOpen}
          title='The atlas is empty'
          description='Every place, people, legend and law the world creates is recorded here.'
        />
      ) : (
        <div className='@container/atlas min-w-0'>
          <div className='grid min-w-0 grid-cols-1 gap-6 @3xl/atlas:grid-cols-5'>
            <aside
              aria-label='Atlas index'
              className='@container/pane flex min-w-0 flex-col @3xl/atlas:col-span-2'
            >
              <OrnateFrame
                frame='card'
                crest
                className='flex min-w-0 flex-col gap-4 px-5 py-6'
              >
                <TypeChips
                  types={types}
                  counts={typeCounts}
                  active={search.type ?? null}
                  onPick={(type) =>
                    change({ type: type ?? undefined, page: undefined })
                  }
                />
                <AtlasFilters
                  search={search}
                  onChange={change}
                  types={types}
                  typeCounts={typeCounts}
                  matches={matching.length}
                  view={view}
                />
                {entities.isPending ? (
                  <div className='flex flex-col gap-2'>
                    <Skeleton className='h-control-sm w-full' />
                    <Skeleton className='h-control-sm w-5/6' />
                    <Skeleton className='h-control-sm w-4/6' />
                  </div>
                ) : view === 'tree' ? (
                  <AtlasTree
                    nodes={shownTree}
                    open={open}
                    onToggle={branches.toggle}
                    selected={selected}
                    onSelect={(node) => show(node.key, drawerFor(node))}
                    onActivate={activate}
                    query={filters.q}
                    imageWorkerOn={
                      health.data?.image_worker_configured ?? false
                    }
                  />
                ) : (
                  <AtlasList
                    items={sorted}
                    sort={search.sort ?? 'name'}
                    descending={search.desc ?? false}
                    onSort={(sort) =>
                      change(
                        sort === (search.sort ?? 'name')
                          ? { desc: search.desc ? undefined : true }
                          : { sort, desc: undefined }
                      )
                    }
                    page={search.page ?? 1}
                    onPage={(page) =>
                      change({ page: page > 1 ? page : undefined })
                    }
                    selected={
                      selected?.startsWith('entity:')
                        ? Number(selected.slice('entity:'.length))
                        : null
                    }
                    onSelect={(entity: EntitySummary) =>
                      show(`entity:${entity.id}`, {
                        kind: 'entity',
                        id: String(entity.id),
                      })
                    }
                    typeLabel={typeLabel}
                    locationName={(id) =>
                      id !== null ? (byId.get(id)?.name ?? null) : null
                    }
                    query={filters.q}
                  />
                )}
                {entities.isSuccess && matching.length === 0 && filtering && (
                  <EmptyState
                    size='compact'
                    icon={BookOpen}
                    title='Nothing matches'
                    description='Loosen the search or the filters.'
                  />
                )}
              </OrnateFrame>
            </aside>
            <section
              aria-label='Record'
              className='@container/pane flex min-w-0 flex-col gap-6 @3xl/atlas:col-span-3'
            >
              <AtlasDetail
                selection={selected}
                group={selectedGroup}
                records={all.length}
                kinds={typeCounts.size}
                onSelect={pick}
              />
            </section>
          </div>
        </div>
      )}
    </>
  )
}
