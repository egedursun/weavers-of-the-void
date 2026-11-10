import { describe, expect, it } from 'vitest'
import { type EntityDetail } from '../api/types'
import { buildContext } from './context'
import { fixedCost } from './gate'
import { RECORD_ACTIONS, actionsFor } from './registry'

function detail(
  type: string,
  status = 'canon',
  flags: string[] = [],
  pendingName = false
): EntityDetail {
  return {
    entity: {
      id: 9,
      name: 'Velmora',
      title: null,
      entity_type: type,
      subtype: null,
      status,
      world_id: 1,
      location_id: null,
      power_level: 3,
      birth_epoch: 1,
      end_epoch: null,
      importance: 10,
      favorite: false,
      pending_name: pendingName,
      description: 'A record.',
      stats: { kind: type },
      domain: null,
      origin: 'son',
      creator_son_id: null,
      mortal_role: null,
      legend_category: null,
      fate_note: null,
      depth: null,
      archive_override: null,
      private_note: null,
      map_x: null,
      map_y: null,
      image_prompt: null,
      civ_tier: null,
      sanity: null,
      last_acted_epoch: 0,
      is_underworld: false,
      is_water: false,
    },
    cover: null,
    creator_son: null,
    maker: null,
    patron: null,
    breadcrumb: [],
    contents: [],
    content_total: 0,
    flags,
    traits: [],
    tags: [],
    bonds: [],
    bond_total: 0,
    chronicle: [],
    chronicle_total: 0,
    facts: [],
    perspectives: [],
    similar: [],
    anchored_sons: [],
    importance: null,
    images: [],
    insight: {},
  } as unknown as EntityDetail
}

const ALL = new Set(RECORD_ACTIONS.map((spec) => spec.id))

function ids(type: string, status?: string, flags?: string[]) {
  return actionsFor(
    buildContext(detail(type, status, flags), [], undefined, []),
    ALL
  ).map((spec) => spec.id)
}

describe('record action registry', () => {
  it('has one spec per catalogue action', () => {
    expect(new Set(RECORD_ACTIONS.map((spec) => spec.id)).size).toBe(
      RECORD_ACTIONS.length
    )
  })

  it('offers mortal powers only to living mortals', () => {
    const living = ids('mortal')
    expect(living).toEqual(
      expect.arrayContaining([
        'take_life',
        'deify',
        'drain:mortal',
        'mortal:protect',
      ])
    )
    expect(living).not.toContain('harvest')
    const dead = ids('mortal', 'dead')
    expect(dead).toContain('resurrect:mortal')
    expect(dead).not.toContain('take_life')
  })

  it('offers community, settlement and species commands to their kinds', () => {
    expect(ids('settlement')).toEqual(
      expect.arrayContaining([
        'harvest',
        'settlement:shelter',
        'society:shares',
        'war:open',
      ])
    )
    expect(ids('settlement', 'canon', ['ruin'])).toContain(
      'settlement:resettle'
    )
    expect(ids('species')).toEqual(
      expect.arrayContaining(['species:awaken', 'species:cull'])
    )
    expect(ids('species')).not.toContain('settlement:shelter')
  })

  it('needs a war before war orders appear', () => {
    expect(ids('people')).not.toContain('war:battle')
  })

  it('reads fixed costs from the live cost text', () => {
    expect(fixedCost('15 essence')).toBe(15)
    expect(fixedCost('Free')).toBe(0)
    expect(fixedCost('40 + power x 2 essence')).toBeNull()
  })

  it('offers prisoner and tribute orders only where a prisoner or tribute is held', () => {
    const bond = (kind: string, outgoing: boolean) =>
      ({
        id: 5,
        kind,
        state: 'active',
        outgoing,
        other: { id: 3, name: 'Kharun', kind: 'entity' },
        war_id: null,
      }) as never
    const plain = actionsFor(
      buildContext(detail('people'), [], undefined, []),
      ALL
    ).map((spec) => spec.id)
    expect(plain).not.toContain('captive:free')
    expect(plain).not.toContain('tribute:forgive')
    const held = buildContext(
      detail('people'),
      [bond('holds_captive', true), bond('pays_tribute', false)],
      undefined,
      []
    )
    const offered = actionsFor(held, ALL).map((spec) => spec.id)
    expect(offered).toEqual(
      expect.arrayContaining([
        'captive:free',
        'captive:ransom',
        'tribute:forgive',
      ])
    )
    expect(held.captives).toEqual([
      { value: 3, label: 'Kharun, held by Velmora' },
    ])
    expect(held.tributes).toEqual([{ value: 5, label: 'Kharun pays Velmora' }])
    const prisoner = buildContext(
      detail('mortal'),
      [bond('holds_captive', false)],
      undefined,
      []
    )
    expect(prisoner.captives).toEqual([
      { value: 9, label: 'Velmora, held by Kharun' },
    ])
  })

  it('lets a living mortal act now through the language model, after confirmation', () => {
    expect(ids('mortal')).toContain('mortal:act')
    expect(ids('mortal', 'dead')).not.toContain('mortal:act')
    const spec = RECORD_ACTIONS.find((item) => item.id === 'mortal:act')
    expect(spec).toMatchObject({ llm: true, world: true, self: 'entity_id' })
    expect(
      spec?.confirm?.(buildContext(detail('mortal'), [], undefined, []))
    ).toContain('Velmora plays a turn')
  })

  it('seats a capital only on a settlement that is not one yet', () => {
    expect(ids('settlement')).toContain('settlement:capital')
    expect(ids('settlement', 'canon', ['capital'])).not.toContain(
      'settlement:capital'
    )
    expect(ids('people')).not.toContain('settlement:capital')
  })

  it('accepts a name despite the dialect only while the name waits for review', () => {
    expect(ids('people')).not.toContain('name:accept')
    const waiting = buildContext(
      detail('people', 'canon', [], true),
      [],
      undefined,
      []
    )
    expect(actionsFor(waiting, ALL).map((spec) => spec.id)).toContain(
      'name:accept'
    )
    expect(
      RECORD_ACTIONS.find((item) => item.id === 'name:accept')?.defaults?.(
        waiting
      )
    ).toEqual({ name: 'Velmora' })
  })
})
