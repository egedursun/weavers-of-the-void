import { type FoodWeb } from './api'

type Node = FoodWeb['nodes'][number]
type Link = FoodWeb['links'][number]

export type PlacedNode = {
  id: number
  name: string
  diet: string
  tier: number
  x: number
  y: number
  r: number
}

export type PlacedEdge = { from: number; to: number; pinned: boolean }

export type WebLayout = {
  nodes: PlacedNode[]
  edges: PlacedEdge[]
  width: number
  height: number
  tiers: number
}

const ROW = 96
const PAD = 40
const MIN_R = 9
const GROW_R = 14
const PERCENT = 100

export function tiersOf(
  ids: readonly number[],
  links: readonly Link[]
): Map<number, number> {
  const prey = new Map<number, number[]>()
  for (const link of links) {
    if (link.hunter_id === link.prey_id) continue
    prey.set(link.hunter_id, [
      ...(prey.get(link.hunter_id) ?? []),
      link.prey_id,
    ])
  }
  const known = new Set(ids)
  const tiers = new Map<number, number>()
  const visit = (id: number, path: Set<number>): number => {
    const done = tiers.get(id)
    if (done !== undefined) return done
    if (path.has(id)) return 0
    path.add(id)
    const below = (prey.get(id) ?? []).filter((item) => known.has(item))
    const tier =
      below.length === 0
        ? 0
        : 1 + Math.max(...below.map((item) => visit(item, path)))
    path.delete(id)
    tiers.set(id, tier)
    return tier
  }
  for (const id of ids) visit(id, new Set())
  return tiers
}

export function layoutWeb(web: FoodWeb, width = 640): WebLayout {
  const ids = web.nodes.map((node) => node.species.id)
  const tiers = tiersOf(ids, web.links)
  const top = Math.max(0, ...tiers.values())
  const rows = new Map<number, Node[]>()
  for (const node of web.nodes) {
    const tier = tiers.get(node.species.id) ?? 0
    rows.set(tier, [...(rows.get(tier) ?? []), node])
  }
  const nodes: PlacedNode[] = []
  for (const [tier, row] of rows) {
    const sorted = [...row].sort(
      (left, right) =>
        right.abundance - left.abundance || left.species.id - right.species.id
    )
    sorted.forEach((node, index) => {
      nodes.push({
        id: node.species.id,
        name: node.species.name,
        diet: node.diet,
        tier,
        x: Math.round(((index + 1) * width) / (sorted.length + 1)),
        y: PAD + (top - tier) * ROW,
        r:
          MIN_R +
          Math.round((Math.min(PERCENT, node.abundance) / PERCENT) * GROW_R),
      })
    })
  }
  const placed = new Set(nodes.map((node) => node.id))
  const edges = web.links
    .filter(
      (link) =>
        placed.has(link.hunter_id) &&
        placed.has(link.prey_id) &&
        link.hunter_id !== link.prey_id
    )
    .map((link) => ({
      from: link.hunter_id,
      to: link.prey_id,
      pinned: link.kind === 'pinned',
    }))
  return { nodes, edges, width, height: PAD * 2 + top * ROW, tiers: top + 1 }
}
