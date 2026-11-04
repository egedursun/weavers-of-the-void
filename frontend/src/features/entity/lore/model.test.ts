import { describe, expect, it } from 'vitest'
import {
  artMediumValues,
  backlashKindValues,
  curseKindValues,
  ideologyTenetValues,
  itemClassValues,
  itemDeedValues,
  knowledgeBranchValues,
  legendArchetypeValues,
  magicSchoolValues,
  magicSourceValues,
  prophecyPredicateValues,
  prophecyStateValues,
  riteEffectKindValues,
  socialClassValues,
  speakerKindValues,
  traditionKindValues,
} from '@/api/generated/schema'
import {
  ARCHETYPES,
  BACKLASHES,
  CLASSES,
  CURSES,
  DEEDS,
  EFFECTS,
  ITEM_CLASSES,
  type LoreNamed,
  MEDIUMS,
  PREDICATES,
  PROPHECY_STATES,
  SCHOOLS,
  SOURCES,
  SPEAKER_KINDS,
  TENETS,
  TRADITION_KINDS,
  branchOf,
  fieldLabel,
  lookup,
} from './model'

const TABLES: [string, readonly string[], Record<string, LoreNamed>][] = [
  ['archetype', legendArchetypeValues, ARCHETYPES],
  ['tradition kind', traditionKindValues, TRADITION_KINDS],
  ['tenet', ideologyTenetValues, TENETS],
  ['social class', socialClassValues, CLASSES],
  ['magic school', magicSchoolValues, SCHOOLS],
  ['magic source', magicSourceValues, SOURCES],
  ['backlash', backlashKindValues, BACKLASHES],
  ['rite effect', riteEffectKindValues, EFFECTS],
  ['prophecy predicate', prophecyPredicateValues, PREDICATES],
  ['prophecy state', prophecyStateValues, PROPHECY_STATES],
  ['item class', itemClassValues, ITEM_CLASSES],
  ['curse', curseKindValues, CURSES],
  ['item deed', itemDeedValues, DEEDS],
  ['art medium', artMediumValues, MEDIUMS],
  ['speaker kind', speakerKindValues, SPEAKER_KINDS],
]

describe('lore labels', () => {
  it.each(TABLES)(
    'gives every %s a human label, an icon and a tone',
    (_, values, table) => {
      for (const value of values) {
        const spec = table[value]
        expect(spec, value).toBeDefined()
        expect(spec.label).not.toMatch(/_/)
        expect(spec.label.charAt(0)).toBe(spec.label.charAt(0).toUpperCase())
        expect(spec.icon).toBeTruthy()
        expect(spec.tone).toBeTruthy()
      }
    }
  )

  it('names every knowledge branch in plain words', () => {
    for (const branch of knowledgeBranchValues) {
      const spec = branchOf(branch)
      expect(spec.label).not.toMatch(/_/)
      expect(spec.icon).toBeTruthy()
    }
    expect(branchOf('gate_lore').label).toBe('Gate lore')
    expect(branchOf('warfare').label).toBe('Warfare')
  })

  it('never shows a raw key for an unknown value or field', () => {
    expect(lookup({}, 'new_kind_of_thing').label).toBe('New kind of thing')
    expect(fieldLabel('backlash_chance')).toBe('Backlash chance')
    expect(fieldLabel('some_new_field')).toBe('Some new field')
  })
})
