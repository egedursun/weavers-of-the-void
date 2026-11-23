import {
  knowledgeBranchValues,
  travelMethodValues,
} from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { type ComboboxOption } from '@/components/domain/RecordCombobox'
import { wordOf } from '@/features/entity/affairs/labels'
import {
  type CosmosView,
  type EntityType,
  type ForeignGodRecord,
  type KnowledgeView,
  type NameEntry,
  type ThreadRecord,
  type WorldState,
} from '../api/types'
import { COMMUNITY_TYPES } from '../constants'
import { type EntityContext } from './context'
import { humanize } from './schema'

export type PickerSpec =
  | {
      source: 'entity'
      types?: readonly EntityType[]
      sameType?: boolean
      containers?: boolean
      statuses?: readonly string[]
    }
  | { source: 'son'; status: 'living' | 'dead' | 'any' }
  | { source: 'foreign-god'; sameWorld?: boolean }
  | { source: 'world'; excludeOwn?: boolean }
  | { source: 'route' }
  | { source: 'knowledge'; unknownOnly?: boolean }
  | { source: 'war' }
  | { source: 'debt' }
  | { source: 'captive' }
  | { source: 'tribute' }
  | { source: 'thread' }

export type PickerData = {
  names: NameEntry[]
  state: WorldState | undefined
  cosmos: CosmosView | undefined
  knowledge: KnowledgeView[]
  foreignGods: ForeignGodRecord[]
  threads: ThreadRecord[]
}

const MORTAL: readonly EntityType[] = ['mortal']
const CANON_ONLY: readonly string[] = ['canon']

export const DEFAULT_PICKERS: Record<string, PickerSpec> = {
  son_id: { source: 'son', status: 'living' },
  god_id: { source: 'foreign-god' },
  foreign_god_id: { source: 'foreign-god' },
  world_id: { source: 'world', excludeOwn: true },
  route_id: { source: 'route' },
  knowledge_id: { source: 'knowledge', unknownOnly: true },
  war_id: { source: 'war' },
  bond_id: { source: 'debt' },
  captive_id: { source: 'captive' },
  tribute_id: { source: 'tribute' },
  thread_id: { source: 'thread' },
  region_id: { source: 'entity', types: ['region'] },
  place_id: { source: 'entity', types: ['place', 'region'] },
  species_id: { source: 'entity', types: ['species'] },
  monster_id: { source: 'entity', types: ['species', 'outer_being'] },
  soul_id: { source: 'entity', types: ['spirit'] },
  mortal_id: { source: 'entity', types: MORTAL },
  hero_id: { source: 'entity', types: MORTAL },
  heir_id: { source: 'entity', types: MORTAL },
  ruler_id: { source: 'entity', types: MORTAL },
  victim_id: { source: 'entity', types: MORTAL },
  community_id: { source: 'entity', types: COMMUNITY_TYPES },
  cult_id: { source: 'entity', types: ['cult'] },
  faction_id: { source: 'entity', types: ['faction'] },
  army_id: { source: 'entity', types: ['army'] },
  legend_id: { source: 'entity', types: ['legend'] },
  prophecy_id: { source: 'entity', types: ['prophecy'] },
  event_id: { source: 'entity', types: ['event'] },
  temple_id: { source: 'entity', types: ['structure'] },
  location_id: { source: 'entity', containers: true },
  other_id: { source: 'entity', sameType: true },
}

function worldName(state: WorldState | undefined, worldId: number | null) {
  if (worldId === null) return undefined
  return state?.worlds.find((world) => world.id === worldId)?.name
}

function joinHint(...parts: (string | undefined | null)[]): string | undefined {
  const shown = parts.filter((part): part is string => Boolean(part))
  return shown.length ? shown.join(' · ') : undefined
}

function entityOptions(
  spec: Extract<PickerSpec, { source: 'entity' }>,
  ctx: EntityContext,
  data: PickerData
): ComboboxOption[] {
  const types = spec.sameType
    ? [ctx.type]
    : spec.containers
      ? ctx.containers
      : spec.types
  const statuses = spec.statuses ?? CANON_ONLY
  const multi = ctx.multiWorld
  return data.names
    .filter(
      (entry) =>
        entry.kind === 'entity' &&
        entry.id !== ctx.entity.id &&
        (!types || types.includes(entry.type as EntityType)) &&
        (!entry.status || statuses.includes(entry.status))
    )
    .map((entry) => ({
      value: String(entry.id),
      label: entry.name,
      hint: joinHint(
        humanize(entry.type),
        multi ? worldName(data.state, entry.world_id ?? null) : undefined
      ),
    }))
}

function sonOptions(
  status: 'living' | 'dead' | 'any',
  data: PickerData
): ComboboxOption[] {
  return (data.state?.sons ?? [])
    .filter((view) => {
      const dead = view.son.status === 'dead'
      if (status === 'living') return !dead
      if (status === 'dead') return dead
      return true
    })
    .map((view) => ({
      value: String(view.son.id),
      label: view.son.name,
      hint: joinHint(
        view.son.title,
        worldName(data.state, view.son.current_world_id)
      ),
    }))
}

export function optionsFor(
  spec: PickerSpec,
  ctx: EntityContext,
  data: PickerData
): ComboboxOption[] {
  switch (spec.source) {
    case 'entity':
      return entityOptions(spec, ctx, data)
    case 'son':
      return sonOptions(spec.status, data)
    case 'foreign-god':
      return data.foreignGods
        .filter(
          (god) =>
            god.status !== 'dead' &&
            (!spec.sameWorld || god.world_id === ctx.entity.world_id)
        )
        .map((god) => ({
          value: String(god.id),
          label: god.name,
          hint: joinHint(god.title, worldName(data.state, god.world_id)),
        }))
    case 'world':
      return (data.state?.worlds ?? [])
        .filter(
          (world) =>
            !(spec.excludeOwn && world.id === ctx.entity.world_id) &&
            world.discovery !== 'forgotten'
        )
        .map((world) => ({
          value: String(world.id),
          label: world.name,
          hint: humanize(world.world_type),
        }))
    case 'route': {
      const worlds = data.cosmos?.worlds ?? []
      const name = (id: number) =>
        worlds.find((item) => item.world.id === id)?.world.name ?? `World ${id}`
      return (data.cosmos?.routes ?? [])
        .filter(
          (route) =>
            route.active &&
            route.known &&
            (route.world_a_id === ctx.entity.world_id ||
              route.world_b_id === ctx.entity.world_id)
        )
        .map((route) => {
          const other =
            route.world_a_id === ctx.entity.world_id
              ? route.world_b_id
              : route.world_a_id
          return {
            value: String(route.id),
            label: name(other),
            hint: joinHint(
              wordOf(travelMethodValues, route.method),
              `${plural(route.duration_epochs, 'epoch', 'epochs')}`
            ),
          }
        })
    }
    case 'knowledge': {
      const known = new Set(
        ctx.bonds
          .filter((bond) => bond.kind === 'knows' && bond.outgoing)
          .map((bond) => bond.other?.id)
      )
      return data.knowledge
        .filter((item) => !spec.unknownOnly || !known.has(item.knowledge.id))
        .map((item) => ({
          value: String(item.knowledge.id),
          label: item.knowledge.name,
          hint: joinHint(
            item.branch
              ? wordOf(knowledgeBranchValues, item.branch)
              : undefined,
            ctx.multiWorld
              ? worldName(data.state, item.knowledge.world_id)
              : undefined
          ),
        }))
    }
    case 'war':
      return ctx.wars.map((war) => ({
        value: String(war.warId),
        label: war.label,
      }))
    case 'debt':
      return ctx.debts.map((debt) => ({
        value: String(debt.bondId),
        label: debt.label,
      }))
    case 'captive':
      return ctx.captives.map((item) => ({
        value: String(item.value),
        label: item.label,
      }))
    case 'tribute':
      return ctx.tributes.map((item) => ({
        value: String(item.value),
        label: item.label,
      }))
    case 'thread':
      return data.threads
        .filter((thread) => thread.status === 'open')
        .map((thread) => ({
          value: String(thread.id),
          label: thread.text,
          hint: `Epoch ${thread.epoch}`,
        }))
  }
}
