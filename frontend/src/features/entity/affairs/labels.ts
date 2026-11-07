import {
  Ban,
  Globe2,
  GraduationCap,
  HeartPulse,
  PartyPopper,
  ScrollText,
  Briefcase,
  Building2,
  Church,
  Coins,
  Crown,
  Eye,
  Gem,
  Hammer,
  HandCoins,
  Handshake,
  Home,
  Landmark,
  Medal,
  Moon,
  Scale,
  Search,
  Shield,
  Swords,
  Wheat,
  Vote,
} from 'lucide-react'
import {
  commodityKindValues,
  districtKindValues,
  socialClassValues,
} from '@/api/generated/schema'
import { type Named } from '../environment/labels'
import { sentence } from '../realm/labels'

export const AFFAIRS_ICON = Briefcase
export const ELECTION_ICON = Vote
export const CORRUPTION_ICON = HandCoins
export const TAX_ICON = Coins
export const MANDATE_ICON = Landmark
export const DEMAND_ICON = Crown
export const APPROVAL_ICON = Scale

export const TASKS: Record<string, Named> = {
  improve_relations: {
    label: 'Improve relations',
    icon: Handshake,
    tone: 'info',
  },
  train_troops: { label: 'Train troops', icon: Swords, tone: 'danger' },
  collect_taxes: { label: 'Collect taxes', icon: Coins, tone: 'gold' },
  disrupt_schemes: { label: 'Disrupt schemes', icon: Eye, tone: 'verdigris' },
  convert_province: {
    label: 'Carry the faith',
    icon: Church,
    tone: 'verdigris',
  },
  purge_corruption: {
    label: 'Purge corruption',
    icon: Search,
    tone: 'success',
  },
}

export const TAX_KINDS: Record<string, Named> = {
  land: { label: 'Land tax', icon: Wheat, tone: 'gold' },
  poll: { label: 'Poll tax', icon: Home, tone: 'warning' },
  trade: { label: 'Trade tax', icon: Building2, tone: 'info' },
  consumption: { label: 'Tax on luxuries', icon: Gem, tone: 'verdigris' },
  tithe: { label: 'Tithe', icon: Church, tone: 'muted' },
}

export const MANDATE_KINDS: Record<string, Named> = {
  produce: { label: 'Production order', icon: Hammer, tone: 'info' },
  export_ban: { label: 'Export ban', icon: Ban, tone: 'warning' },
  build: { label: 'Building order', icon: Building2, tone: 'gold' },
  famine_relief: { label: 'Famine relief', icon: Wheat, tone: 'success' },
  curfew: { label: 'Curfew', icon: Moon, tone: 'danger' },
}

export const MANDATE_STATES: Record<string, Named> = {
  active: { label: 'In force', icon: Landmark, tone: 'info' },
  met: { label: 'Met', icon: Medal, tone: 'success' },
  failed: { label: 'Failed', icon: Ban, tone: 'danger' },
}

export const WANTS: Record<string, Named> = {
  dwelling: { label: 'A fine dwelling', icon: Home, tone: 'gold' },
  fine_goods: { label: 'Fine goods', icon: Gem, tone: 'verdigris' },
  office: { label: 'An office', icon: Shield, tone: 'info' },
  honour: { label: 'Honour', icon: Medal, tone: 'gold' },
}

export const ASSEMBLY_ICON = Globe2
export const COURT_ICON = Crown

export const RESOLUTION_KINDS: Record<string, Named> = {
  route_security: { label: 'Guard the routes', icon: Shield, tone: 'info' },
  embargo: { label: 'Embargo a realm', icon: Ban, tone: 'warning' },
  void_ban: { label: 'Ban rites of the void', icon: Moon, tone: 'verdigris' },
  sanction: { label: 'Sanction a god’s world', icon: Scale, tone: 'danger' },
}

export const RESOLUTION_STATES: Record<string, Named> = {
  proposed: { label: 'Before the vote', icon: Vote, tone: 'info' },
  passed: { label: 'Binding', icon: Medal, tone: 'success' },
  rejected: { label: 'Voted down', icon: Ban, tone: 'muted' },
  lapsed: { label: 'Lapsed', icon: Moon, tone: 'muted' },
}

export const POSITIONS: Record<string, Named> = {
  steward: { label: 'Steward', icon: Coins, tone: 'gold' },
  champion: { label: 'Champion', icon: Swords, tone: 'danger' },
  physician: { label: 'Physician', icon: HeartPulse, tone: 'success' },
  tutor: { label: 'Tutor', icon: GraduationCap, tone: 'info' },
  chronicler: { label: 'Chronicler', icon: ScrollText, tone: 'verdigris' },
  master_of_revels: {
    label: 'Master of revels',
    icon: PartyPopper,
    tone: 'gold',
  },
}

export function labelTable(
  specs: Record<string, Named>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(specs).map(([key, spec]) => [key, spec.label])
  )
}

export function valueTable(
  values: ReadonlyArray<string>
): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, sentence(value)]))
}

export const COMMODITIES = valueTable(commodityKindValues)
export const DISTRICTS = valueTable(districtKindValues)
export const CLASSES = valueTable(socialClassValues)

export function spec(
  table: Record<string, Named>,
  key: string | null | undefined
): Named {
  return (
    (key ? table[key] : undefined) ?? {
      label: key ? sentence(key) : 'None',
      icon: Briefcase,
      tone: 'muted',
    }
  )
}
