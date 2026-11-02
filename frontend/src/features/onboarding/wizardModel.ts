import {
  type CosmosSize,
  type GenesisRequest,
  type LanguageTexture,
  type LoreLanguage,
  type Rarity,
  type TechnologyEra,
  type WizardTemplate,
} from './api'

export const CREATOR_NAME_MAX = 60
export const SEED_MAX = 2000
export const TONE_MAX = 300
export const PERCENT_MAX = 100

export const WIZARD_STEPS = ['template', 'creator', 'world', 'review'] as const
export type WizardStep = (typeof WIZARD_STEPS)[number]

export const STEP_TITLE: Record<WizardStep, string> = {
  template: 'Template',
  creator: 'The Creator',
  world: 'The world',
  review: 'First sons',
}

export type WizardDraft = {
  template: WizardTemplate['key'] | null
  creatorName: string
  loreLanguage: LoreLanguage
  seed: string
  tone: string
  magic: number
  darkness: number
  technology: TechnologyEra
  language: LanguageTexture
  cosmos: CosmosSize
  peoples: number
  firstSons: Rarity[] | null
}

export type WizardDefaults = {
  magic: number
  darkness: number
  peoples: number
}

export function initialDraft(defaults: WizardDefaults): WizardDraft {
  return {
    template: null,
    creatorName: '',
    loreLanguage: 'english',
    seed: '',
    tone: '',
    magic: defaults.magic,
    darkness: defaults.darkness,
    technology: 'iron',
    language: 'free',
    cosmos: 'single',
    peoples: defaults.peoples,
    firstSons: null,
  }
}

export function applyTemplate(
  draft: WizardDraft,
  template: WizardTemplate | null,
  defaults: WizardDefaults
): WizardDraft {
  if (!template)
    return {
      ...initialDraft(defaults),
      creatorName: draft.creatorName,
      loreLanguage: draft.loreLanguage,
      firstSons: draft.firstSons,
    }
  return {
    ...draft,
    template: template.key,
    seed: template.seed,
    tone: template.tone,
    magic: template.magic,
    darkness: template.darkness,
    technology: template.technology,
    language: template.language,
    cosmos: template.cosmos,
    peoples: template.peoples,
  }
}

export function stepProblem(
  step: WizardStep,
  draft: WizardDraft,
  peoplesMax: number
): string | null {
  if (step === 'creator' && draft.creatorName.trim() === '')
    return 'Give the Creator a name.'
  if (step === 'world') {
    if (draft.seed.trim() === '') return 'Write a seed for the world.'
    if (draft.peoples < 1 || draft.peoples > peoplesMax)
      return `Between 1 and ${peoplesMax} first peoples.`
    if (
      [draft.magic, draft.darkness].some(
        (value) => value < 0 || value > PERCENT_MAX
      )
    )
      return 'Magic and darkness go from 0 to 100.'
  }
  return null
}

export function resizeFirstSons(
  current: Rarity[],
  count: number,
  fallback: Rarity
): Rarity[] {
  return Array.from(
    { length: count },
    (_, index) => current[index] ?? current[current.length - 1] ?? fallback
  )
}

export function toRequest(
  draft: WizardDraft,
  firstSons: Rarity[]
): GenesisRequest {
  return {
    creator_name: draft.creatorName.trim(),
    seed: draft.seed.trim(),
    tone: draft.tone.trim() || null,
    lore_language: draft.loreLanguage,
    first_sons: firstSons,
    wizard: {
      template: draft.template,
      magic: draft.magic,
      darkness: draft.darkness,
      technology: draft.technology,
      language: draft.language,
      cosmos: draft.cosmos,
      peoples: draft.peoples,
      tone: draft.tone.trim() || null,
      seed: draft.seed.trim(),
    },
  }
}
