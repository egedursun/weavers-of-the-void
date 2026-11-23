import { describe, expect, it } from 'vitest'
import { AGENT_STATUS, FATE_OF, ROLE, SACK_CHOICE, SIEGE_WORK } from './depth'
import {
  DEFENCE,
  FATE,
  OPERATION,
  SIEGE_ACTION,
  SIEGE_STATUS,
  STANCE,
} from './labels'

describe('war values of the fifth wave', () => {
  it('names every new stance, role, fate, operation and siege value', () => {
    expect(STANCE.winter_quarters.label).toBe('In winter quarters')
    expect(STANCE.pursue.label).toBe('Pursuing')
    expect(STANCE.escort.label).toBe('Escorting convoys')
    expect(ROLE.scout_master.label).toBe('Master of scouts')
    expect(FATE.recruited.label).toBe('Pressed into the army')
    expect(FATE_OF.deserted.label).toBe('Deserted')
    expect(OPERATION.disinform.label).toBe('Fed false beliefs')
    expect(AGENT_STATUS.exposed.label).toBe('Known to the enemy')
    expect(SIEGE_ACTION.suborn.label).toBe('Suborning the garrison')
    expect(DEFENCE.expel_mouths.label).toBe(
      'Driving out those who cannot fight'
    )
    expect(SIEGE_WORK.ramp.label).toBe('Siege ramp')
    expect(SACK_CHOICE.ransom_city.label).toBe('Ransom the city')
    expect(SIEGE_STATUS.surrendered.label).toBe('Surrendered on terms')
  })
})
