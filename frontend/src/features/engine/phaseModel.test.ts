import { describe, expect, it } from 'vitest'
import { type EnginePhase } from './api'
import { matchesQuery, phaseLabel, phasesByStage } from './phaseModel'

function phase(name: string, stage: EnginePhase['stage']): EnginePhase {
  return {
    name,
    stage,
    enabled: true,
    essential: false,
    heavy: false,
    runnable: true,
    rule_key: name,
  }
}

describe('engine phase model', () => {
  it('humanizes phase names', () => {
    expect(phaseLabel('dead_bonds_opening')).toBe('Dead bonds opening')
  })

  it('groups phases by stage in pipeline order', () => {
    const grouped = phasesByStage([
      phase('a', 'transition'),
      phase('b', 'tick'),
      phase('c', 'tick'),
    ])
    expect(grouped.get('tick')?.map((item) => item.name)).toEqual(['b', 'c'])
    expect([...grouped.keys()]).toEqual([
      'tick',
      'pre_transition',
      'transition',
      'post_transition',
    ])
  })

  it('searches by label', () => {
    expect(matchesQuery(phase('monster_raids', 'tick'), 'raid')).toBe(true)
    expect(matchesQuery(phase('monster_raids', 'tick'), 'plague')).toBe(false)
    expect(matchesQuery(phase('monster_raids', 'tick'), '  ')).toBe(true)
  })
})
