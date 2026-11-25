import {
  BadgeCheck,
  Ban,
  BookOpen,
  Briefcase,
  Building2,
  Church,
  Coins,
  Crown,
  Drama,
  Eye,
  Factory,
  Fence,
  Gem,
  Globe2,
  GraduationCap,
  Hammer,
  HandCoins,
  Handshake,
  HeartPulse,
  Home,
  Landmark,
  Languages,
  Medal,
  Moon,
  Package,
  PartyPopper,
  Pickaxe,
  Scale,
  ScrollText,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Shovel,
  Swords,
  Utensils,
  Vote,
  Wallet,
  Wheat,
  Wine,
  Ticket,
} from 'lucide-react'
import {
  bondRoleValues,
  coastKindValues,
  commodityKindValues,
  type components,
  districtKindValues,
  entityTypeValues,
  epochStepKindValues,
  holdingKindValues,
  needKindValues,
  nodeKindValues,
  resourceMechanicValues,
  socialClassValues,
  stanceValues,
  techniqueValues,
  temperatureBandValues,
  terrainKindValues,
  warEndingValues,
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
  oversee_works: { label: 'Oversee the works', icon: Hammer, tone: 'info' },
  promote_trade: { label: 'Promote trade', icon: Scale, tone: 'gold' },
  advance_learning: {
    label: 'Advance learning',
    icon: BookOpen,
    tone: 'verdigris',
  },
  public_health: { label: 'Public health', icon: HeartPulse, tone: 'success' },
  secure_borders: {
    label: 'Keep the borders',
    icon: ShieldCheck,
    tone: 'info',
  },
}

export const TAX_KINDS: Record<components['schemas']['TaxKind'], Named> = {
  land: { label: 'Land tax', icon: Wheat, tone: 'gold' },
  poll: { label: 'Poll tax', icon: Home, tone: 'warning' },
  trade: { label: 'Trade tax', icon: Building2, tone: 'info' },
  consumption: { label: 'Tax on luxuries', icon: Gem, tone: 'verdigris' },
  tithe: { label: 'Tithe', icon: Church, tone: 'muted' },
  income: { label: 'Income tax', icon: Wallet, tone: 'info' },
  property: { label: 'Property tax', icon: Landmark, tone: 'gold' },
  inheritance: { label: 'Inheritance tax', icon: ScrollText, tone: 'muted' },
  wealth: { label: 'Wealth tax', icon: Crown, tone: 'gold' },
  company: { label: 'Company tax', icon: Coins, tone: 'info' },
  labour_levy: { label: 'Labour levy', icon: Hammer, tone: 'warning' },
  in_kind: { label: 'Tax paid in goods', icon: Package, tone: 'muted' },
  licence: { label: 'Licence fees', icon: BadgeCheck, tone: 'info' },
  seigniorage: { label: 'Seigniorage on coin', icon: Coins, tone: 'gold' },
  pollution: { label: 'Pollution tax', icon: Factory, tone: 'warning' },
  excise: { label: 'Excise on goods', icon: Wine, tone: 'verdigris' },
  hearth: { label: 'Hearth tax', icon: Home, tone: 'gold' },
  toll: { label: 'Toll', icon: Ticket, tone: 'gold' },
}

export const MANDATE_KINDS: Record<string, Named> = {
  produce: { label: 'Production order', icon: Hammer, tone: 'info' },
  export_ban: { label: 'Export ban', icon: Ban, tone: 'warning' },
  build: { label: 'Building order', icon: Building2, tone: 'gold' },
  famine_relief: { label: 'Famine relief', icon: Wheat, tone: 'success' },
  curfew: { label: 'Curfew', icon: Moon, tone: 'danger' },
  slum_clearance: { label: 'Slum clearance', icon: Shovel, tone: 'warning' },
  prepare: { label: 'Works against disaster', icon: ShieldCheck, tone: 'info' },
  enclosure: { label: 'Enclosure of the commons', icon: Fence, tone: 'danger' },
  ration: { label: 'Rationing by rule', icon: Scale, tone: 'warning' },
  corvee: { label: 'Called-out labour', icon: Pickaxe, tone: 'danger' },
  quarantine: { label: 'Quarantine', icon: ShieldAlert, tone: 'warning' },
  conscription: { label: 'Conscription', icon: Swords, tone: 'danger' },
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
  jester: { label: 'Jester', icon: Drama, tone: 'warning' },
  seer: { label: 'Seer', icon: Eye, tone: 'verdigris' },
  taster: { label: 'Food taster', icon: Utensils, tone: 'warning' },
  interpreter: { label: 'Interpreter', icon: Languages, tone: 'info' },
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

const WORD_TABLES = new Map<ReadonlyArray<string>, Record<string, string>>()

export function wordOf<T extends string>(
  values: ReadonlyArray<T>,
  value: NoInfer<T>
): string {
  const known = WORD_TABLES.get(values) ?? valueTable(values)
  WORD_TABLES.set(values, known)
  return known[value]
}

export const COMMODITIES = valueTable(commodityKindValues)
export const DISTRICTS = valueTable(districtKindValues)
export const CLASSES = valueTable(socialClassValues)
export const TECHNIQUE_WORDS = valueTable(techniqueValues)
export const WAR_ENDING_WORDS = valueTable(warEndingValues)
export const RESOURCE_MECHANIC_WORDS = valueTable(resourceMechanicValues)
export const NEED_WORDS = valueTable(needKindValues)
export const BOND_ROLE_WORDS = valueTable(bondRoleValues)
export const ENTITY_TYPE_WORDS = valueTable(entityTypeValues)
export const COAST_WORDS = valueTable(coastKindValues)
export const TERRAIN_WORDS = valueTable(terrainKindValues)
export const TEMPERATURE_WORDS = valueTable(temperatureBandValues)
export const EPOCH_STEP_WORDS = valueTable(epochStepKindValues)
export const STANCE_WORDS = valueTable(stanceValues)
export const HOLDING_WORDS = valueTable(holdingKindValues)
export const NODE_KIND_WORDS = valueTable(nodeKindValues)

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
