import { describe, expect, it } from 'vitest'
import { type WorldSettings } from './api'
import { draftOf, patchFrom } from './worldSettingsModel'

const SETTINGS: WorldSettings = {
  fate_mode: 'auto',
  son_distribution: 'auto',
  mortal_agents_per_epoch: 4,
  council_every_epochs: 4,
  mortal_agent_parallelism: 1,
  llm_enabled: true,
  image_generation: false,
}

describe('world settings patch', () => {
  it('sends only what changed', () => {
    const draft = { ...draftOf(SETTINGS), fateAuto: false, council: '0' }
    expect(patchFrom(SETTINGS, draft)).toEqual({
      automatic_mortal_agents: false,
      fate_mode: 'off',
      council_every_epochs: 0,
    })
  })

  it('switches mortal agents to automatic and rejects bad numbers', () => {
    expect(
      patchFrom(SETTINGS, { ...draftOf(SETTINGS), automaticMortals: true })
    ).toEqual({ automatic_mortal_agents: true })
    expect(patchFrom(SETTINGS, { ...draftOf(SETTINGS), council: '1.5' })).toBe(
      'Use whole numbers only.'
    )
    expect(patchFrom(SETTINGS, draftOf(SETTINGS))).toBe('Nothing has changed.')
  })
})
