import {
  Map,
  Megaphone,
  Baby,
  BadgeCheck,
  Ban,
  Bird,
  BrickWall,
  Building2,
  Castle,
  Church,
  CircleCheck,
  Coins,
  Crown,
  Droplet,
  Eye,
  Feather,
  Flag,
  Footprints,
  Gavel,
  Gem,
  Gift,
  Globe,
  Hammer,
  HandCoins,
  HandHeart,
  Handshake,
  Heart,
  HeartCrack,
  HeartHandshake,
  Hexagon,
  Hourglass,
  House,
  Landmark,
  Lock,
  Map as MapIcon,
  Medal,
  Moon,
  PartyPopper,
  PenLine,
  Scale,
  ScrollText,
  Shield,
  ShieldCheck,
  ShieldOff,
  Ship,
  Signpost,
  Sparkles,
  Stethoscope,
  Sun,
  Swords,
  Trophy,
  TrendingUp,
  Users,
  Vote,
  VolumeX,
  WandSparkles,
  GraduationCap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type Named, named, plain } from '../environment/labels'

export { named, plain }
export type { Named }

export const GOVERNMENTS: Record<string, Named> = {
  chiefdom: { label: 'Chiefdom', icon: Flag, tone: 'warning' },
  monarchy: { label: 'Monarchy', icon: Crown, tone: 'gold' },
  theocracy: { label: 'Theocracy', icon: Church, tone: 'verdigris' },
  oligarchy: { label: 'Oligarchy', icon: Gem, tone: 'info' },
  republic: { label: 'Republic', icon: Landmark, tone: 'info' },
  tribal_confederation: {
    label: 'Tribal confederation',
    icon: Users,
    tone: 'success',
  },
  empire: { label: 'Empire', icon: Castle, tone: 'gold' },
  hive_council: { label: 'Hive council', icon: Hexagon, tone: 'verdigris' },
  god_kingdom: { label: 'God-kingdom', icon: Sun, tone: 'gold' },
  occupation: { label: 'Occupation', icon: Swords, tone: 'danger' },
}

export const RULES: Record<string, Named & { hint: string }> = {
  autocratic: {
    label: 'Autocratic',
    icon: Gavel,
    tone: 'gold',
    hint: 'The ruler alone decides',
  },
  council: {
    label: 'By council',
    icon: Users,
    tone: 'info',
    hint: 'A council of the great decides',
  },
  assembly: {
    label: 'By assembly',
    icon: Vote,
    tone: 'success',
    hint: 'The free people vote',
  },
  divine: {
    label: 'By divine will',
    icon: Sparkles,
    tone: 'verdigris',
    hint: 'Omens and priests decide',
  },
}

export const STANDINGS: Record<string, Named> = {
  hegemon: { label: 'Hegemon', icon: Trophy, tone: 'gold' },
  great_power: { label: 'Great power', icon: Medal, tone: 'info' },
  minor_power: { label: 'Minor power', icon: Shield, tone: 'muted' },
  client: { label: 'Client state', icon: Lock, tone: 'warning' },
}

export const OFFICES: Record<string, Named> = {
  ruler: { label: 'Ruler', icon: Crown, tone: 'gold' },
  heir_designate: { label: 'Heir designate', icon: Baby, tone: 'success' },
  regent: { label: 'Regent', icon: Hourglass, tone: 'verdigris' },
  chancellor: { label: 'Chancellor', icon: ScrollText, tone: 'info' },
  marshal: { label: 'Marshal', icon: Swords, tone: 'danger' },
  treasurer: { label: 'Treasurer', icon: Coins, tone: 'gold' },
  high_judge: { label: 'High judge', icon: Scale, tone: 'info' },
  spymaster: { label: 'Spymaster', icon: Eye, tone: 'verdigris' },
  governor: { label: 'Governor', icon: MapIcon, tone: 'success' },
  ambassador: { label: 'Ambassador', icon: Handshake, tone: 'info' },
  herald: { label: 'Herald', icon: Megaphone, tone: 'warning' },
  chaplain: { label: 'Court chaplain', icon: Church, tone: 'verdigris' },
  court_scholar: { label: 'Court scholar', icon: GraduationCap, tone: 'info' },
}

export const LAW_AREAS: Record<string, Named> = {
  succession: { label: 'Succession', icon: Crown, tone: 'gold' },
  property: { label: 'Property', icon: House, tone: 'success' },
  fiscal: { label: 'Taxes and coin', icon: Coins, tone: 'gold' },
  penal: { label: 'Crime and punishment', icon: Gavel, tone: 'danger' },
  military: { label: 'War and levies', icon: Swords, tone: 'danger' },
  social: { label: 'Society', icon: Users, tone: 'info' },
  public_health: {
    label: 'Public health',
    icon: Stethoscope,
    tone: 'success',
  },
  magic: { label: 'Magic', icon: WandSparkles, tone: 'verdigris' },
  constitutional: {
    label: 'The fundamental law',
    icon: ScrollText,
    tone: 'gold',
  },
}

export const LAW_KINDS: Record<string, string> = {
  succession_rule: 'Law of the throne',
  inheritance_split: 'Inheritance',
  land_tenure: 'Land tenure',
  slavery: 'Slavery',
  serfdom: 'Serfdom',
  tax_rate: 'Tax rate',
  tithe: 'Tithe',
  tolls: 'Tolls',
  debt_law: 'Debt',
  penal_code: 'Penal code',
  levy_law: 'Levy',
  conscription: 'Conscription',
  standing_army: 'Standing army',
  veteran_pension: 'Veterans’ pension',
  ransom_custom: 'Ransom custom',
  marriage_law: 'Marriage',
  sumptuary: 'Sumptuary law',
  guild_charter: 'Guild charter',
  foreigner_rights: 'Rights of foreigners',
  religious_tolerance: 'Religious tolerance',
  worship_ban: 'Worship ban',
  censorship: 'Censorship',
  blood_feud: 'Blood feud',
  quarantine: 'Quarantine',
  burial_law: 'Burial',
  sanitation: 'Sanitation',
  magic_ban: 'Ban on magic',
  licensed_magic: 'Licensed magic',
  rite_restrictions: 'Restricted rites',
  franchise: 'Franchise',
  constitution: 'Constitution',
  custom: 'Custom',
}

export const LAW_PARAMS: Record<string, string> = {
  rule: 'Rule',
  gender: 'Gender',
  wholeness_required: 'Must be whole of body',
  min_age: 'Minimum age',
  split: 'Split',
  tenure: 'Tenure',
  status: 'Status',
  allowed: 'Allowed',
  labour_days: 'Labour days',
  rate: 'Rate (%)',
  enforced: 'Enforced',
  remedy: 'Remedy',
  jubilee_epochs: 'Jubilee every (epochs)',
  share: 'Share (%)',
  duration: 'Duration (seasons)',
  amount: 'Amount',
  price: 'Price',
  custom: 'Custom',
  endogamy: 'Marry within',
  divorce: 'Divorce',
  noble_luxury: 'Noble luxury',
  merchant_luxury: 'Merchant luxury',
  guild_id: 'Guild',
  monopoly: 'Monopoly',
  level: 'Level',
  son_id: 'Banned god',
  wergild_allowed: 'Wergild allowed',
  automatic: 'Automatic',
  epochs: 'Epochs',
  rite: 'Rite',
  works: 'Works',
  severity: 'Severity',
  fee: 'Fee',
  trial: 'Trial by',
  torture: 'Questioning under torture',
}

export const LEGITIMACY_BASES: Record<string, Named> = {
  custom: { label: 'By custom', icon: ScrollText, tone: 'muted' },
  decree: { label: 'By decree', icon: Gavel, tone: 'gold' },
  divine: { label: 'By divine will', icon: Sparkles, tone: 'verdigris' },
  council: { label: 'By council', icon: Users, tone: 'info' },
}

export const CLAIM_BASES: Record<string, Named> = {
  inheritance: { label: 'By blood', icon: Crown, tone: 'gold' },
  marriage: { label: 'By marriage', icon: Heart, tone: 'danger' },
  conquest: { label: 'By conquest', icon: Swords, tone: 'danger' },
  divine: { label: 'By divine right', icon: Sparkles, tone: 'verdigris' },
  fabricated: { label: 'Forged', icon: Feather, tone: 'warning' },
  de_jure: { label: 'By right of the land', icon: Map, tone: 'info' },
}

export const TREATY_KINDS: Record<string, Named & { plural: string }> = {
  peace: { label: 'Peace', plural: 'Peaces', icon: Bird, tone: 'success' },
  truce: { label: 'Truce', plural: 'Truces', icon: Hourglass, tone: 'warning' },
  alliance_defensive: {
    label: 'Defensive alliance',
    plural: 'Defensive alliances',
    icon: ShieldCheck,
    tone: 'info',
  },
  alliance_offensive: {
    label: 'Offensive alliance',
    plural: 'Offensive alliances',
    icon: Swords,
    tone: 'danger',
  },
  non_aggression: {
    label: 'Non-aggression pact',
    plural: 'Non-aggression pacts',
    icon: Ban,
    tone: 'muted',
  },
  vassalage: {
    label: 'Vassalage',
    plural: 'Vassalages',
    icon: Crown,
    tone: 'gold',
  },
  tribute: { label: 'Tribute', plural: 'Tributes', icon: Coins, tone: 'gold' },
  marriage_pact: {
    label: 'Marriage pact',
    plural: 'Marriage pacts',
    icon: HeartHandshake,
    tone: 'verdigris',
  },
  trade_pact: {
    label: 'Trade pact',
    plural: 'Trade pacts',
    icon: Ship,
    tone: 'success',
  },
  condotta: {
    label: 'Condotta',
    plural: 'Condottas',
    icon: HandCoins,
    tone: 'warning',
  },
  guarantee: {
    label: 'Guarantee',
    plural: 'Guarantees',
    icon: BadgeCheck,
    tone: 'info',
  },
  interworld: {
    label: 'Interworld pact',
    plural: 'Interworld pacts',
    icon: Globe,
    tone: 'verdigris',
  },
  coalition: {
    label: 'Coalition',
    plural: 'Coalitions',
    icon: Users,
    tone: 'danger',
  },
}

export const TREATY_STATUSES: Record<
  components['schemas']['TreatyStatus'],
  Named
> = {
  in_force: { label: 'In force', icon: CircleCheck, tone: 'success' },
  fulfilled: { label: 'Fulfilled', icon: BadgeCheck, tone: 'info' },
  expired: { label: 'Expired', icon: Hourglass, tone: 'muted' },
  broken: { label: 'Broken', icon: HeartCrack, tone: 'danger' },
  proposed: { label: 'Proposed', icon: PenLine, tone: 'gold' },
  rejected: { label: 'Rejected', icon: Ban, tone: 'muted' },
}

export const PARTY_ROLES: Record<string, Named> = {
  signatory: { label: 'Signatory', icon: PenLine, tone: 'gold' },
  overlord: { label: 'Overlord', icon: Crown, tone: 'gold' },
  vassal: { label: 'Vassal', icon: Shield, tone: 'muted' },
  guarantor: { label: 'Guarantor', icon: ShieldCheck, tone: 'info' },
}

export const CLAUSES: Record<string, Named> = {
  call_to_arms: { label: 'Call to arms', icon: Swords, tone: 'danger' },
  tribute: { label: 'Tribute', icon: Coins, tone: 'gold' },
  cession: { label: 'Cession of land', icon: MapIcon, tone: 'warning' },
  hostage: { label: 'Hostages', icon: Lock, tone: 'warning' },
  marriage: { label: 'Marriage', icon: Heart, tone: 'verdigris' },
  trade_rights: { label: 'Trade rights', icon: Ship, tone: 'success' },
  tolls_waived: { label: 'Tolls waived', icon: Signpost, tone: 'success' },
  religious_freedom: {
    label: 'Freedom of worship',
    icon: Church,
    tone: 'verdigris',
  },
  demilitarised: { label: 'Demilitarised land', icon: ShieldOff },
  champion: { label: 'Champions', icon: Medal, tone: 'gold' },
  extradition: { label: 'Extradition', icon: Gavel, tone: 'info' },
  wergild: { label: 'Wergild', icon: HandCoins, tone: 'gold' },
  non_aggression: { label: 'Non-aggression', icon: Ban, tone: 'muted' },
  route_control: {
    label: 'Road and tolls ceded',
    icon: Signpost,
    tone: 'gold',
  },
  resource_demand: {
    label: 'Tribute to a living resource',
    icon: Gem,
    tone: 'verdigris',
  },
  research_agreement: {
    label: 'Shared research',
    icon: GraduationCap,
    tone: 'info',
  },
}

export const OATHS: Record<string, Named> = {
  fealty: { label: 'Fealty', icon: Crown, tone: 'gold' },
  vengeance: { label: 'Vengeance', icon: Swords, tone: 'danger' },
  celibacy: { label: 'Celibacy', icon: Moon, tone: 'verdigris' },
  pilgrimage: { label: 'Pilgrimage', icon: Footprints, tone: 'info' },
  protection: { label: 'Protection', icon: Shield, tone: 'success' },
  silence: { label: 'Silence', icon: VolumeX, tone: 'muted' },
  blood_brotherhood: {
    label: 'Blood brotherhood',
    icon: Droplet,
    tone: 'danger',
  },
}

export const OATH_STATUSES: Record<string, Named> = {
  sworn: { label: 'Sworn', icon: PenLine, tone: 'info' },
  kept: { label: 'Kept', icon: CircleCheck, tone: 'success' },
  fulfilled: { label: 'Fulfilled', icon: BadgeCheck, tone: 'success' },
  broken: { label: 'Broken', icon: HeartCrack, tone: 'danger' },
}

export const TREASURY_ENTRIES: Record<string, Named> = {
  tax: { label: 'Taxes', icon: Coins, tone: 'gold' },
  tolls: { label: 'Tolls', icon: Signpost, tone: 'gold' },
  investment: { label: 'Investment', icon: TrendingUp, tone: 'success' },
  garrison: { label: 'Garrison and court upkeep', icon: Shield },
  walls: { label: 'Walls', icon: BrickWall },
  building: { label: 'Building works', icon: Hammer },
  festival: { label: 'Festival', icon: PartyPopper, tone: 'verdigris' },
  alms: { label: 'Alms', icon: HandHeart, tone: 'success' },
  fire: { label: 'Fire', icon: Building2, tone: 'danger' },
  plunder: { label: 'Plunder', icon: Swords, tone: 'danger' },
  grant: { label: 'Grant', icon: Gift, tone: 'gold' },
  loan: { label: 'Loan', icon: Coins, tone: 'info' },
  upkeep: { label: 'Upkeep', icon: Hammer, tone: 'muted' },
}

export const MEMBER_TYPES: Record<string, Named> = {
  people: { label: 'People', icon: Users, tone: 'info' },
  settlement: { label: 'Settlement', icon: Castle, tone: 'gold' },
  tribe: { label: 'Tribe', icon: Flag, tone: 'success' },
  polity: { label: 'Realm', icon: Crown, tone: 'gold' },
}

export const TINCTURES: Record<string, Named> = {
  gules: { label: 'Gules', icon: Shield, tone: 'danger' },
  or: { label: 'Or', icon: Shield, tone: 'gold' },
  azure: { label: 'Azure', icon: Shield, tone: 'info' },
  vert: { label: 'Vert', icon: Shield, tone: 'success' },
  sable: { label: 'Sable', icon: Shield, tone: 'muted' },
  argent: { label: 'Argent', icon: Shield, tone: 'muted' },
  purpure: { label: 'Purpure', icon: Shield, tone: 'verdigris' },
}

export const REALM_FIELDS: Record<string, string> = {
  government: 'Government',
  decision_rule: 'Who decides',
  legitimacy: 'Legitimacy',
  stability: 'Stability',
  treasury: 'Treasury',
  debt: 'Debt',
  war_weariness: 'War weariness',
  standing: 'Standing',
}

export const SEXES: Record<string, string> = {
  male: 'Man',
  female: 'Woman',
}

export type Band = { label: string; tone: KpiTone }

const QUARTERS = [25, 50, 75]

function quarter(value: number): number {
  return QUARTERS.filter((edge) => value >= edge).length
}

export function goodBand(
  value: number,
  words: [string, string, string, string]
): Band {
  const index = quarter(value)
  const tones: KpiTone[] = ['danger', 'warning', 'gold', 'success']
  return { label: words[index], tone: tones[index] }
}

export function badBand(
  value: number,
  words: [string, string, string, string]
): Band {
  const index = quarter(value)
  const tones: KpiTone[] = ['success', 'gold', 'warning', 'danger']
  return { label: words[index], tone: tones[index] }
}

export function badgeVariant(
  tone: KpiTone | undefined
): 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'info' {
  if (tone === 'gold') return 'default'
  if (tone === 'success') return 'success'
  if (tone === 'warning') return 'warning'
  if (tone === 'danger') return 'destructive'
  if (tone === 'info' || tone === 'verdigris') return 'info'
  return 'secondary'
}

export function sentence(value: string): string {
  return plain({}, value)
}

export function labels(table: Record<string, Named>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}
