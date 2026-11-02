import {
  type BondView,
  type EntityDetail,
  type EntityRecord,
  type EntityType,
  type EntityTypeInfo,
  type WorldState,
} from '../api/types'
import { COMMUNITY_TYPES, THINKING_TYPES } from '../constants'

export type WarRef = {
  warId: number
  label: string
}

export type DebtRef = {
  bondId: number
  label: string
}

export type PickRef = {
  value: number
  label: string
}

export type EntityContext = {
  detail: EntityDetail
  entity: EntityRecord
  type: EntityType
  canon: boolean
  dead: boolean
  flags: ReadonlySet<string>
  bonds: BondView[]
  wars: WarRef[]
  debts: DebtRef[]
  captives: PickRef[]
  tributes: PickRef[]
  multiWorld: boolean
  containers: EntityType[]
  state: WorldState | undefined
}

export function isCommunity(type: EntityType): boolean {
  return COMMUNITY_TYPES.includes(type)
}

export function isThinking(type: EntityType): boolean {
  return THINKING_TYPES.includes(type)
}

export function isLiving(type: EntityType): boolean {
  return type === 'mortal' || isCommunity(type)
}

function warsOf(entity: EntityRecord, bonds: BondView[]): WarRef[] {
  const seen = new Map<number, WarRef>()
  for (const bond of bonds) {
    if (bond.war_id === null || bond.state !== 'active') continue
    if (seen.has(bond.war_id)) continue
    const label =
      bond.kind === 'party_to' && bond.outgoing
        ? (bond.other?.name ?? `War ${bond.war_id}`)
        : bond.kind === 'party_to'
          ? entity.name
          : `${bond.other?.name ?? 'War'} (war ${bond.war_id})`
    seen.set(bond.war_id, { warId: bond.war_id, label })
  }
  return [...seen.values()]
}

function debtsOf(bonds: BondView[]): DebtRef[] {
  return bonds
    .filter((bond) => bond.kind === 'owes' && bond.state === 'active')
    .map((bond) => ({
      bondId: bond.id,
      label: bond.outgoing
        ? `Owes ${bond.other?.name ?? 'someone'}${bond.debt_amount ? ` ${bond.debt_amount}` : ''}`
        : `${bond.other?.name ?? 'Someone'} owes${bond.debt_amount ? ` ${bond.debt_amount}` : ''}`,
    }))
}

function captivesOf(entity: EntityRecord, bonds: BondView[]): PickRef[] {
  return bonds
    .filter((bond) => bond.kind === 'holds_captive' && bond.state === 'active')
    .map((bond) => {
      const captiveId = bond.outgoing ? (bond.other?.id ?? 0) : entity.id
      const captive = bond.outgoing
        ? (bond.other?.name ?? 'Prisoner')
        : entity.name
      const captor = bond.outgoing
        ? entity.name
        : (bond.other?.name ?? 'a captor')
      return { value: captiveId, label: `${captive}, held by ${captor}` }
    })
    .filter((item) => item.value > 0)
}

function tributesOf(entity: EntityRecord, bonds: BondView[]): PickRef[] {
  return bonds
    .filter((bond) => bond.kind === 'pays_tribute' && bond.state === 'active')
    .map((bond) => ({
      value: bond.id,
      label: bond.outgoing
        ? `${entity.name} pays ${bond.other?.name ?? 'a ruler'}`
        : `${bond.other?.name ?? 'Someone'} pays ${entity.name}`,
    }))
}

export function buildContext(
  detail: EntityDetail,
  bonds: BondView[],
  state: WorldState | undefined,
  types: EntityTypeInfo[]
): EntityContext {
  const entity = detail.entity
  const info = types.find((item) => item.key === entity.entity_type)
  return {
    detail,
    entity,
    type: entity.entity_type,
    canon: entity.status === 'canon',
    dead: entity.status === 'dead',
    flags: new Set<string>(detail.flags),
    bonds,
    wars: warsOf(entity, bonds),
    debts: debtsOf(bonds),
    captives: captivesOf(entity, bonds),
    tributes: tributesOf(entity, bonds),
    multiWorld: (state?.worlds.length ?? 0) > 1,
    containers: info?.containers ?? [],
    state,
  }
}
