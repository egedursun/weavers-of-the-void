import {
  type CosmosView,
  type EntitySummary,
  type EntityTypeInfo,
  type WorldState,
} from '@/features/entity/api/types'
import { type AtlasSort } from './atlasSearch'

export type AtlasNodeKind =
  'group' | 'entity' | 'son' | 'creator' | 'world' | 'star' | 'foreign-god'

export type AtlasNode = {
  key: string
  label: string
  kind: AtlasNodeKind
  id?: number
  hint?: string
  entity?: EntitySummary
  typeKey?: string
  children: AtlasNode[]
}

export type AtlasFilters = {
  q: string
  type: string | null
  status: string
  favorites: boolean
  world?: number | null
}

export const VISIBLE_STATUS = 'visible'
const VISIBLE = new Set(['canon', 'dead', 'destroyed', 'fulfilled'])

export function matchesEntity(
  entity: EntitySummary,
  filters: AtlasFilters
): boolean {
  if (filters.type && entity.entity_type !== filters.type) return false
  if (filters.world && entity.world_id !== filters.world) return false
  if (
    filters.status === VISIBLE_STATUS
      ? !VISIBLE.has(entity.status)
      : entity.status !== filters.status
  )
    return false
  if (filters.favorites && !entity.favorite) return false
  const needle = filters.q.trim().toLowerCase()
  if (!needle) return true
  return [entity.name, entity.title ?? '', entity.subtype ?? ''].some((text) =>
    text.toLowerCase().includes(needle)
  )
}

export function isFiltering(filters: AtlasFilters): boolean {
  return Boolean(
    filters.q.trim() ||
    filters.type ||
    filters.favorites ||
    filters.world ||
    filters.status !== VISIBLE_STATUS
  )
}

export function nodeKey(kind: AtlasNodeKind, id: number | string): string {
  return `${kind}:${id}`
}

function sortEntities(items: EntitySummary[]): EntitySummary[] {
  return [...items].sort((left, right) => left.name.localeCompare(right.name))
}

function locationTree(
  roots: EntitySummary[],
  childrenOf: Map<number, EntitySummary[]>,
  seen: Set<number>
): AtlasNode[] {
  return sortEntities(roots)
    .filter((entity) => !seen.has(entity.id))
    .map((entity) => {
      seen.add(entity.id)
      return {
        key: nodeKey('entity', entity.id),
        label: entity.name,
        kind: 'entity' as const,
        id: entity.id,
        hint: entity.subtype ?? undefined,
        entity,
        children: locationTree(
          childrenOf.get(entity.id) ?? [],
          childrenOf,
          seen
        ),
      }
    })
}

type TreeInput = {
  entities: EntitySummary[]
  state: WorldState | undefined
  cosmos: CosmosView | undefined
  types: EntityTypeInfo[]
}

function pantheon(state: WorldState | undefined): AtlasNode | null {
  if (!state?.creator) return null
  const sons = state.sons.map((view) => view.son)
  const byParent = new Map<number | null, typeof sons>()
  for (const son of sons) {
    const parent = sons.some((other) => other.id === son.parent_son_id)
      ? son.parent_son_id
      : null
    byParent.set(parent, [...(byParent.get(parent) ?? []), son])
  }
  const branch = (parent: number | null): AtlasNode[] =>
    (byParent.get(parent) ?? []).map((son) => ({
      key: nodeKey('son', son.id),
      label: son.name,
      kind: 'son' as const,
      id: son.id,
      hint: son.title,
      children: branch(son.id),
    }))
  return {
    key: 'group:pantheon',
    label: 'Pantheon',
    kind: 'group',
    children: [
      {
        key: nodeKey('creator', state.creator.id),
        label: state.creator.name,
        kind: 'creator',
        id: state.creator.id,
        hint: state.creator.title ?? 'The Creator',
        children: branch(null),
      },
    ],
  }
}

export function buildAtlasTree({
  entities,
  state,
  cosmos,
  types,
}: TreeInput): AtlasNode[] {
  const byId = new Map(entities.map((entity) => [entity.id, entity]))
  const childrenOf = new Map<number, EntitySummary[]>()
  const rootsOf = new Map<number, EntitySummary[]>()
  for (const entity of entities) {
    if (entity.location_id !== null && byId.has(entity.location_id)) {
      childrenOf.set(entity.location_id, [
        ...(childrenOf.get(entity.location_id) ?? []),
        entity,
      ])
    } else {
      rootsOf.set(entity.world_id, [
        ...(rootsOf.get(entity.world_id) ?? []),
        entity,
      ])
    }
  }
  const typeLabel = (key: string) =>
    types.find((item) => item.key === key)?.plural ?? key
  const worldNode = (
    worldId: number,
    name: string,
    hint?: string
  ): AtlasNode => {
    const seen = new Set<number>()
    const roots = rootsOf.get(worldId) ?? []
    const places = roots.filter(
      (entity) =>
        entity.entity_type === 'region' ||
        entity.entity_type === 'place' ||
        childrenOf.has(entity.id)
    )
    const loose = roots.filter((entity) => !places.includes(entity))
    const groups = new Map<string, EntitySummary[]>()
    for (const entity of loose)
      groups.set(entity.entity_type, [
        ...(groups.get(entity.entity_type) ?? []),
        entity,
      ])
    const gods = (cosmos?.foreign_gods ?? [])
      .filter((god) => god.world_id === worldId)
      .map((god) => ({
        key: nodeKey('foreign-god', god.id),
        label: god.name,
        kind: 'foreign-god' as const,
        id: god.id,
        hint: god.title ?? 'Old god',
        children: [],
      }))
    const moons = (cosmos?.worlds ?? [])
      .filter((item) => item.world.parent_world_id === worldId)
      .map((item) => worldNode(item.world.id, item.world.name, item.type_label))
    return {
      key: nodeKey('world', worldId),
      label: name,
      kind: 'world',
      id: worldId,
      hint,
      children: [
        ...moons,
        ...locationTree(places, childrenOf, seen),
        ...[...groups.entries()]
          .sort(([left], [right]) =>
            typeLabel(left).localeCompare(typeLabel(right))
          )
          .map(([type, items]) => ({
            key: `group:${worldId}:${type}`,
            label: typeLabel(type),
            kind: 'group' as const,
            typeKey: type,
            children: locationTree(items, childrenOf, seen),
          })),
        ...(gods.length
          ? [
              {
                key: `group:${worldId}:gods`,
                label: 'Old and foreign gods',
                kind: 'group' as const,
                children: gods,
              },
            ]
          : []),
      ],
    }
  }
  const worlds = cosmos?.worlds ?? []
  const stars = cosmos?.stars ?? []
  const topWorlds = worlds.filter((item) => item.world.parent_world_id === null)
  const starNodes: AtlasNode[] = stars.map((star) => ({
    key: nodeKey('star', star.id),
    label: star.name,
    kind: 'star',
    id: star.id,
    children: topWorlds
      .filter((item) => item.world.star_id === star.id)
      .map((item) =>
        worldNode(item.world.id, item.world.name, item.type_label)
      ),
  }))
  const starless = topWorlds
    .filter(
      (item) =>
        item.world.star_id === null ||
        !stars.some((star) => star.id === item.world.star_id)
    )
    .map((item) => worldNode(item.world.id, item.world.name, item.type_label))
  const knownWorlds = new Set(worlds.map((item) => item.world.id))
  const orphans = [...rootsOf.keys()]
    .filter((worldId) => !knownWorlds.has(worldId))
    .map((worldId) =>
      worldNode(
        worldId,
        state?.worlds.find((world) => world.id === worldId)?.name ??
          `World ${worldId}`
      )
    )
  const top = pantheon(state)
  return [
    ...(top ? [top] : []),
    {
      key: 'group:cosmos',
      label: 'Cosmos',
      kind: 'group',
      children: [...starNodes, ...starless, ...orphans],
    },
  ]
}

export function pruneTree(
  nodes: AtlasNode[],
  keep: (node: AtlasNode) => boolean
): AtlasNode[] {
  const result: AtlasNode[] = []
  for (const node of nodes) {
    const children = pruneTree(node.children, keep)
    if (children.length > 0 || (node.kind !== 'group' && keep(node)))
      result.push({ ...node, children })
  }
  return result
}

export function countLeaves(node: AtlasNode): number {
  if (node.children.length === 0) return node.kind === 'group' ? 0 : 1
  return node.children.reduce(
    (sum, child) => sum + countLeaves(child),
    node.kind === 'group' ? 0 : 1
  )
}

export function flattenVisible(
  nodes: AtlasNode[],
  open: ReadonlySet<string>,
  depth = 0
): { node: AtlasNode; depth: number; parent: string | null }[] {
  const rows: { node: AtlasNode; depth: number; parent: string | null }[] = []
  const walk = (items: AtlasNode[], level: number, parent: string | null) => {
    for (const node of items) {
      rows.push({ node, depth: level, parent })
      if (node.children.length && open.has(node.key))
        walk(node.children, level + 1, node.key)
    }
  }
  walk(nodes, depth, null)
  return rows
}

export function allKeys(nodes: AtlasNode[]): string[] {
  return nodes.flatMap((node) =>
    node.children.length ? [node.key, ...allKeys(node.children)] : []
  )
}

export function sortList(
  items: EntitySummary[],
  sort: AtlasSort,
  descending: boolean
): EntitySummary[] {
  const value = (entity: EntitySummary): string | number => {
    switch (sort) {
      case 'type':
        return entity.entity_type
      case 'epoch':
        return entity.birth_epoch
      case 'power':
        return entity.power_level
      case 'importance':
        return entity.importance ?? 0
      default:
        return entity.name.toLowerCase()
    }
  }
  const sorted = [...items].sort((left, right) => {
    const a = value(left)
    const b = value(right)
    const order =
      typeof a === 'number' && typeof b === 'number'
        ? a - b
        : String(a).localeCompare(String(b))
    return order !== 0 ? order : left.name.localeCompare(right.name)
  })
  return descending ? sorted.reverse() : sorted
}

export const DEFAULT_OPEN = ['group:pantheon', 'group:cosmos']
