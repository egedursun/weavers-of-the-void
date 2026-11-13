import { type LucideIcon } from 'lucide-react'
import { type StructureTypes } from '@/features/city/api'
import {
  DWELLING_ICON,
  buildingTypeKey,
  dwellingTypeKey,
} from '@/features/city/typeKeys'
import { type Cosmography } from '@/features/cosmography/api'
import {
  type CosmosView,
  type EntitySummary,
  type EntityTypeInfo,
  type WorldState,
} from '@/features/entity/api/types'
import { KIND_SPEC } from '@/features/entity/society/structureLabels'
import { type WorldKinds } from '@/features/madeKinds/api'
import { type MadeKind, kindKey } from '@/features/madeKinds/kindKeys'
import { COURSE, SLOT, VEHICLE_FAMILY } from '@/features/madeKinds/labels'
import { HOUSING } from '@/features/urban/labels'
import { FAMILY, unitIcon } from '@/features/wars/military/labels'
import { type AtlasSort } from './atlasSearch'

export type AtlasNodeKind =
  | 'group'
  | 'entity'
  | 'son'
  | 'creator'
  | 'world'
  | 'star'
  | 'foreign-god'
  | 'dimension'
  | 'cluster'
  | 'galaxy'
  | 'building-type'
  | 'dwelling-type'
  | 'made-type'

export type AtlasNode = {
  key: string
  label: string
  kind: AtlasNodeKind
  id?: number
  hint?: string
  entity?: EntitySummary
  typeKey?: string
  icon?: LucideIcon
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
  heavens?: Cosmography | undefined
  types: EntityTypeInfo[]
  buildings?: ReadonlyMap<number, StructureTypes>
  kinds?: ReadonlyMap<number, WorldKinds>
}

export const INSTANCE_TYPES: ReadonlySet<string> = new Set(['structure'])

function buildingTypes(
  worldId: number,
  found: StructureTypes | undefined
): AtlasNode[] {
  if (!found) return []
  const structures = found.structures
    .filter((row) => row.instances.length > 0)
    .map((row) => ({
      key: buildingTypeKey(worldId, row.kind),
      label: row.label,
      kind: 'building-type' as const,
      hint: `${row.instances.length} built`,
      icon: KIND_SPEC[row.kind].icon,
      children: [],
    }))
  const dwellings = found.dwellings
    .filter((row) => row.dwellings > 0)
    .map((row) => ({
      key: dwellingTypeKey(worldId, row.housing),
      label: HOUSING[row.housing].label,
      kind: 'dwelling-type' as const,
      hint: `${row.dwellings} homes`,
      icon: DWELLING_ICON,
      children: [],
    }))
  return [
    ...(structures.length
      ? [
          {
            key: `group:${worldId}:building-types`,
            label: 'Buildings by type',
            kind: 'group' as const,
            children: structures,
          },
        ]
      : []),
    ...(dwellings.length
      ? [
          {
            key: `group:${worldId}:dwelling-types`,
            label: 'Homes by type',
            kind: 'group' as const,
            children: dwellings,
          },
        ]
      : []),
  ]
}

function madeGroup(
  worldId: number,
  kind: MadeKind,
  label: string,
  children: AtlasNode[]
): AtlasNode[] {
  return children.length
    ? [
        {
          key: `group:${worldId}:made-${kind}`,
          label,
          kind: 'group' as const,
          children,
        },
      ]
    : []
}

function madeTypes(
  worldId: number,
  found: WorldKinds | undefined
): AtlasNode[] {
  if (!found) return []
  const node = (
    kind: MadeKind,
    id: number,
    label: string,
    hint: string,
    icon: AtlasNode['icon']
  ): AtlasNode => ({
    key: kindKey(kind, worldId, id),
    label,
    kind: 'made-type',
    hint,
    icon,
    children: [],
  })
  const groups = [
    ...madeGroup(
      worldId,
      'vehicle',
      'Vehicle types',
      found.vehicle_types.map((row) =>
        node(
          'vehicle',
          row.id,
          row.name,
          `${row.frame_label ?? 'Vehicle'} of ${row.origin?.name ?? 'no maker'}`,
          VEHICLE_FAMILY[row.family ?? 'cart'].icon
        )
      )
    ),
    ...madeGroup(
      worldId,
      'unit',
      'Kinds of soldier',
      found.unit_types.map((row) =>
        node(
          'unit',
          row.id,
          row.name,
          `${row.role_label} of ${row.origin?.name ?? 'no maker'}`,
          unitIcon(row.base_kind, FAMILY[row.family].icon)
        )
      )
    ),
    ...madeGroup(
      worldId,
      'equipment',
      'Equipment models',
      found.equipment_models.map((row) =>
        node(
          'equipment',
          row.id,
          row.name,
          `${row.family_label} of ${row.origin?.name ?? 'no maker'}`,
          SLOT[row.slot].icon
        )
      )
    ),
    ...madeGroup(
      worldId,
      'dish',
      'Dishes',
      found.dishes.map((row) =>
        node(
          'dish',
          row.id,
          row.name,
          `${COURSE[row.course].label} of ${row.origin?.name ?? 'no maker'}`,
          COURSE[row.course].icon
        )
      )
    ),
    ...madeGroup(
      worldId,
      'building',
      'Building types of the peoples',
      found.building_types.map((row) =>
        node(
          'building',
          row.id,
          row.name,
          `${row.kind_label} of ${row.origin?.name ?? 'no maker'}`,
          KIND_SPEC[row.base_kind].icon
        )
      )
    ),
  ]
  return groups.length
    ? [
        {
          key: `group:${worldId}:made-kinds`,
          label: 'Made kinds',
          kind: 'group' as const,
          children: groups,
        },
      ]
    : []
}

function humanizeKind(value: string): string {
  const text = value.replaceAll('_', ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function heavensTree(
  heavens: Cosmography,
  starNode: (starId: number) => AtlasNode | null,
  freeWorlds: Map<string, AtlasNode[]>
): { nodes: AtlasNode[]; placedStars: Set<number> } {
  const placedStars = new Set<number>()
  const galaxyNode = (galaxyId: number): AtlasNode | null => {
    const galaxy = heavens.galaxies.find((row) => row.id === galaxyId)
    if (!galaxy) return null
    const stars = heavens.stars
      .filter((star) => star.galaxy_id === galaxy.id)
      .map((star) => {
        placedStars.add(star.id)
        return starNode(star.id)
      })
      .filter((node): node is AtlasNode => node !== null)
    return {
      key: nodeKey('galaxy', galaxy.id),
      label: galaxy.name,
      kind: 'galaxy',
      id: galaxy.id,
      hint: `${humanizeKind(galaxy.galaxy_type)} galaxy`,
      children: [...stars, ...(freeWorlds.get(`galaxy:${galaxy.id}`) ?? [])],
    }
  }
  const clusterNode = (clusterId: number): AtlasNode | null => {
    const cluster = heavens.clusters.find((row) => row.id === clusterId)
    if (!cluster) return null
    const inner = heavens.clusters
      .filter((row) => row.parent_cluster_id === cluster.id)
      .map((row) => clusterNode(row.id))
    const galaxies = heavens.galaxies
      .filter((row) => row.cluster_id === cluster.id)
      .map((row) => galaxyNode(row.id))
    return {
      key: nodeKey('cluster', cluster.id),
      label: cluster.name,
      kind: 'cluster',
      id: cluster.id,
      hint: humanizeKind(cluster.cluster_kind),
      children: [...inner, ...galaxies].filter(
        (node): node is AtlasNode => node !== null
      ),
    }
  }
  const prime =
    heavens.dimensions.find((row) => row.dimension_kind === 'prime') ??
    heavens.dimensions[0]
  const nodes = heavens.dimensions.map((dimension) => {
    const home = (value: number | null) => (value ?? prime?.id) === dimension.id
    const clusters = heavens.clusters
      .filter((row) => row.parent_cluster_id === null && home(row.dimension_id))
      .map((row) => clusterNode(row.id))
    const loose = heavens.galaxies
      .filter((row) => row.cluster_id === null && home(row.dimension_id))
      .map((row) => galaxyNode(row.id))
    return {
      key: nodeKey('dimension', dimension.id),
      label: dimension.name,
      kind: 'dimension' as const,
      id: dimension.id,
      hint: `${humanizeKind(dimension.dimension_kind)} dimension`,
      children: [
        ...[...clusters, ...loose].filter(
          (node): node is AtlasNode => node !== null
        ),
        ...(freeWorlds.get(`dimension:${dimension.id}`) ?? []),
      ],
    }
  })
  return { nodes, placedStars }
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
  heavens,
  types,
  buildings,
  kinds,
}: TreeInput): AtlasNode[] {
  const byId = new Map(entities.map((entity) => [entity.id, entity]))
  const childrenOf = new Map<number, EntitySummary[]>()
  const rootsOf = new Map<number, EntitySummary[]>()
  for (const entity of entities) {
    if (INSTANCE_TYPES.has(entity.entity_type)) continue
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
        ...buildingTypes(worldId, buildings?.get(worldId)),
        ...madeTypes(worldId, kinds?.get(worldId)),
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
  const starOf = (starId: number): AtlasNode | null => {
    const star = stars.find((row) => row.id === starId)
    if (!star) return null
    return {
      key: nodeKey('star', star.id),
      label: star.name,
      kind: 'star',
      id: star.id,
      children: topWorlds
        .filter((item) => item.world.star_id === star.id)
        .map((item) =>
          worldNode(item.world.id, item.world.name, item.type_label)
        ),
    }
  }
  const starlessWorlds = topWorlds.filter(
    (item) =>
      item.world.star_id === null ||
      !stars.some((star) => star.id === item.world.star_id)
  )
  const placeOf = new Map(
    (heavens?.placements ?? []).map((row) => [row.world_id, row])
  )
  const freeWorlds = new Map<string, AtlasNode[]>()
  const unplaced: AtlasNode[] = []
  for (const item of starlessWorlds) {
    const node = worldNode(item.world.id, item.world.name, item.type_label)
    const place = placeOf.get(item.world.id)
    const slot =
      place?.galaxy_id != null
        ? `galaxy:${place.galaxy_id}`
        : place?.dimension_id != null
          ? `dimension:${place.dimension_id}`
          : null
    if (heavens && heavens.dimensions.length > 0 && slot)
      freeWorlds.set(slot, [...(freeWorlds.get(slot) ?? []), node])
    else unplaced.push(node)
  }
  const scale =
    heavens && heavens.dimensions.length > 0
      ? heavensTree(heavens, starOf, freeWorlds)
      : null
  const starNodes: AtlasNode[] = [
    ...(scale?.nodes ?? []),
    ...stars
      .filter((star) => !scale?.placedStars.has(star.id))
      .map((star) => starOf(star.id))
      .filter((node): node is AtlasNode => node !== null),
  ]
  const starless = unplaced
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

export function findNode(nodes: AtlasNode[], key: string): AtlasNode | null {
  for (const node of nodes) {
    if (node.key === key) return node
    const found = findNode(node.children, key)
    if (found) return found
  }
  return null
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
