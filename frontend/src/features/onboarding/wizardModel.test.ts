import { describe, expect, it } from 'vitest'
import { type WizardTemplate } from './api'
import {
  applyTemplate,
  initialDraft,
  landShaped,
  layerBlocked,
  resizeFirstSons,
  shapeBlocked,
  shapeLand,
  stepProblem,
  toRequest,
} from './wizardModel'

const DEFAULTS = { magic: 50, danger: 50, peoples: 2 }
const TEMPLATE: WizardTemplate = {
  key: 'dark_fantasy',
  name: 'Dark fantasy',
  tone: 'gloomy',
  magic: 60,
  danger: 80,
  technology: 'iron',
  language: 'guttural',
  peoples: 3,
  cosmos: 'single',
  seed: 'Corpses of gods.',
  storyteller: 'rising',
  shape: 'one_sun',
  world_type: 'corpse_world',
  climate_era: null,
  world_age: null,
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
    expect(filled.danger).toBe(80)
    expect(filled.worldType).toBe('corpse_world')
    expect(filled.storyteller).toBe('rising')
    const cleared = applyTemplate(filled, null, DEFAULTS)
    expect(cleared.seed).toBe('')
    expect(cleared.creatorName).toBe('Aeron')
    expect(cleared.loreLanguage).toBe('turkish')
  })

  it('keeps the chosen storyteller through templates and sends it', () => {
    const draft = { ...initialDraft(DEFAULTS), storyteller: 'chaotic' as const }
    expect(initialDraft(DEFAULTS).storyteller).toBe('cyclic')
    const cleared = applyTemplate(draft, null, DEFAULTS)
    expect(cleared.storyteller).toBe('chaotic')
    expect(toRequest(cleared, ['common']).wizard?.storyteller).toBe('chaotic')
  })

  it('checks each step and builds the request', () => {
    const draft = initialDraft(DEFAULTS)
    expect(stepProblem('creator', draft, 5)).toBe('Give the Creator a name.')
    expect(stepProblem('seed', draft, 5)).toBe('Write a seed for the world.')
    expect(
      stepProblem('peoples', { ...draft, seed: 'Salt', peoples: 9 }, 5)
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

  it('sends the first world choices and leaves the rest to the seed', () => {
    const draft = { ...initialDraft(DEFAULTS), creatorName: 'A', seed: 'S' }
    expect(landShaped(draft)).toBe(false)
    const shaped = { ...draft, ...shapeLand(draft, true) }
    expect(landShaped(shaped)).toBe(true)
    const wizard = toRequest(
      { ...shaped, worldType: 'ocean', climateEra: 'rain', worldAge: 'old' },
      ['common']
    ).wizard
    expect(wizard?.world_type).toBe('ocean')
    expect(wizard?.sea_pct).toBe(50)
    expect(wizard?.climate_era).toBe('rain')
    expect(wizard?.world_age).toBe('old')
    expect(toRequest(draft, ['common']).wizard?.sea_pct).toBeNull()
    expect(stepProblem('land', { ...shaped, moisturePct: -150 }, 5)).toMatch(
      /Moisture/
    )
  })

  it('places further worlds by shape only when there are any', () => {
    const single = initialDraft(DEFAULTS)
    expect(shapeBlocked(single)).not.toBeNull()
    expect(layerBlocked(single)).not.toBeNull()
    const layered = {
      ...single,
      cosmos: 'small' as const,
      shape: 'layered' as const,
      layerKind: 'astral' as const,
    }
    expect(shapeBlocked(layered)).toBeNull()
    expect(layerBlocked(layered)).toBeNull()
    expect(toRequest(layered, ['common']).wizard?.layer_kind).toBe('astral')
    const back = { ...layered, cosmos: 'single' as const }
    expect(toRequest(back, ['common']).wizard?.shape).toBe('one_sun')
    expect(toRequest(back, ['common']).wizard?.layer_kind).toBeNull()
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
