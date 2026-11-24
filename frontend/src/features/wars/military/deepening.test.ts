import { describe, expect, it } from 'vitest'
import {
  AGENT_STATUS,
  CONTRACT_STATUS,
  ROLE,
  SACK_CHOICE,
  SIEGE_WORK,
} from './depth'
import {
  COMMAND_AREA,
  DEFENCE,
  FATE,
  FORMATION,
  OPERATION,
  SIEGE_ACTION,
  SIEGE_STATUS,
  STANCE,
  STARVATION,
  TACTIC,
  TRAIT,
} from './labels'

describe('the deepened war values', () => {
  it('labels every new stance, role, fate and siege choice', () => {
    expect(STANCE.disband.label).toBe('Disbanding')
    expect(ROLE.engineer_master.label).toBe('Master of engineers')
    expect(CONTRACT_STATUS.renewed.label).toBe('Renewed')
    expect(AGENT_STATUS.sleeper.label).toBe('Sleeper')
    expect(FATE.adopted.label).toBe('Adopted')
    expect(OPERATION.recruit_agent.label).toBe('Recruited an agent')
    expect(SIEGE_WORK.dam.label).toBe('Dam')
    expect(SACK_CHOICE.resettle.label).toBe("Settle the victors' people")
    expect(SIEGE_STATUS.betrayed.label).toBe('Betrayed from within')
    expect(STARVATION.hunger_sickness.label).toBe('Hunger sickness')
    expect(SIEGE_ACTION.divert_river.label).toBe('Turned the river')
    expect(DEFENCE.evacuate_by_sea.label).toBe('Left by sea')
  })

  it('names the new commanders, tactics, formations and command areas', () => {
    expect(TRAIT.river_crosser.label).toBe('River crosser')
    expect(TACTIC.fire_attack.label).toBe('Fire attack')
    expect(FORMATION.circle.label).toBe('Circle')
    expect(COMMAND_AREA.intelligence.label).toBe('Intelligence')
  })
})
