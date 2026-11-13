import { describe, expect, it } from 'vitest'
import {
  buildingFormValues,
  landGroundValues,
  structureKindValues,
} from '@/api/generated/schema'
import { STRUCTURE_LOOK, groundLook, riverLook, typedLook } from './models'

const RIM = new Set(['wall', 'gate'])
const WATER_GATES = new Set(['reservoir', 'canal_lock'])

function walled(models: string[]): boolean {
  return models.some((model) => /\/wall_/.test(model))
}

describe('city models', () => {
  it('draws a wall only for the rim of a town and for the gates of water works', () => {
    const kinds = structureKindValues.filter((kind) =>
      walled(STRUCTURE_LOOK[kind].map((part) => part.model))
    )
    expect(
      kinds.filter((kind) => !RIM.has(kind) && !WATER_GATES.has(kind))
    ).toEqual([])
    const forms = buildingFormValues.filter((form) =>
      walled([typedLook('market', form, 1)[0].model])
    )
    expect(forms).toEqual(['wall_line'])
  })

  it('fills every hex of a land with its ground tile, rivers included, so no gap opens between hexes', () => {
    const tiles = [
      ...landGroundValues.map((ground) => groundLook(ground, 0, 0)[0]),
      riverLook()[0],
    ]
    expect(tiles.filter((part) => (part.scale ?? 1) !== 1)).toEqual([])
  })
})
