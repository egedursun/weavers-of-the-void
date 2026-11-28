import { type FullGraph, type LinkGroup, type LinkGroupInfo } from './api'
import { type Family, familyOf } from './families'

export const INSIDE = 'inside'
export const IN_WORLD = 'in_world'
export const ROUTE = 'route'
export const CREATED = 'created'

export type GraphNode = {
  id: number
  kind: string
  name: string
  type: string
  size: number
  epoch: number
  status: string
  worldId: number | null
  locationId: number | null
  family: Family
}

export type GraphLink = {
  key: string
  source: number
  target: number
  kind: string
  epoch: number
  past: boolean
  open: boolean
  description: string | null
  groups: readonly LinkGroup[]
}

export type Graph = { nodes: GraphNode[]; links: GraphLink[] }

export type WorldInfo = { id: number; name: string; createdEpoch: number }
export type RouteInfo = {
  id: number
  first: number
  second: number
  active: boolean
  epoch: number
  description: string | null
}

export type LinkGroupIndex = ReadonlyMap<string, readonly LinkGroup[]>

export function linkGroupIndex(
  groups: readonly LinkGroupInfo[]
): LinkGroupIndex {
  const index = new Map<string, LinkGroup[]>()
  for (const group of groups)
    for (const kind of group.kinds)
      index.set(kind, [...(index.get(kind) ?? []), group.key as LinkGroup])
  return index
}

export type LinkTone = 'route' | 'inside' | 'conflict' | 'faith' | 'other'

export function linkTone(link: GraphLink): LinkTone {
  if (link.kind === ROUTE || link.kind === IN_WORLD) return 'route'
  if (link.kind === INSIDE) return 'inside'
  if (link.groups.includes('conflict')) return 'conflict'
  if (link.groups.includes('faith')) return 'faith'
  return 'other'
}

export function inGroup(link: GraphLink, group: LinkGroup): boolean {
  return link.groups.includes(group)
}

export function linkKey(source: number, target: number, kind: string): string {
  return `${source}-${target}-${kind}`
}

const ROOT_TYPES = new Set(['region', 'place'])
const WORLD_SIZE = 9

export function buildGraph(
  full: FullGraph,
  worlds: readonly WorldInfo[],
  routes: readonly RouteInfo[],
  groupIndex: LinkGroupIndex
): Graph {
  const nodes: GraphNode[] = full.nodes.map((node) => ({
    id: node.id,
    kind: node.kind,
    name: node.name,
    type: node.type,
    size: node.size,
    epoch: node.epoch,
    status: node.status,
    worldId: node.world_id ?? null,
    locationId: node.location_id ?? null,
    family: familyOf(node.type),
  }))
  const links: GraphLink[] = full.links.map((link) => ({
    key: linkKey(link.source, link.target, link.kind),
    source: link.source,
    target: link.target,
    kind: link.kind,
    epoch: link.epoch,
    past: link.past,
    open: true,
    description: null,
    groups: groupIndex.get(link.kind) ?? [],
  }))
  const present = new Set(nodes.map((node) => node.id))
  for (const node of full.nodes) {
    if (node.creator_son_id && present.has(node.creator_son_id))
      links.push({
        key: linkKey(node.creator_son_id, node.id, CREATED),
        source: node.creator_son_id,
        target: node.id,
        kind: CREATED,
        groups: groupIndex.get(CREATED) ?? [],
        epoch: node.epoch,
        past: false,
        open: true,
        description: null,
      })
  }
  if (worlds.length > 1) {
    for (const world of worlds) {
      if (present.has(world.id)) continue
      present.add(world.id)
      nodes.push({
        id: world.id,
        kind: 'world',
        name: world.name,
        type: 'world',
        size: WORLD_SIZE,
        epoch: world.createdEpoch,
        status: 'canon',
        worldId: world.id,
        locationId: null,
        family: familyOf('world'),
      })
    }
    for (const route of routes) {
      if (!present.has(route.first) || !present.has(route.second)) continue
      links.push({
        key: linkKey(route.first, route.second, ROUTE),
        source: route.first,
        target: route.second,
        kind: ROUTE,
        groups: groupIndex.get(ROUTE) ?? [],
        epoch: route.epoch,
        past: false,
        open: route.active,
        description: route.description,
      })
    }
    for (const node of nodes) {
      if (node.kind === 'world' || node.worldId === null) continue
      const root =
        (node.kind === 'entity' &&
          ROOT_TYPES.has(node.type) &&
          node.locationId === null) ||
        node.kind === 'foreign_god'
      if (!root || !present.has(node.worldId)) continue
      links.push({
        key: linkKey(node.id, node.worldId, IN_WORLD),
        source: node.id,
        target: node.worldId,
        kind: IN_WORLD,
        groups: groupIndex.get(IN_WORLD) ?? [],
        epoch: node.epoch,
        past: false,
        open: true,
        description: null,
      })
    }
  }
  return { nodes, links }
}

export type GraphFilter = {
  group: LinkGroup
  epoch: number | null
  hiddenTypes: ReadonlySet<string>
  worldId: number | null
  focusId: number | null
  whole: boolean
  autoLinks: number
  radius: number
  cap: number
}

export type FilteredGraph = Graph & {
  focusId: number | null
  strayFocus: boolean
  radius: number
  reduced: boolean
  partial: number
  degree: Map<number, number>
}

export function degrees(links: readonly GraphLink[]): Map<number, number> {
  const degree = new Map<number, number>()
  for (const link of links) {
    degree.set(link.source, (degree.get(link.source) ?? 0) + 1)
    degree.set(link.target, (degree.get(link.target) ?? 0) + 1)
  }
  return degree
}

function adjacency(links: readonly GraphLink[]): Map<number, number[]> {
  const found = new Map<number, number[]>()
  for (const link of links) {
    found.set(link.source, [...(found.get(link.source) ?? []), link.target])
    found.set(link.target, [...(found.get(link.target) ?? []), link.source])
  }
  return found
}

export function rings(
  links: readonly GraphLink[],
  kinds: ReadonlyMap<number, string>,
  focus: number,
  radius: number
): number[][] {
  const neighbours = adjacency(links)
  const seen = new Set([focus])
  const found = [[focus]]
  let frontier = [focus]
  for (let step = 0; step < radius && frontier.length > 0; step += 1) {
    const next: number[] = []
    for (const id of frontier) {
      if (id !== focus && kinds.get(id) === 'world') continue
      for (const other of neighbours.get(id) ?? []) {
        if (seen.has(other)) continue
        seen.add(other)
        next.push(other)
      }
    }
    if (next.length > 0) found.push(next)
    frontier = next
  }
  return found
}

function nearest(
  found: readonly number[][],
  cap: number,
  degree: ReadonlyMap<number, number>
): { kept: Set<number>; whole: number; partial: number; cut: boolean } {
  const kept = new Set<number>()
  let whole = 0
  for (const [step, ring] of found.entries()) {
    if (kept.size + ring.length <= cap) {
      for (const id of ring) kept.add(id)
      whole = step
      continue
    }
    const room = Math.max(cap - kept.size, 0)
    const best = [...ring]
      .sort((a, b) => (degree.get(b) ?? 0) - (degree.get(a) ?? 0) || a - b)
      .slice(0, room)
    for (const id of best) kept.add(id)
    return { kept, whole, partial: best.length, cut: true }
  }
  return { kept, whole, partial: 0, cut: false }
}

function worldScope(graph: Graph, worldId: number): Set<number> {
  const neighbours = new Set([worldId])
  for (const link of graph.links) {
    if (link.kind !== ROUTE) continue
    if (link.source === worldId) neighbours.add(link.target)
    if (link.target === worldId) neighbours.add(link.source)
  }
  return new Set(
    graph.nodes
      .filter((node) =>
        node.kind === 'world'
          ? neighbours.has(node.id)
          : node.worldId === null || node.worldId === worldId
      )
      .map((node) => node.id)
  )
}

function busiest(
  nodes: readonly GraphNode[],
  links: readonly GraphLink[]
): number | null {
  const degree = degrees(links)
  const ranked = [...nodes].sort(
    (left, right) =>
      (degree.get(right.id) ?? 0) - (degree.get(left.id) ?? 0) ||
      left.id - right.id
  )
  return ranked[0]?.id ?? null
}

export function filterGraph(graph: Graph, filter: GraphFilter): FilteredGraph {
  const scope =
    filter.worldId === null ? null : worldScope(graph, filter.worldId)
  let nodes = graph.nodes.filter(
    (node) =>
      !filter.hiddenTypes.has(node.type) &&
      (filter.epoch === null || node.epoch <= filter.epoch) &&
      (scope === null || scope.has(node.id))
  )
  const ids = new Set(nodes.map((node) => node.id))
  let links = graph.links.filter(
    (link) =>
      inGroup(link, filter.group) &&
      (filter.epoch === null || link.epoch <= filter.epoch) &&
      ids.has(link.source) &&
      ids.has(link.target)
  )
  let radius = filter.radius
  let reduced = false
  let partial = 0
  const inView = filter.focusId !== null && ids.has(filter.focusId)
  const focusId = inView
    ? filter.focusId
    : filter.whole && filter.focusId === null
      ? null
      : (defaultFocus({ nodes, links }, filter.hiddenTypes, filter.autoLinks) ??
        busiest(nodes, links))
  const strayFocus = filter.focusId !== null && !inView
  if (focusId !== null) {
    const kinds = new Map(nodes.map((node) => [node.id, node.kind]))
    const found = rings(links, kinds, focusId, radius)
    const fitted = nearest(found, filter.cap, degrees(links))
    const around = fitted.kept
    if (fitted.cut) {
      reduced = true
      radius = fitted.whole
      partial = fitted.partial
    }
    nodes = nodes.filter((node) => around.has(node.id))
    links = links.filter(
      (link) => around.has(link.source) && around.has(link.target)
    )
  } else if (filter.group !== 'all') {
    const linked = new Set(links.flatMap((link) => [link.source, link.target]))
    nodes = nodes.filter((node) => linked.has(node.id))
  }
  return {
    nodes,
    links,
    focusId,
    strayFocus,
    radius,
    reduced,
    partial,
    degree: degrees(links),
  }
}

export function defaultFocus(
  graph: Graph,
  hiddenTypes: ReadonlySet<string>,
  maxLinks: number
): number | null {
  const structural = graph.links.filter(
    (link) => link.kind !== INSIDE && link.kind !== IN_WORLD
  )
  const degree = degrees(structural)
  const score = (node: GraphNode) =>
    (degree.get(node.id) ?? 0) * 2 + node.size + (node.kind === 'son' ? 3 : 0)
  const candidates = graph.nodes.filter(
    (node) => node.kind !== 'world' && !hiddenTypes.has(node.type)
  )
  const ranked = [...candidates].sort(
    (left, right) => score(right) - score(left)
  )
  const linked = ranked.filter((node) => (degree.get(node.id) ?? 0) > 0)
  const within = linked.find((node) => (degree.get(node.id) ?? 0) <= maxLinks)
  return (within ?? linked[0] ?? ranked[0])?.id ?? null
}

export function nodeRadius(node: GraphNode, degree: number): number {
  if (node.kind === 'world') return 16
  const base = node.kind === 'son' ? 6 : 3
  return base + Math.min(10, node.size * 0.8 + Math.sqrt(degree) * 1.4)
}

export function linkLabel(
  link: Pick<GraphLink, 'kind' | 'past'>,
  labels: ReadonlyMap<string, string>
): string {
  const names: Record<string, string> = {
    [CREATED]: 'created',
    [INSIDE]: 'inside',
    [ROUTE]: 'inter-world route',
    [IN_WORLD]: 'in this world',
    'in world': 'in this world',
  }
  const label =
    names[link.kind] ?? labels.get(link.kind) ?? link.kind.replaceAll('_', ' ')
  return link.past ? `formerly ${label}` : label
}

export type GraphMode = '2d' | '3d'
export const GRAPH_MODES: readonly GraphMode[] = ['2d', '3d']
export const RADII = [1, 2, 3] as const

export type NodeEntryKind =
  'son' | 'foreign-god' | 'creator' | 'world' | 'entity'

export function entryKindOf(kind: string | undefined): NodeEntryKind | null {
  switch (kind) {
    case 'son':
      return 'son'
    case 'foreign_god':
      return 'foreign-god'
    case 'creator':
      return 'creator'
    case 'world':
      return 'world'
    case 'entity':
      return 'entity'
    default:
      return null
  }
}

export function findNode<T extends { name: string }>(
  nodes: readonly T[],
  text: string
): T | undefined {
  const wanted = text.trim().toLocaleLowerCase('en-US')
  if (!wanted) return undefined
  return nodes.find((node) => node.name.toLocaleLowerCase('en-US') === wanted)
}
