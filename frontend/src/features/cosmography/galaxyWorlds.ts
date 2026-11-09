import { type CosmosData } from '@/features/cosmos/api'
import { layoutCosmos3D } from '@/features/cosmos/model/layout3d'
import { type Cosmography } from './api'
import { cosmosInGalaxy } from './cosmosGalaxy'

export type WorldMark = {
  id: number
  name: string
  x: number
  y: number
  sunless: boolean
}

export function worldMarks(
  cosmos: CosmosData | undefined,
  heavens: Cosmography,
  galaxyId: number
): WorldMark[] {
  if (!cosmos) return []
  const shown = cosmosInGalaxy(cosmos, heavens, galaxyId)
  const layout = layoutCosmos3D(shown)
  return shown.worlds.flatMap((item) => {
    const body = layout.worlds.get(item.world.id)
    if (!body || body.kind === 'moon') return []
    const host = body.starId !== null ? layout.stars.get(body.starId) : null
    const [x, , y] = host
      ? [
          host.position[0] + Math.cos(body.phase) * body.orbitRadius,
          0,
          host.position[2] + Math.sin(body.phase) * body.orbitRadius,
        ]
      : body.anchor
    return [{ id: item.world.id, name: item.world.name, x, y, sunless: !host }]
  })
}
