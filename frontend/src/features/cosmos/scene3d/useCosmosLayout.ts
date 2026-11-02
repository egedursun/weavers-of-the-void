import { useMemo } from 'react'
import { type CosmosData } from '../api'
import { type Layout3D, layoutCosmos3D } from '../model/layout3d'

const BEND_STEP = 0.2

export function layoutSignature(data: CosmosData): string {
  const stars = data.stars.map(
    (star) => `${star.id}:${star.star_type}:${star.x}:${star.y}`
  )
  const worlds = data.worlds.map(
    (item) =>
      `${item.world.id}:${item.world.star_id}:${item.world.parent_world_id}:${item.world.orbit}:${item.world.world_type}:${item.counts.population}:${item.counts.regions}`
  )
  return `${stars.join('|')}#${worlds.join('|')}`
}

export function routeBends(data: CosmosData): Map<number, number> {
  const seen = new Map<string, number>()
  const bends = new Map<number, number>()
  for (const route of data.routes) {
    const low = Math.min(route.world_a_id, route.world_b_id)
    const high = Math.max(route.world_a_id, route.world_b_id)
    const key = `${low}-${high}`
    const count = seen.get(key) ?? 0
    seen.set(key, count + 1)
    const magnitude = Math.ceil(count / 2) * BEND_STEP
    bends.set(route.id, count % 2 === 0 ? magnitude : -magnitude)
  }
  return bends
}

function bySignature<T>(
  build: (data: CosmosData) => T,
  sign: (data: CosmosData) => string
) {
  let lastSignature: string | null = null
  let lastValue: T | null = null
  return (data: CosmosData): T => {
    const signature = sign(data)
    if (lastValue === null || signature !== lastSignature) {
      lastValue = build(data)
      lastSignature = signature
    }
    return lastValue
  }
}

const stableLayout = bySignature(layoutCosmos3D, layoutSignature)
const stableBends = bySignature(routeBends, (data) =>
  data.routes
    .map((route) => `${route.id}:${route.world_a_id}:${route.world_b_id}`)
    .join('|')
)

export function useCosmosLayout(data: CosmosData): {
  layout: Layout3D
  routeBend: Map<number, number>
} {
  const layout = useMemo(() => stableLayout(data), [data])
  const routeBend = useMemo(() => stableBends(data), [data])
  return { layout, routeBend }
}
