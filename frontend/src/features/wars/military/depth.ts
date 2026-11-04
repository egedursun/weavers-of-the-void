import { useQuery } from '@tanstack/react-query'
import {
  Anchor,
  Axe,
  BadgeCheck,
  Banknote,
  Bone,
  Brain,
  CloudFog,
  Coins,
  Crown,
  Drama,
  Feather,
  Flame,
  Gavel,
  Gem,
  Ghost,
  Gift,
  HandHeart,
  Handshake,
  HeartPulse,
  KeySquare,
  Leaf,
  type LucideIcon,
  Map,
  Rocket,
  Sailboat,
  Scale,
  Ship,
  ShipWheel,
  Skull,
  Sparkles,
  Swords,
  Target,
  Unlock,
  Users,
  Waves,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { type Named } from './labels'

export type RecordTable = components['schemas']['RecordTableView']
export type RecordRow = components['schemas']['RecordRowView']
export type RecordColumn = components['schemas']['RecordColumnView']
export type BattleDepth = components['schemas']['BattleDepthView']
export type Vessel = components['schemas']['VesselView']
export type HullSpec = components['schemas']['HullSpecView']
export type Feud = components['schemas']['FeudView']
export type PeaceTerm = components['schemas']['PeaceTermView']
export type RecordValues = Record<string, unknown>

export const depthKeys = {
  records: (kind: string, scope: number | null) =>
    ['military', 'records', kind, scope] as const,
  battle: (id: number) => ['battles', id, 'depth'] as const,
  vessel: (id: number) => ['vessels', id] as const,
  hulls: ['vessels', 'hulls'] as const,
  feuds: (id: number | null) => ['feuds', id] as const,
  terms: (id: number) => ['wars', id, 'terms'] as const,
}

export function useRecords(kind: string, scope: number | null) {
  return useQuery({
    queryKey: depthKeys.records(kind, scope),
    queryFn: () =>
      unwrap(
        api.GET('/api/military/records/{kind}', {
          params: {
            path: { kind },
            query: scope === null ? {} : { scope_id: scope },
          },
        })
      ),
  })
}

export function useBattleDepth(id: number) {
  return useQuery({
    queryKey: depthKeys.battle(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/battles/{battle_id}/depth', {
          params: { path: { battle_id: id } },
        })
      ),
  })
}

export function useVessel(id: number, enabled = true) {
  return useQuery({
    queryKey: depthKeys.vessel(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/vessel', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useHulls() {
  return useQuery({
    queryKey: depthKeys.hulls,
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/vessels/hulls')),
  })
}

export function useFeuds(entityId: number | null) {
  return useQuery({
    queryKey: depthKeys.feuds(entityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/feuds', {
          params: { query: entityId === null ? {} : { entity_id: entityId } },
        })
      ),
  })
}

export function usePeaceTerms(warId: number) {
  return useQuery({
    queryKey: depthKeys.terms(warId),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars/{war_id}/terms', {
          params: { path: { war_id: warId } },
        })
      ),
  })
}

export const RECORD_ICON: Record<string, LucideIcon> = {
  unit_design: Axe,
  stack: Users,
  army_profile: Map,
  officer: BadgeCheck,
  contract: Banknote,
  war: Swords,
  siege: KeySquare,
  war_aim: Target,
  occupation: Crown,
  battle: Swords,
  captive_cohort: Users,
  captive: Unlock,
  peace_term: Handshake,
  spy_network: Drama,
  spy_agent: Drama,
  feud: Flame,
  vessel: Ship,
}

export const HULL: Record<string, Named> = {
  raft: { label: 'Raft', icon: Waves, tone: 'muted' },
  boat: { label: 'Boat', icon: Sailboat, tone: 'muted' },
  galley: { label: 'Galley', icon: ShipWheel, tone: 'gold' },
  longship: { label: 'Longship', icon: Sailboat, tone: 'warning' },
  cog: { label: 'Cog', icon: Ship, tone: 'info' },
  carrack: { label: 'Carrack', icon: Ship, tone: 'success' },
  warship: { label: 'Warship', icon: Swords, tone: 'danger' },
  light_sailer: { label: 'Light-sailer', icon: Feather, tone: 'verdigris' },
  bone_hull: { label: 'Bone hull', icon: Bone, tone: 'muted' },
  generation_ship: { label: 'Generation ship', icon: Rocket, tone: 'info' },
  skyship: { label: 'Skyship', icon: Sparkles, tone: 'verdigris' },
  living_ship: { label: 'Living ship', icon: Leaf, tone: 'success' },
}

export const ARMAMENT: Record<string, Named> = {
  rams: { label: 'Rams', icon: Axe, tone: 'warning' },
  missiles: { label: 'Missiles', icon: Target, tone: 'info' },
  siege_engines: { label: 'Siege engines', icon: KeySquare, tone: 'danger' },
  rites: { label: 'Rites', icon: Sparkles, tone: 'verdigris' },
}

export const VESSEL_STATUS: Record<string, Named> = {
  docked: { label: 'Docked', icon: Anchor, tone: 'muted' },
  afloat: { label: 'Afloat', icon: Sailboat, tone: 'success' },
  damaged: { label: 'Damaged', icon: HeartPulse, tone: 'warning' },
  wrecked: { label: 'Wrecked', icon: Skull, tone: 'danger' },
  ghost: { label: 'Ghost ship', icon: Ghost, tone: 'verdigris' },
}

export const FEUD_STATUS: Record<string, Named> = {
  active: { label: 'Burning', icon: Flame, tone: 'danger' },
  mediated: { label: 'Mediated', icon: HandHeart, tone: 'success' },
  faded: { label: 'Faded', icon: Leaf, tone: 'muted' },
  ended: { label: 'Ended', icon: Handshake, tone: 'info' },
}

export const FEUD_PARTY: Record<string, Named> = {
  house: { label: 'Between houses', icon: Crown, tone: 'gold' },
  community: { label: 'Between peoples', icon: Users, tone: 'info' },
}

export const TERM: Record<string, Named> = {
  cession: { label: 'Cession of land', icon: Map, tone: 'danger' },
  vassalage: { label: 'Vassalage', icon: Crown, tone: 'warning' },
  hostage: { label: 'Hostage', icon: Unlock, tone: 'warning' },
  reparations: { label: 'Reparations', icon: Coins, tone: 'gold' },
  tribute: { label: 'Tribute', icon: Banknote, tone: 'gold' },
  liberty: { label: 'Liberty', icon: Unlock, tone: 'success' },
  throne: { label: 'The throne', icon: Crown, tone: 'gold' },
  break_cult: { label: 'Break the cult', icon: Skull, tone: 'danger' },
  open_temples: {
    label: 'Open the temples',
    icon: Sparkles,
    tone: 'verdigris',
  },
  government: { label: 'New government', icon: Scale, tone: 'info' },
  marriage: { label: 'Marriage of houses', icon: HandHeart, tone: 'success' },
  demilitarised: { label: 'Demilitarised border', icon: Leaf, tone: 'success' },
  trade_concession: { label: 'Trade concession', icon: Coins, tone: 'info' },
  captive_release: {
    label: 'Release of captives',
    icon: Gift,
    tone: 'success',
  },
  champion: {
    label: 'Champions settle disputes',
    icon: Gavel,
    tone: 'warning',
  },
  white_peace: { label: 'White peace', icon: Handshake, tone: 'muted' },
}

export const FATE_OF: Record<string, Named> = {
  killed: { label: 'Killed', icon: Skull, tone: 'danger' },
  wounded: { label: 'Wounded', icon: HeartPulse, tone: 'warning' },
  maimed: { label: 'Maimed', icon: HeartPulse, tone: 'danger' },
  captured: { label: 'Captured', icon: Unlock, tone: 'info' },
}

export const MORALE_PART: Record<string, Named> = {
  leadership: { label: 'Leadership', icon: Crown, tone: 'gold' },
  faith: { label: 'Faith', icon: Sparkles, tone: 'verdigris' },
  babel: { label: 'Many tongues', icon: Brain, tone: 'warning' },
  beast_dread: { label: 'Dread of beasts', icon: Skull, tone: 'danger' },
  warned: { label: 'Warned by spies', icon: Drama, tone: 'info' },
  terror_taken: { label: 'Terror', icon: Ghost, tone: 'danger' },
  willpower: { label: 'Willpower', icon: Brain, tone: 'success' },
  flaring_items: { label: 'Flaring relics', icon: Flame, tone: 'warning' },
}

export const MAGIC_PART: Record<string, Named> = {
  fog: { label: 'Called fog', icon: CloudFog, tone: 'info' },
  healed: { label: 'Healed', icon: HeartPulse, tone: 'success' },
  raised: { label: 'Dead raised', icon: Ghost, tone: 'verdigris' },
  terror: { label: 'Terror', icon: Skull, tone: 'danger' },
  backlash: { label: 'Backlash', icon: Flame, tone: 'warning' },
}

export const CAUSE: Record<string, Named> = {
  claim: { label: 'A claim', icon: Crown, tone: 'gold' },
  holy_war: { label: 'Holy war', icon: Sparkles, tone: 'verdigris' },
  succession: { label: 'Succession', icon: Crown, tone: 'warning' },
  raid: { label: 'Raid', icon: Axe, tone: 'danger' },
  liberation: { label: 'Liberation', icon: Unlock, tone: 'success' },
  punitive: { label: 'Punishment', icon: Gavel, tone: 'danger' },
  declared: { label: 'Declared', icon: Swords, tone: 'danger' },
  independence: { label: 'Independence', icon: Unlock, tone: 'info' },
  resource: { label: 'Resources', icon: Coins, tone: 'gold' },
  trade_route: { label: 'Trade route', icon: Coins, tone: 'info' },
  ideology: { label: 'Ideology', icon: Brain, tone: 'info' },
  vendetta: { label: 'Vendetta', icon: Flame, tone: 'danger' },
  hostility: { label: 'Old hostility', icon: Swords, tone: 'muted' },
}

export function nameOf(table: Record<string, Named>, key: string): Named {
  return (
    table[key] ?? {
      label: key
        .replaceAll('_', ' ')
        .replace(/^./, (first) => first.toUpperCase()),
      icon: Sparkles,
      tone: 'muted',
    }
  )
}

export const ROLE: Record<string, Named> = {
  commander: { label: 'Commander', icon: Crown, tone: 'gold' },
  sub_commander: { label: 'Sub-commander', icon: Swords, tone: 'info' },
  quartermaster: { label: 'Quartermaster', icon: Coins, tone: 'success' },
  standard_bearer: {
    label: 'Standard bearer',
    icon: BadgeCheck,
    tone: 'warning',
  },
  surgeon: { label: 'Surgeon', icon: HeartPulse, tone: 'verdigris' },
}

export const CONTRACT_STATUS: Record<string, Named> = {
  active: { label: 'Under contract', icon: Handshake, tone: 'success' },
  unpaid: { label: 'Unpaid', icon: Banknote, tone: 'warning' },
  turned: { label: 'Turned on its employer', icon: Skull, tone: 'danger' },
  ended: { label: 'Contract ended', icon: Unlock, tone: 'muted' },
}

export const AGENT_STATUS: Record<string, Named> = {
  active: { label: 'In place', icon: Drama, tone: 'success' },
  caught: { label: 'Caught', icon: Unlock, tone: 'danger' },
  turned: { label: 'Turned', icon: Skull, tone: 'warning' },
  dead: { label: 'Dead', icon: Skull, tone: 'muted' },
  retired: { label: 'Retired', icon: Leaf, tone: 'muted' },
}

export const OWNER_KIND: Record<string, Named> = {
  polity: { label: 'Spies of a realm', icon: Crown, tone: 'gold' },
  faction: { label: 'Spies of a faction', icon: Users, tone: 'info' },
  cult: { label: 'Spies of a cult', icon: Sparkles, tone: 'verdigris' },
  community: { label: 'Spies of a people', icon: Users, tone: 'muted' },
}

export const SACK_CHOICE: Record<string, Named> = {
  mercy: { label: 'Mercy', icon: HandHeart, tone: 'success' },
  sack: { label: 'Sack', icon: Flame, tone: 'warning' },
  raze: { label: 'Raze', icon: Skull, tone: 'danger' },
}

export const SIEGE_WORK: Record<string, Named> = {
  circumvallation: { label: 'Ring of walls', icon: Map, tone: 'info' },
  towers: { label: 'Siege towers', icon: KeySquare, tone: 'warning' },
  rams: { label: 'Rams', icon: Axe, tone: 'danger' },
  mines: { label: 'Mines', icon: Bone, tone: 'warning' },
  countermines: { label: 'Countermines', icon: Bone, tone: 'info' },
  ladders: { label: 'Ladders', icon: Rocket, tone: 'muted' },
}

export const WALL_MATERIAL: Record<string, Named> = {
  timber: { label: 'Timber walls', icon: Leaf, tone: 'warning' },
  stone: { label: 'Stone walls', icon: KeySquare, tone: 'info' },
}

const GOVERNMENTS: Record<string, string> = {
  republic: 'a republic',
  monarchy: 'a monarchy',
  theocracy: 'a theocracy',
}

export function aimParamText(
  kind: string,
  params: Record<string, unknown>,
  names: Record<number, string>
): string | null {
  const named = (key: string) => {
    const value = params[key]
    return typeof value === 'number'
      ? (names[value] ?? `record ${value}`)
      : null
  }
  switch (kind) {
    case 'tribute':
    case 'loot':
      return typeof params.amount === 'number'
        ? `${kind === 'loot' ? 'Plunder' : 'Tribute'} of ${params.amount} wealth${typeof params.epochs === 'number' && params.epochs > 0 ? ` for ${params.epochs} epochs` : ''}`
        : null
    case 'convert':
      return named('god')
        ? `Turn them to ${named('god')}`
        : 'Turn them to our god'
    case 'press_claim':
      return typeof params.claim === 'number'
        ? 'Seat our claimant on their throne'
        : 'Press our claim'
    case 'revenge':
      return typeof params.memory === 'number'
        ? 'Avenge a wrong still remembered'
        : 'Avenge an old wrong'
    case 'change_government':
      return typeof params.government === 'string'
        ? `Make their realm ${GOVERNMENTS[params.government] ?? params.government.replaceAll('_', ' ')}`
        : null
    case 'liberate':
      return named('freed') ? `Free ${named('freed')}` : null
    case 'vassalise':
      return named('overlord') ? `Bend the knee to ${named('overlord')}` : null
    case 'destroy_cult':
      return named('cult') ? `Break ${named('cult')}` : null
    default:
      return named('target') ? `Take ${named('target')}` : null
  }
}

export const MATERIAL: Record<string, Named> = Object.fromEntries(
  Object.entries(MATERIAL_LABEL).map(([key, label]) => [
    key,
    { label, icon: Gem, tone: 'muted' as const },
  ])
)

export const SOCIAL_CLASS: Record<string, Named> = Object.fromEntries(
  Object.entries(CLASS_SPEC).map(([key, spec]) => [
    key,
    { label: spec.label, icon: spec.icon, tone: spec.tone },
  ])
)

export function termParamText(
  kind: string,
  params: Record<string, unknown>,
  names: Record<number, string>
): string | null {
  const named = (key: string) => {
    const value = params[key]
    return typeof value === 'number'
      ? (names[value] ?? `record ${value}`)
      : null
  }
  if (
    (kind === 'reparations' || kind === 'tribute') &&
    typeof params.amount === 'number'
  ) {
    return `${params.amount} wealth${typeof params.epochs === 'number' && params.epochs > 0 ? ` for ${params.epochs} epochs` : ''}`
  }
  if ((kind === 'cession' || kind === 'demilitarised') && named('region'))
    return named('region')
  if (kind === 'marriage' && named('first_house') && named('second_house'))
    return `${named('first_house')} weds ${named('second_house')}`
  return null
}
