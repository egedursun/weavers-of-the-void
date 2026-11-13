import { describe, expect, it } from 'vitest'
import { buildingFormValues, structureKindValues } from '@/api/generated/schema'
import { STRUCTURE_LOOK, typedLook } from './models'

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
})
