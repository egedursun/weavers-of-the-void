import {
  DEFAULT_IMAGE_STYLE,
  type ImageStyle,
  imageStyleProblem,
} from '@/features/images/imageStyles'
import {
  type ClimateEra,
  type CosmosShape,
  type CosmosSize,
  type DimensionKind,
  type GenesisRequest,
  type LanguageTexture,
  type LoreLanguage,
  type Rarity,
  type AgeCycle,
  type StorytellerProfile,
  type TechnologyEra,
  type WizardTemplate,
  type WorldAge,
  type WorldType,
} from './api'

export const CREATOR_NAME_MAX = 60
export const SEED_MAX = 2000
export const TONE_MAX = 300
export const PERCENT_MAX = 100
export const MOISTURE_MIN = -100
export const LAND_DEFAULTS = { sea: 50, mountains: 30, moisture: 0 }

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
  danger: number
  technology: TechnologyEra
  language: LanguageTexture
  cosmos: CosmosSize
  shape: CosmosShape
  layerKind: DimensionKind | null
  storyteller: StorytellerProfile
  ageCycle: AgeCycle
  worldType: WorldType | null
  seaPct: number | null
  mountainsPct: number | null
  moisturePct: number | null
  climateEra: ClimateEra | null
  worldAge: WorldAge | null
  prehistoryEpochs: number | null
  madeMinds: number | null
  informationReach: number | null
  peoples: number
  firstSons: Rarity[] | null
  imageStyle: ImageStyle
  imageStyleCustom: string
}

export type WizardDefaults = {
  magic: number
  danger: number
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
    danger: defaults.danger,
    technology: 'iron',
    language: 'free',
    cosmos: 'single',
    shape: 'one_sun',
    layerKind: null,
    storyteller: 'cyclic',
    ageCycle: 'linear',
    worldType: null,
    seaPct: null,
    mountainsPct: null,
    moisturePct: null,
    climateEra: null,
    worldAge: null,
    prehistoryEpochs: null,
    madeMinds: null,
    informationReach: null,
    peoples: defaults.peoples,
    firstSons: null,
    imageStyle: DEFAULT_IMAGE_STYLE,
    imageStyleCustom: '',
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
      storyteller: draft.storyteller,
      ageCycle: draft.ageCycle,
      firstSons: draft.firstSons,
      imageStyle: draft.imageStyle,
      imageStyleCustom: draft.imageStyleCustom,
    }
  return {
    ...draft,
    template: template.key,
    seed: template.seed,
    tone: template.tone,
    magic: template.magic,
    danger: template.danger,
    technology: template.technology,
    language: template.language,
    cosmos: template.cosmos,
    shape: template.shape,
    layerKind: null,
    storyteller: template.storyteller,
    worldType: template.world_type ?? null,
    seaPct: null,
    mountainsPct: null,
    moisturePct: null,
    climateEra: template.climate_era ?? null,
    worldAge: template.world_age ?? null,
    madeMinds: template.made_minds ?? null,
    informationReach: template.information_reach ?? null,
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
      [draft.magic, draft.danger].some(
        (value) => value < 0 || value > PERCENT_MAX
      )
    )
      return 'Magic and danger go from 0 to 100.'
    if (
      [draft.seaPct, draft.mountainsPct].some(
        (value) => value !== null && (value < 0 || value > PERCENT_MAX)
      )
    )
      return 'Water and high ground go from 0 to 100.'
    if (
      draft.moisturePct !== null &&
      (draft.moisturePct < MOISTURE_MIN || draft.moisturePct > PERCENT_MAX)
    )
      return 'Moisture goes from -100 to 100.'
    const style = imageStyleProblem(draft.imageStyle, draft.imageStyleCustom)
    if (style) return style
  }
  return null
}

export function landShaped(draft: WizardDraft): boolean {
  return (
    draft.seaPct !== null ||
    draft.mountainsPct !== null ||
    draft.moisturePct !== null
  )
}

export function shapeLand(
  draft: WizardDraft,
  on: boolean
): Partial<WizardDraft> {
  return on
    ? {
        seaPct: draft.seaPct ?? LAND_DEFAULTS.sea,
        mountainsPct: draft.mountainsPct ?? LAND_DEFAULTS.mountains,
        moisturePct: draft.moisturePct ?? LAND_DEFAULTS.moisture,
      }
    : { seaPct: null, mountainsPct: null, moisturePct: null }
}

export function shapeBlocked(draft: WizardDraft): string | null {
  return draft.cosmos === 'single'
    ? 'A single world has no further worlds to place; choose a small or large cosmos first'
    : null
}

export function effectiveShape(draft: WizardDraft): CosmosShape {
  return draft.cosmos === 'single' ? 'one_sun' : draft.shape
}

export function layerBlocked(draft: WizardDraft): string | null {
  return effectiveShape(draft) === 'layered'
    ? null
    : 'Only a layered cosmos has a second layer; choose the layered shape first'
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
    image_style: draft.imageStyle,
    image_style_custom:
      draft.imageStyle === 'custom' ? draft.imageStyleCustom.trim() : '',
    wizard: {
      template: draft.template,
      magic: draft.magic,
      danger: draft.danger,
      technology: draft.technology,
      language: draft.language,
      cosmos: draft.cosmos,
      shape: effectiveShape(draft),
      layer_kind: effectiveShape(draft) === 'layered' ? draft.layerKind : null,
      storyteller: draft.storyteller,
      age_cycle: draft.ageCycle,
      world_type: draft.worldType,
      sea_pct: draft.seaPct,
      mountains_pct: draft.mountainsPct,
      moisture_pct: draft.moisturePct,
      climate_era: draft.climateEra,
      world_age: draft.worldAge,
      prehistory_epochs: draft.prehistoryEpochs,
      made_minds: draft.madeMinds,
      information_reach: draft.informationReach,
      peoples: draft.peoples,
      tone: draft.tone.trim() || null,
      seed: draft.seed.trim(),
    },
  }
}
