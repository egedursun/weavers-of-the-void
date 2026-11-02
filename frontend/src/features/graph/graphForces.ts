import {
  type GraphLink,
  type GraphNode,
  INSIDE,
  IN_WORLD,
  ROUTE,
} from './graphModel'

export type PositionMemory = Map<number, { x: number; y: number; z?: number }>

type SimNode = GraphNode & {
  x?: number
  y?: number
  z?: number
  vx?: number
  vy?: number
  vz?: number
}

type LinkForce = {
  distance: (value: (link: GraphLink) => number) => LinkForce
  strength: (value: (link: GraphLink) => number) => LinkForce
}

type ChargeForce = { strength: (value: number) => ChargeForce }

type ForceHost = {
  d3Force: (name: string, force?: unknown) => unknown
}

const DISTANCE: Record<string, number> = {
  [INSIDE]: 36,
  [ROUTE]: 240,
  [IN_WORLD]: 70,
}
const STRENGTH: Record<string, number> = {
  [INSIDE]: 0.8,
  [ROUTE]: 0.05,
  [IN_WORLD]: 0.22,
}
const DEFAULT_DISTANCE = 80
const DEFAULT_STRENGTH = 0.22
const FOCUSED_CHARGE = -260
const OPEN_CHARGE = -150
const CLUSTER_STRENGTH = 0.14

export function configureForces(
  host: ForceHost,
  focused: boolean,
  scale = 1
): void {
  const link = host.d3Force('link') as LinkForce | undefined
  link
    ?.distance((item) => (DISTANCE[item.kind] ?? DEFAULT_DISTANCE) * scale)
    .strength((item) => STRENGTH[item.kind] ?? DEFAULT_STRENGTH)
  const charge = host.d3Force('charge') as ChargeForce | undefined
  charge?.strength(focused ? FOCUSED_CHARGE : OPEN_CHARGE)
}

export function clusterCentres(
  nodes: readonly SimNode[],
  radius: number
): Map<number, { x: number; y: number }> {
  const worlds = [
    ...new Set(
      nodes
        .map((node) => node.worldId)
        .filter((id): id is number => id !== null)
    ),
  ].sort((left, right) => left - right)
  return new Map(
    worlds.map((id, index) => {
      const angle = (index / Math.max(1, worlds.length)) * Math.PI * 2
      return [id, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }]
    })
  )
}

export function clusterForce(
  nodes: readonly SimNode[],
  radius: number,
  strength = CLUSTER_STRENGTH,
  flatten = 0
) {
  let current: SimNode[] = [...nodes]
  let centres = clusterCentres(current, radius)
  const force = (alpha: number) => {
    for (const node of current) {
      if (node.worldId === null) continue
      const centre = centres.get(node.worldId)
      if (!centre) continue
      node.vx = (node.vx ?? 0) + (centre.x - (node.x ?? 0)) * strength * alpha
      node.vy = (node.vy ?? 0) + (centre.y - (node.y ?? 0)) * strength * alpha
      if (flatten > 0)
        node.vz = (node.vz ?? 0) - (node.z ?? 0) * flatten * alpha
    }
  }
  force.initialize = (next: SimNode[]) => {
    current = next
    centres = clusterCentres(current, radius)
  }
  return force
}

export function knownShare(
  nodes: readonly GraphNode[],
  positions: PositionMemory
): number {
  if (nodes.length === 0) return 0
  return nodes.filter((node) => positions.has(node.id)).length / nodes.length
}
