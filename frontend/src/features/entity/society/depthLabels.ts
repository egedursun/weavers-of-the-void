import {
  Anvil,
  Ban,
  Beef,
  Building2,
  Church,
  Coins,
  Crown,
  Flame,
  Gem,
  HandCoins,
  Handshake,
  HardHat,
  HeartPulse,
  Landmark,
  Link,
  Lock,
  Pickaxe,
  Scale,
  Shield,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Swords,
  Trophy,
  Unlink,
  Users,
  UtensilsCrossed,
  Wheat,
  Wind,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Spec } from './labels'

type Schemas = components['schemas']
export type ShortfallEffect = Schemas['ShortfallEffect']
export type LabourReason = Schemas['LabourReason']
export type DriftCause = Schemas['DriftCause']
export type LoyaltyPart = Schemas['LoyaltyPart']
export type MobilityEvent = Schemas['MobilityEvent']
export type SocietyDepth = Schemas['SocietyDepthView']

export const EFFECT_SPEC: Record<ShortfallEffect, Spec> = {
  hunger: {
    label: 'Hunger',
    icon: UtensilsCrossed,
    tone: 'danger',
    hint: 'No grain, meat, fish or bread: hunger and famine',
  },
  herds: {
    label: 'Starving herds',
    icon: Beef,
    tone: 'warning',
    hint: 'No fodder: livestock starves',
  },
  cold: {
    label: 'Cold',
    icon: Snowflake,
    tone: 'info',
    hint: 'No fuel, timber or cloth: people die of cold, more so in cold lands',
  },
  sickness: {
    label: 'Sickness',
    icon: HeartPulse,
    tone: 'danger',
    hint: 'No medicine: adults fall sick and cannot work',
  },
  impiety: {
    label: 'Impiety',
    icon: Church,
    tone: 'verdigris',
    hint: 'No incense or sacred goods: piety falls, priests grow bitter',
  },
  status: {
    label: 'Lost status',
    icon: Gem,
    tone: 'gold',
    hint: 'No luxuries: nobles and merchants are slighted',
  },
  toil: {
    label: 'Toil',
    icon: Anvil,
    tone: 'warning',
    hint: 'No tools, ore or stone: prosperity falls',
  },
  insecurity: {
    label: 'Insecurity',
    icon: Shield,
    tone: 'danger',
    hint: 'No weapons, armour or mounts: defence falls',
  },
  arcane: {
    label: 'Arcane want',
    icon: Sparkles,
    tone: 'info',
    hint: 'No magical reagents: scholars stagnate',
  },
}
export const EFFECT_ORDER = Object.keys(EFFECT_SPEC) as ShortfallEffect[]

export const REASON_SPEC: Record<LabourReason, Spec> = {
  class: {
    label: 'By class',
    icon: Users,
    tone: 'muted',
    hint: 'Where each class works by custom',
  },
  price: {
    label: 'Prices',
    icon: Coins,
    tone: 'gold',
    hint: 'Dear goods pull workers into the trades that make them',
  },
  structure: {
    label: 'Workshops',
    icon: Building2,
    tone: 'info',
    hint: 'Each workshop draws workers into its trade',
  },
  resource: {
    label: 'Resources',
    icon: Pickaxe,
    tone: 'verdigris',
    hint: 'Worked mines, quarries and forests draw workers',
  },
  no_structure: {
    label: 'Nothing to work',
    icon: Ban,
    tone: 'danger',
    hint: 'No mine, no miners; no coast or fishery, no fishers',
  },
  corvee: {
    label: 'Corvee',
    icon: HardHat,
    tone: 'warning',
    hint: 'Farmhands taken for the great works',
  },
  held: {
    label: 'Held by you',
    icon: Lock,
    tone: 'gold',
    hint: 'A number of workers you set and hold',
  },
}

export const CAUSE_SPEC: Record<DriftCause, Spec> = {
  god: { label: 'Their god', icon: Sparkles, tone: 'gold' },
  ruler: { label: 'Their ruler', icon: Crown, tone: 'gold' },
  neighbours: { label: 'Neighbours', icon: Handshake, tone: 'info' },
  ideology: { label: "Scholars' ideas", icon: Scale, tone: 'verdigris' },
  war_fought: { label: 'War', icon: Swords, tone: 'warning' },
  war_won: { label: 'Victory', icon: Trophy, tone: 'success' },
  war_lost: { label: 'Defeat', icon: Skull, tone: 'danger' },
  plague: { label: 'Plague', icon: HeartPulse, tone: 'danger' },
  famine: { label: 'Famine', icon: Wheat, tone: 'warning' },
  trade: { label: 'Trade', icon: HandCoins, tone: 'gold' },
  conquest: { label: 'Conquest', icon: Landmark, tone: 'danger' },
}
export const CAUSE_ORDER = Object.keys(CAUSE_SPEC) as DriftCause[]

export const PART_SPEC: Record<LoyaltyPart, Spec> = {
  tribute: { label: 'Tribute paid', icon: HandCoins, tone: 'danger' },
  weariness: { label: 'War weariness', icon: Wind, tone: 'danger' },
  conquest: { label: 'Memory of conquest', icon: Skull, tone: 'danger' },
  tax: { label: 'Heavy tax', icon: Coins, tone: 'danger' },
  routes: { label: 'Trade routes', icon: Handshake, tone: 'success' },
  victories: { label: 'Victories', icon: Trophy, tone: 'success' },
  faith: { label: 'Shared faith', icon: Church, tone: 'success' },
  prosperity: { label: 'Prosperity', icon: Sprout, tone: 'success' },
  injustice: { label: 'Wrongful convictions', icon: Scale, tone: 'danger' },
  identity: { label: 'Bound to the realm', icon: Users, tone: 'success' },
  separatism: { label: 'Apart from its ruler', icon: Unlink, tone: 'danger' },
  suppression: { label: 'Mockery punished', icon: Ban, tone: 'danger' },
}

export const EVENT_SPEC: Record<MobilityEvent, Spec> = {
  ennobled: { label: 'Ennobled', icon: Crown, tone: 'gold' },
  enslaved: { label: 'Enslaved', icon: Link, tone: 'danger' },
  freed: { label: 'Freed', icon: Unlink, tone: 'success' },
  ruined: { label: 'Ruined', icon: Flame, tone: 'warning' },
}

export const STANDING_LABEL: Record<string, string> = {
  fed_pct: 'Fed',
  needs_met_pct: 'Needs met',
  luxury_pct: 'Luxury',
  wealth: 'Wealth',
  grievances: 'Grievances',
  benefits: 'Benefits',
  loyalty: 'Loyalty',
}

export function standingLabel(key: string): string {
  return STANDING_LABEL[key] ?? key.replaceAll('_', ' ')
}
