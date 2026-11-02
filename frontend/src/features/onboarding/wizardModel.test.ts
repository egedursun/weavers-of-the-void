import { describe, expect, it } from 'vitest'
import { type WizardTemplate } from './api'
import {
  applyTemplate,
  initialDraft,
  resizeFirstSons,
  stepProblem,
  toRequest,
} from './wizardModel'

const DEFAULTS = { magic: 50, darkness: 50, peoples: 2 }
const TEMPLATE: WizardTemplate = {
  key: 'dark_fantasy',
  name: 'Dark fantasy',
  tone: 'gloomy',
  magic: 60,
  darkness: 80,
  technology: 'iron',
  language: 'guttural',
  peoples: 3,
  cosmos: 'single',
  seed: 'Corpses of gods.',
}

describe('genesis wizard model', () => {
  it('defaults the lore language to English', () => {
    expect(initialDraft(DEFAULTS).loreLanguage).toBe('english')
  })

  it('fills and clears a template while keeping the Creator', () => {
    const named = {
      ...initialDraft(DEFAULTS),
      creatorName: 'Aeron',
      loreLanguage: 'turkish' as const,
    }
    const filled = applyTemplate(named, TEMPLATE, DEFAULTS)
    expect(filled.seed).toBe('Corpses of gods.')
    expect(filled.darkness).toBe(80)
    const cleared = applyTemplate(filled, null, DEFAULTS)
    expect(cleared.seed).toBe('')
    expect(cleared.creatorName).toBe('Aeron')
    expect(cleared.loreLanguage).toBe('turkish')
  })

  it('checks each step and builds the request', () => {
    const draft = initialDraft(DEFAULTS)
    expect(stepProblem('creator', draft, 5)).toBe('Give the Creator a name.')
    expect(
      stepProblem('world', { ...draft, seed: 'Salt', peoples: 9 }, 5)
    ).toMatch(/first peoples/)
    const request = toRequest(
      { ...draft, creatorName: ' Aeron ', seed: ' Salt ' },
      ['common', 'rare']
    )
    expect(request.creator_name).toBe('Aeron')
    expect(request.lore_language).toBe('english')
    expect(request.wizard?.peoples).toBe(2)
    expect(request.first_sons).toEqual(['common', 'rare'])
  })

  it('resizes the first sons keeping the earlier picks', () => {
    expect(resizeFirstSons(['rare', 'epic'], 3, 'common')).toEqual([
      'rare',
      'epic',
      'epic',
    ])
    expect(resizeFirstSons(['rare', 'epic'], 1, 'common')).toEqual(['rare'])
    expect(resizeFirstSons([], 2, 'common')).toEqual(['common', 'common'])
  })
})
