import { describe, expect, it } from 'vitest'
import {
  BEING_AGENDAS,
  BEING_SCALES,
  RIFT_CAUSES,
} from '@/features/cosmography/labels'
import { STANCES, TRAITS } from '@/features/living/labels'
import {
  AUGMENT_KINDS,
  MIND_PURPOSES,
  NETWORK_CARRIERS,
  REALM_ENTRIES,
  RELIC_STATES,
  SURVEILLANCE_FOCUSES,
} from '@/features/minds/labels'
import { ALLOCATION } from '@/features/orders/labels'
import {
  ATTITUDES,
  ORIGINS,
  SOURCE_LAWS,
  TRUTH_KINDS,
} from '@/features/powers/labels'

describe('labels of the boundless, the made and the gifted', () => {
  it('names every value the second pass and the deepening add', () => {
    expect(BEING_AGENDAS.slumber).toBe('Slumber')
    expect(BEING_SCALES.region).toBe('Region')
    expect(RIFT_CAUSES.mass_weapon).toBeTruthy()
    expect(RIFT_CAUSES.outer_bargain).toBeTruthy()
    expect(MIND_PURPOSES.soldier.label).toBe('Soldier')
    expect(MIND_PURPOSES.teacher.label).toBe('Teacher')
    expect(REALM_ENTRIES.dream.label).toBe('Dream')
    expect(AUGMENT_KINDS.life_support.label).toBe('Life support')
    expect(AUGMENT_KINDS.armour.label).toBe('Armour')
    expect(SURVEILLANCE_FOCUSES.kind.label).toBe('Kind of being')
    expect(SURVEILLANCE_FOCUSES.language.label).toBe('Language')
    expect(NETWORK_CARRIERS.dream_link.label).toBe('Dream link')
    expect(RELIC_STATES.restored.label).toBe('Restored')
    expect(ALLOCATION.lottery.label).toBe('By lot')
    expect(SOURCE_LAWS.conscripted.label).toBe('Conscripted')
    expect(SOURCE_LAWS.taxed.label).toBe('Taxed')
    expect(ATTITUDES.exploited.label).toBe('Exploited')
    expect(ATTITUDES.envied.label).toBe('Envied')
    expect(ORIGINS.bargain.label).toBe('An outer bargain')
    expect(TRUTH_KINDS.lineage.label).toBe('Lineage')
    expect(STANCES.regulated.label).toBe('Regulated')
    expect(TRAITS.filtering.label).toBe('Filters water and air')
  })
})
