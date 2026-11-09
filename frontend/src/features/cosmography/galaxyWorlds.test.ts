import { describe, expect, it } from 'vitest'
import { type CosmosData } from '@/features/cosmos/api'
import { layoutCosmos3D } from '@/features/cosmos/model/layout3d'
import cosmosFixture from '../../../e2e/fixtures/cosmos.json'
import { VIEW } from './cosmographyFixtures'
import { cosmosInGalaxy } from './cosmosGalaxy'
import { worldMarks } from './galaxyWorlds'

const HOME = 301
const FAR = 302
const RAW = cosmosFixture.cosmos as unknown as CosmosData
const COSMOS: CosmosData = {
  ...RAW,
  stars: RAW.stars.map((star) => ({
    ...star,
    galaxy_id: star.id === 11 ? FAR : HOME,
  })),
}
const HEAVENS = {
  ...VIEW,
  galaxies: [...VIEW.galaxies, { ...VIEW.galaxies[0], id: FAR }],
  placements: COSMOS.worlds.map((item) => ({
    ...VIEW.placements[0],
    world_id: item.world.id,
    star_id: item.world.star_id,
    galaxy_id: item.world.star_id === 11 ? FAR : HOME,
  })),
}

describe('worlds on the galaxy map', () => {
  it('stand exactly where the Cosmos draws them, and only in their own galaxy', () => {
    const marks = worldMarks(COSMOS, HEAVENS, HOME)
    const layout = layoutCosmos3D(cosmosInGalaxy(COSMOS, HEAVENS, HOME))
    expect(marks.map((mark) => mark.id).sort((a, b) => a - b)).toEqual([
      3, 5, 6, 8, 9, 13,
    ])
    for (const mark of marks) {
      const body = layout.worlds.get(mark.id)
      expect(body).toBeDefined()
      if (!body) continue
      const host =
        body.starId !== null ? layout.stars.get(body.starId) : undefined
      const x = host
        ? host.position[0] + Math.cos(body.phase) * body.orbitRadius
        : body.anchor[0]
      expect(mark.x).toBeCloseTo(x)
      expect(mark.sunless).toBe(!host)
    }
    expect(marks.find((mark) => mark.id === 13)?.sunless).toBe(true)
    expect(worldMarks(COSMOS, HEAVENS, FAR).map((mark) => mark.id)).toEqual([
      12, 14,
    ])
  })
})
