import {
  ArrowLeftRight,
  Bath,
  Building2,
  Castle,
  Church,
  Coins,
  Factory,
  Flag,
  Gift,
  Hammer,
  HandCoins,
  Handshake,
  Home,
  Landmark,
  type LucideIcon,
  Map,
  PiggyBank,
  Plane,
  Scale,
  Shovel,
  Swords,
  Users,
  Vault,
  Wheat,
  Crown,
  Cog,
  Equal,
  Award,
  Briefcase,
  CircleSlash,
  Bot,
  Lock,
  Hourglass,
  CheckCheck,
  XCircle,
  Megaphone,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const ORDERS_ICON: LucideIcon = Scale

export const TAB_ICONS = {
  order: Scale,
  saving: PiggyBank,
  exchange: ArrowLeftRight,
  trade: Factory,
  travel: Plane,
} as const

export const OWNERSHIP: Record<Schema['OwnershipRegime'], Named> = {
  household: { label: 'Households', icon: Home, tone: 'success' },
  kin_group: { label: 'Kin groups', icon: Users, tone: 'verdigris' },
  community: { label: 'The community', icon: Users, tone: 'info' },
  temple: { label: 'Temples', icon: Church, tone: 'gold' },
  ruler: { label: 'The ruler', icon: Crown, tone: 'warning' },
  state: { label: 'The state', icon: Landmark, tone: 'info' },
  private: { label: 'Private owners', icon: Briefcase, tone: 'gold' },
  cooperative: { label: 'Cooperatives', icon: Handshake, tone: 'success' },
  company: { label: 'Companies', icon: Building2, tone: 'muted' },
  common: { label: 'Held in common', icon: Map, tone: 'verdigris' },
  none: { label: 'No one', icon: CircleSlash, tone: 'muted' },
}

export const ALLOCATION: Record<Schema['AllocationMode'], Named> = {
  market: { label: 'Market', icon: Coins, tone: 'gold' },
  redistribution: { label: 'Redistribution', icon: Vault, tone: 'info' },
  command: { label: 'Command', icon: Megaphone, tone: 'warning' },
  obligation: { label: 'Dues and services', icon: Wheat, tone: 'muted' },
  gift: { label: 'Gift', icon: Gift, tone: 'verdigris' },
  need: { label: 'Need', icon: HandCoins, tone: 'success' },
  abundance: { label: 'Abundance', icon: Award, tone: 'success' },
}

export const LABOUR: Record<Schema['OrderLabour'], Named> = {
  free: { label: 'Free', icon: Flag, tone: 'success' },
  kin: { label: 'Kin', icon: Users, tone: 'verdigris' },
  corvee: { label: 'Corvée', icon: Shovel, tone: 'warning' },
  serf: { label: 'Serf', icon: Wheat, tone: 'warning' },
  bound: { label: 'Bound', icon: Lock, tone: 'danger' },
  enslaved: { label: 'Enslaved', icon: Lock, tone: 'danger' },
  conscripted: { label: 'Conscripted', icon: Swords, tone: 'warning' },
  cooperative: { label: 'Cooperative', icon: Handshake, tone: 'success' },
  made: { label: 'Made minds', icon: Bot, tone: 'info' },
}

export const DISTRIBUTION: Record<Schema['DistributionRule'], Named> = {
  by_holding: { label: 'By holding', icon: Landmark, tone: 'gold' },
  by_office: { label: 'By office', icon: Crown, tone: 'info' },
  by_need: { label: 'By need', icon: HandCoins, tone: 'success' },
  by_work: { label: 'By work', icon: Hammer, tone: 'warning' },
  by_share: { label: 'By share', icon: Briefcase, tone: 'muted' },
  equal: { label: 'Equally', icon: Equal, tone: 'success' },
  by_prestige: { label: 'By prestige', icon: Award, tone: 'gold' },
}

export const CHANGES: Record<Schema['TransitionKind'], Named> = {
  collectivisation: {
    label: 'Collectivisation',
    icon: Handshake,
    tone: 'warning',
  },
  nationalisation: { label: 'Nationalisation', icon: Landmark, tone: 'info' },
  privatisation: { label: 'Privatisation', icon: Briefcase, tone: 'gold' },
  land_reform: { label: 'Land reform', icon: Wheat, tone: 'success' },
  enclosure: { label: 'Enclosure', icon: Lock, tone: 'warning' },
  emancipation: { label: 'Emancipation', icon: Flag, tone: 'success' },
  decollectivisation: { label: 'Decollectivisation', icon: Home, tone: 'info' },
  restoration_of_holdings: {
    label: 'Restoration of holdings',
    icon: Castle,
    tone: 'muted',
  },
}

export const STAGES: Record<Schema['TransitionStage'], Named> = {
  proclaimed: { label: 'Proclaimed', icon: Megaphone, tone: 'info' },
  transferring: { label: 'Moving holdings', icon: Hourglass, tone: 'warning' },
  done: { label: 'Done', icon: CheckCheck, tone: 'success' },
  failed: { label: 'Broken', icon: XCircle, tone: 'danger' },
}

export const COMPENSATION: Record<Schema['Compensation'], Named> = {
  none: { label: 'Unpaid', icon: CircleSlash, tone: 'danger' },
  partial: { label: 'Half paid', icon: HandCoins, tone: 'warning' },
  full: { label: 'Fully paid', icon: Coins, tone: 'success' },
}

export const SAVING_FORMS: Record<Schema['SavingForm'], Named> = {
  hoard: { label: 'Buried hoard', icon: Shovel, tone: 'warning' },
  deposit: { label: 'Bank deposit', icon: Vault, tone: 'info' },
  investment: { label: 'Investment', icon: Cog, tone: 'success' },
}

export const HOARD_STATES: Record<Schema['HoardState'], Named> = {
  hidden: { label: 'Hidden', icon: Shovel, tone: 'muted' },
  lost: { label: 'Lost', icon: CircleSlash, tone: 'warning' },
  found: { label: 'Found', icon: Award, tone: 'gold' },
  spent: { label: 'Spent', icon: Coins, tone: 'info' },
}

export const SIGHTS: Record<Schema['TouristSight'], Named> = {
  wonder: { label: 'Wonder', icon: Award, tone: 'gold' },
  baths: { label: 'Baths', icon: Bath, tone: 'info' },
  sacred: { label: 'Holy place', icon: Church, tone: 'verdigris' },
  battlefield: { label: 'Battlefield', icon: Swords, tone: 'danger' },
  city: { label: 'Great city', icon: Building2, tone: 'success' },
}
