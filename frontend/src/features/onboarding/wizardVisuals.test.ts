import { type LucideIcon } from 'lucide-react'
import { describe, expect, it } from 'vitest'
import {
  AGE_CYCLE_ICON,
  AGE_ICON,
  CLIMATE_ICON,
  COSMOS_ICON,
  LANGUAGE_ICON,
  LORE_LANGUAGE_ICON,
  SHAPE_ICON,
  STEP_ICON,
  STORYTELLER_ICON,
  TECHNOLOGY_ICON,
  TEMPLATE_ICON,
} from './wizardVisuals'

const TABLES: Record<string, Record<string, LucideIcon>> = {
  steps: STEP_ICON,
  templates: TEMPLATE_ICON,
  shapes: SHAPE_ICON,
  climates: CLIMATE_ICON,
  ages: AGE_ICON,
  technologies: TECHNOLOGY_ICON,
  languages: LANGUAGE_ICON,
  sizes: COSMOS_ICON,
  storytellers: STORYTELLER_ICON,
  cycles: AGE_CYCLE_ICON,
  lore: LORE_LANGUAGE_ICON,
}

describe('wizard visuals', () => {
  it('gives every choice of a step its own icon', () => {
    for (const [name, table] of Object.entries(TABLES)) {
      const icons = Object.values(table)
      const twins = Object.keys(table).filter(
        (_, index) => icons.indexOf(icons[index]) !== index
      )
      expect(twins, name).toEqual([])
    }
  })
})
