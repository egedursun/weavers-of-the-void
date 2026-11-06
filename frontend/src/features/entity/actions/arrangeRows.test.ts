import { describe, expect, it } from 'vitest'
import { type EntityDetail, type WorldState } from '../api/types'
import { buildContext } from './context'
import { RECORD_ACTIONS, actionsFor } from './registry'

const ALL = new Set(RECORD_ACTIONS.map((spec) => spec.id))

function detail(type: string, flags: string[] = []): EntityDetail {
  return {
    entity: {
      id: 9,
      name: 'Velmora',
      entity_type: type,
      status: 'canon',
      world_id: 1,
      stats: { kind: type },
    },
    flags,
    traits: [],
    tags: [],
    bonds: [],
    bond_total: 0,
    insight: {},
  } as unknown as EntityDetail
}

function state(worlds: number, resource: boolean): WorldState {
  return {
    worlds: Array.from({ length: worlds }, (_, index) => ({
      id: index + 1,
      name: `World ${index + 1}`,
    })),
    world: { travel_resource: resource ? { name: 'Hour sand' } : null },
    sons: [],
  } as unknown as WorldState
}

function offered(type: string, flags: string[] = [], world = state(2, true)) {
  const ctx = buildContext(detail(type, flags), [], world, [])
  return new Map(actionsFor(ctx, ALL).map((spec) => [spec.id, { spec, ctx }]))
}

describe('arrange and command rows', () => {
  it('offers exile of a living record only when the cosmos has another world', () => {
    const exile = offered('mortal').get('exile')
    expect(exile?.spec.route).toMatchObject({
      path: '/api/entities/{entity_id}/exile',
    })
    expect(exile?.spec.destructive).toBe(true)
    expect(offered('people').has('exile')).toBe(true)
    expect(offered('mortal', [], state(1, true)).has('exile')).toBe(false)
    expect(offered('structure').has('exile')).toBe(false)
  })

  it('offers a pardon only to oath-breakers, exiles and the cursed', () => {
    expect(offered('mortal').has('pardon')).toBe(false)
    for (const flag of ['oathbreaker', 'exile', 'cursed'])
      expect(offered('mortal', [flag]).has('pardon')).toBe(true)
  })

  it('binds a spirit into a vessel, item or work through the soul-bind route', () => {
    const bind = offered('spirit').get('cosmic:soul_bind')
    expect(bind?.spec.route).toEqual({
      method: 'POST',
      path: '/api/cosmic/soul-bind',
    })
    expect(bind?.spec.self).toBe('soul_id')
    expect(bind?.spec.labels?.target_id).toBe('Vessel, item or work')
    expect(offered('mortal').has('cosmic:soul_bind')).toBe(false)
  })

  it('opens a cosmic deposit in a region only once the travel resource is defined', () => {
    const ready = offered('region').get('cosmos:deposit')
    expect(ready?.spec.route).toEqual({
      method: 'POST',
      path: '/api/cosmic-resource/deposits',
    })
    expect(ready?.spec.self).toBe('place_id')
    expect(ready?.spec.blocked?.(ready.ctx) ?? null).toBeNull()
    const waiting = offered('region', [], state(2, false)).get('cosmos:deposit')
    expect(waiting?.spec.blocked?.(waiting.ctx)).toBe(
      "Define the cosmos's travel resource in the Cosmos screen first."
    )
    expect(offered('mortal').has('cosmos:deposit')).toBe(false)
  })
})
