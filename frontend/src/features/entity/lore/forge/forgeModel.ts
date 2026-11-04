import {
  BookOpen,
  CalendarHeart,
  Snowflake,
  Sprout,
  Swords,
  Wheat,
} from 'lucide-react'
import {
  artMediumValues,
  ideologyTenetValues,
  itemClassValues,
  knowledgeBranchValues,
  legendArchetypeValues,
  magicSchoolValues,
  magicSourceValues,
  prophecyPredicateValues,
  traditionKindValues,
} from '@/api/generated/schema'
import {
  ARCHETYPES,
  ITEM_CLASSES,
  LORE_KIND,
  type LoreKind,
  type LoreNamed,
  MAX_LEVEL,
  MAX_POWER,
  MEDIUMS,
  PERCENT,
  PREDICATES,
  SCHOOLS,
  SOURCES,
  TENETS,
  TRADITION_KINDS,
  branchOf,
  lookup,
} from '../model'

export type ForgeKind = LoreKind | 'knowledge'

export type ForgeField =
  | {
      key: string
      label: string
      kind: 'enum'
      table: Record<string, LoreNamed>
      required?: boolean
    }
  | {
      key: string
      label: string
      kind: 'multi'
      table: Record<string, LoreNamed>
      required?: boolean
    }
  | {
      key: string
      label: string
      kind: 'number'
      min: number
      max: number
      initial: number
    }

export type ForgeDraft = Record<string, string | number | string[]>

function named<T extends string>(
  values: readonly T[],
  known: Record<T, LoreNamed>
): Record<string, LoreNamed> {
  return Object.fromEntries(
    values.map((value) => [value, lookup(known, value)])
  )
}

export const CALENDAR_SLOTS: Record<string, LoreNamed> = {
  sowing: { label: 'At the sowing', icon: Sprout, tone: 'verdigris' },
  harvest: { label: 'At the harvest', icon: Wheat, tone: 'gold' },
  midwinter: { label: 'In the dead of winter', icon: Snowflake, tone: 'info' },
  campaign: { label: 'In the season of war', icon: Swords, tone: 'danger' },
  holy_day: {
    label: 'On a holy day in the sky',
    icon: CalendarHeart,
    tone: 'warning',
  },
}
const BRANCHES = Object.fromEntries(
  knowledgeBranchValues.map((value) => [value, branchOf(value)])
)

export const FORGE_KIND: Record<ForgeKind, LoreNamed> = {
  ...LORE_KIND,
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'info' },
}

export const FORGE_KINDS = Object.keys(FORGE_KIND) as ForgeKind[]

export function isForgeKind(
  kind: string | null | undefined
): kind is ForgeKind {
  return (
    Boolean(kind) && (FORGE_KINDS as readonly string[]).includes(kind ?? '')
  )
}

export const FORGE_FIELDS: Record<ForgeKind, ForgeField[]> = {
  language: [],
  legend: [
    {
      key: 'archetype',
      label: 'Kind of tale',
      kind: 'enum',
      table: named(legendArchetypeValues, ARCHETYPES),
      required: true,
    },
    {
      key: 'credence',
      label: 'Belief in it',
      kind: 'number',
      min: 0,
      max: PERCENT,
      initial: 30,
    },
  ],
  tradition: [
    {
      key: 'kind',
      label: 'Kind of custom',
      kind: 'enum',
      table: named(traditionKindValues, TRADITION_KINDS),
      required: true,
    },
    {
      key: 'calendar_slot',
      label: 'When it is kept',
      kind: 'enum',
      table: CALENDAR_SLOTS,
    },
  ],
  ideology: [
    {
      key: 'tenets',
      label: 'Tenets',
      kind: 'multi',
      table: named(ideologyTenetValues, TENETS),
      required: true,
    },
  ],
  rite: [
    {
      key: 'school',
      label: 'School',
      kind: 'enum',
      table: named(magicSchoolValues, SCHOOLS),
      required: true,
    },
    {
      key: 'source',
      label: 'Drawn from',
      kind: 'enum',
      table: named(magicSourceValues, SOURCES),
    },
    {
      key: 'power',
      label: 'Power',
      kind: 'number',
      min: 1,
      max: MAX_POWER,
      initial: 3,
    },
  ],
  prophecy: [
    {
      key: 'predicate',
      label: 'What must happen',
      kind: 'enum',
      table: named(prophecyPredicateValues, PREDICATES),
      required: true,
    },
    {
      key: 'certainty',
      label: 'Certainty',
      kind: 'number',
      min: 0,
      max: PERCENT,
      initial: 50,
    },
  ],
  item: [
    {
      key: 'item_class',
      label: 'Kind of thing',
      kind: 'enum',
      table: named(itemClassValues, ITEM_CLASSES),
      required: true,
    },
    {
      key: 'quality',
      label: 'Quality',
      kind: 'number',
      min: 0,
      max: PERCENT,
      initial: 50,
    },
  ],
  artwork: [
    {
      key: 'medium',
      label: 'Medium',
      kind: 'enum',
      table: named(artMediumValues, MEDIUMS),
      required: true,
    },
    {
      key: 'quality',
      label: 'Quality',
      kind: 'number',
      min: 0,
      max: PERCENT,
      initial: 50,
    },
  ],
  knowledge: [
    {
      key: 'branch',
      label: 'Branch',
      kind: 'enum',
      table: BRANCHES,
      required: true,
    },
    {
      key: 'level',
      label: 'Level',
      kind: 'number',
      min: 1,
      max: MAX_LEVEL,
      initial: 1,
    },
  ],
}

export function initialDraft(fields: readonly ForgeField[]): ForgeDraft {
  return Object.fromEntries(
    fields.map((field) => [
      field.key,
      field.kind === 'number'
        ? field.initial
        : field.kind === 'multi'
          ? []
          : '',
    ])
  )
}

export function missingField(
  fields: readonly ForgeField[],
  draft: ForgeDraft
): ForgeField | null {
  return (
    fields.find((field) => {
      if (field.kind === 'number' || !field.required) return false
      const value = draft[field.key]
      return Array.isArray(value) ? value.length === 0 : !value
    }) ?? null
  )
}

export function forgeValues(
  fields: readonly ForgeField[],
  draft: ForgeDraft
): Record<string, string | number | string[]> {
  return Object.fromEntries(
    fields
      .map((field) => [field.key, draft[field.key]] as const)
      .filter(
        ([, value]) =>
          value !== '' && !(Array.isArray(value) && value.length === 0)
      )
  )
}
