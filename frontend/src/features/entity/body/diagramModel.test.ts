import { describe, expect, it } from 'vitest'
import type { components } from '@/api/generated/schema'
import { LEGEND, isLost, partTone } from './diagramModel'
import {
  CAPACITIES,
  CONDITIONS,
  INJURIES,
  MAIMED,
  PLANS,
  READINGS,
} from './labels'

type Part = components['schemas']['PartView']

function part(changes: Partial<Part>): Part {
  return {
    key: 'right_hand',
    label: 'Right hand',
    region: 'arms',
    functions: ['grasp'],
    severable: true,
    internal: false,
    vital: false,
    loss: 0,
    state: null,
    prosthesis: null,
    ...changes,
  }
}

describe('body diagram model', () => {
  it('colours a part by the state of its worst wound', () => {
    expect(partTone(part({}))).toContain('fill-muted')
    expect(partTone(part({ state: 'fresh', loss: 15 }))).toContain('warning')
    expect(partTone(part({ state: 'infected', loss: 35 }))).toContain(
      'destructive'
    )
    expect(partTone(part({ state: 'healed_scar', loss: 5 }))).toContain(
      'success'
    )
    expect(
      partTone(part({ state: 'permanent', loss: 100, prosthesis: 'silver' }))
    ).toContain('primary')
  })

  it('knows a lost part from a damaged one', () => {
    expect(isLost(part({ state: 'permanent', loss: 100 }))).toBe(true)
    expect(isLost(part({ state: 'permanent', loss: 60 }))).toBe(false)
    expect(
      isLost(part({ state: 'permanent', loss: 100, prosthesis: 'wood' }))
    ).toBe(false)
    expect(LEGEND.some((item) => item.dashed)).toBe(true)
  })

  it('names every kind the backend sends', () => {
    const plans: components['schemas']['BodyPlan'][] = [
      'humanoid',
      'quadruped',
      'avian',
      'serpentine',
      'insectoid',
      'aquatic',
      'amorphous',
      'arboreal',
      'incorporeal',
      'colossal',
      'construct',
      'divine_manifest',
    ]
    const capacities: components['schemas']['Capacity'][] = [
      'melee',
      'missile',
      'command',
      'craft',
      'scholarship',
      'presence',
      'mobility',
      'fertility',
    ]
    const injuries: components['schemas']['InjuryKind'][] = [
      'bruise',
      'cut',
      'deep_cut',
      'puncture',
      'fracture',
      'crush',
      'burn',
      'frostbite',
      'bite',
      'venom',
      'severed',
      'gouged',
      'destroyed',
      'curse_wither',
      'void_touch',
      'divine_brand',
    ]
    const conditions: components['schemas']['ConditionKind'][] = [
      'chronic_illness',
      'paranoia',
      'visions',
      'rage',
      'melancholy',
      'addiction',
      'age_blindness',
      'age_deafness',
      'withered_limb',
      'endless_hunger',
      'possession',
      'void_taint',
      'chosen_mark',
      'divine_brand',
    ]
    const maimed: components['schemas']['MaimedKind'][] = [
      'one_armed',
      'one_legged',
      'one_eyed',
      'blind',
      'deaf',
      'mute',
      'lame',
      'scarred',
      'broken_minded',
    ]
    const readings: components['schemas']['BodyReading'][] = [
      'neutral',
      'martial_honour',
      'purity',
      'sanctified_suffering',
    ]
    expect(plans.filter((key) => !PLANS[key])).toEqual([])
    expect(capacities.filter((key) => !CAPACITIES[key])).toEqual([])
    expect(injuries.filter((key) => !INJURIES[key])).toEqual([])
    expect(conditions.filter((key) => !CONDITIONS[key])).toEqual([])
    expect(maimed.filter((key) => !MAIMED[key])).toEqual([])
    expect(readings.filter((key) => !READINGS[key])).toEqual([])
  })
})
