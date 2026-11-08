import {
  Axe,
  Flame,
  Ghost,
  PawPrint,
  Skull,
  Snowflake,
  Sparkles,
  Sword,
  Wheat,
  Package,
  Pickaxe,
} from 'lucide-react'
import {
  type components,
  damageTypeValues,
  ideologyTenetValues,
  itemClassValues,
  knowledgeBranchValues,
  legendArchetypeValues,
  riteEffectKindValues,
  techniqueValues,
  traditionKindValues,
} from '@/api/generated/schema'
import {
  ARCHETYPES,
  CLASSES,
  EFFECTS,
  ITEM_CLASSES,
  type LoreNamed,
  MAX_LEVEL,
  PERCENT,
  TENETS,
  TRADITION_KINDS,
  TRADITION_TERMS,
  VALUES,
  branchOf,
  lookup,
  sentence,
} from '../model'

type Catalog = components['schemas']['CustomCatalog']
export type KindParams = Record<
  string,
  number | string | string[] | Record<string, number>
>

export type KindParamField =
  | {
      key: string
      label: string
      kind: 'enum'
      table: Record<string, LoreNamed>
    }
  | { key: string; label: string; kind: 'number'; min: number; max: number }
  | {
      key: string
      label: string
      kind: 'table'
      table: Record<string, LoreNamed>
    }

type CatalogSpec = {
  title: string
  note: string
  noun: string
  baseLabel: string
  bases: Record<string, LoreNamed>
  params: KindParamField[]
  summary: (params: KindParams) => Record<string, number>
  summaryTable: Record<string, LoreNamed>
}

const MAX_SCALE = 500
const DAMAGE_ICON: Record<string, LoreNamed['icon']> = {
  cut: Sword,
  pierce: Sword,
  blunt: Axe,
  fire: Flame,
  cold: Snowflake,
  void: Skull,
  holy: Sparkles,
  magic: Sparkles,
  venom: Skull,
}

function named(
  values: readonly string[],
  known: Record<string, LoreNamed>
): Record<string, LoreNamed> {
  return Object.fromEntries(
    values.map((value) => [value, lookup(known, value)])
  )
}

const DAMAGE = Object.fromEntries(
  damageTypeValues.map((value) => [
    value,
    {
      label: sentence(value),
      icon: DAMAGE_ICON[value] ?? Sword,
      tone: 'danger',
    } satisfies LoreNamed,
  ])
)
const SUMMONS: Record<string, LoreNamed> = {
  spirit: { label: 'A spirit', icon: Ghost, tone: 'verdigris' },
  beast: { label: 'A beast', icon: PawPrint, tone: 'warning' },
  undead: { label: 'The risen dead', icon: Skull, tone: 'danger' },
}
const COSTS: Record<string, LoreNamed> = {
  food: { label: 'Food', icon: Wheat, tone: 'warning' },
  goods: { label: 'Goods', icon: Package, tone: 'warning' },
  ore: { label: 'Ore', icon: Pickaxe, tone: 'warning' },
}
const TRADITION_EFFECTS = named(
  [
    'cohesion',
    'satisfaction',
    'piety',
    'fertility',
    'martial',
    'placation',
    'harvest',
    'safety',
    'food_saved',
    'rest',
    'vigil',
  ],
  { ...TRADITION_TERMS, safety: TRADITION_TERMS.hospitality }
)
const BRANCHES = Object.fromEntries(
  knowledgeBranchValues.map((value) => [value, branchOf(value)])
)
const TECHNIQUES = Object.fromEntries(
  techniqueValues.map((value) => [
    value,
    {
      label: sentence(value),
      icon: Sparkles,
      tone: 'info',
    } satisfies LoreNamed,
  ])
)

function numbers(value: unknown): Record<string, number> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, number>)
    : {}
}

export function paramsOf(raw: unknown): KindParams {
  return raw && typeof raw === 'object' && !Array.isArray(raw)
    ? { ...(raw as KindParams) }
    : {}
}

export const KIND_CATALOG: Record<Catalog, CatalogSpec> = {
  technique: {
    title: 'Techniques of your own making',
    note: 'A new technique acts as the one it is built on wherever the world asks for it, gated by the branch and level you set.',
    noun: 'technique',
    baseLabel: 'Built on',
    bases: TECHNIQUES,
    params: [
      { key: 'branch', label: 'Branch', kind: 'enum', table: BRANCHES },
      {
        key: 'level',
        label: 'Level needed',
        kind: 'number',
        min: 1,
        max: MAX_LEVEL,
      },
    ],
    summary: (params) =>
      typeof params.level === 'number'
        ? { level: params.level }
        : ({} as Record<string, number>),
    summaryTable: { level: { label: 'Level', icon: Sparkles, tone: 'info' } },
  },
  tenet: {
    title: 'Tenets of your own making',
    note: 'A new tenet behaves as its base in quarrels and revolutions, but presses the values and calls to the classes you choose.',
    noun: 'tenet',
    baseLabel: 'Built on',
    bases: named(ideologyTenetValues, TENETS),
    params: [
      {
        key: 'values',
        label: 'Values it presses',
        kind: 'table',
        table: VALUES,
      },
      {
        key: 'appeal',
        label: 'Who it calls to',
        kind: 'table',
        table: CLASSES,
      },
    ],
    summary: (params) => numbers(params.values),
    summaryTable: VALUES,
  },
  tradition_kind: {
    title: 'Kinds of custom of your own making',
    note: 'A new kind of custom is kept as its base but costs and brings what you set.',
    noun: 'kind of custom',
    baseLabel: 'Kept like',
    bases: named(traditionKindValues, TRADITION_KINDS),
    params: [
      { key: 'cost', label: 'What it costs', kind: 'table', table: COSTS },
      {
        key: 'effects',
        label: 'What it brings',
        kind: 'table',
        table: TRADITION_EFFECTS,
      },
      {
        key: 'values',
        label: 'Values it presses',
        kind: 'table',
        table: VALUES,
      },
    ],
    summary: (params) => numbers(params.effects),
    summaryTable: TRADITION_EFFECTS,
  },
  archetype: {
    title: 'Kinds of tale of your own making',
    note: 'A new kind of tale works as its base in the world but teaches the moral you set.',
    noun: 'kind of tale',
    baseLabel: 'Told like',
    bases: named(legendArchetypeValues, ARCHETYPES),
    params: [
      {
        key: 'moral',
        label: 'The moral it teaches',
        kind: 'table',
        table: VALUES,
      },
    ],
    summary: (params) => numbers(params.moral),
    summaryTable: VALUES,
  },
  item_class: {
    title: 'Kinds of thing of your own making',
    note: 'A new kind of thing serves as its base but with the reach, cover, weight and wound you set.',
    noun: 'kind of thing',
    baseLabel: 'Used like',
    bases: named(itemClassValues, ITEM_CLASSES),
    params: [
      {
        key: 'damage_type',
        label: 'Wound it deals',
        kind: 'enum',
        table: DAMAGE,
      },
      { key: 'reach', label: 'Reach', kind: 'number', min: 0, max: PERCENT },
      { key: 'coverage', label: 'Cover', kind: 'number', min: 0, max: PERCENT },
      { key: 'weight', label: 'Weight', kind: 'number', min: 0, max: PERCENT },
    ],
    summary: (params) =>
      Object.fromEntries(
        ['reach', 'coverage', 'weight']
          .filter((key) => typeof params[key] === 'number')
          .map((key) => [key, Number(params[key])])
      ),
    summaryTable: {
      reach: { label: 'Reach', icon: Sword, tone: 'info' },
      coverage: { label: 'Cover', icon: Sparkles, tone: 'info' },
      weight: { label: 'Weight', icon: Axe, tone: 'muted' },
    },
  },
  rite_effect: {
    title: 'Workings of your own making',
    note: 'A new working acts as its base effect, scaled and shaped as you set.',
    noun: 'working',
    baseLabel: 'Works like',
    bases: named(riteEffectKindValues, EFFECTS),
    params: [
      {
        key: 'magnitude_pct',
        label: 'Strength (%)',
        kind: 'number',
        min: 0,
        max: MAX_SCALE,
      },
      {
        key: 'damage_type',
        label: 'Wound it deals',
        kind: 'enum',
        table: DAMAGE,
      },
      {
        key: 'summon_form',
        label: 'What it calls',
        kind: 'enum',
        table: SUMMONS,
      },
    ],
    summary: (params) =>
      typeof params.magnitude_pct === 'number'
        ? { strength: params.magnitude_pct - PERCENT }
        : ({} as Record<string, number>),
    summaryTable: {
      strength: { label: 'Strength', icon: Sparkles, tone: 'gold' },
    },
  },
}
