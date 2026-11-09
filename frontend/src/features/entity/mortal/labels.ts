import {
  Baby,
  Backpack,
  BookOpen,
  Brain,
  Brush,
  Coins,
  Compass,
  Crown,
  Eye,
  Feather,
  Flame,
  Footprints,
  Gavel,
  Gem,
  Ghost,
  GraduationCap,
  HandCoins,
  HandHeart,
  Heart,
  HeartCrack,
  HeartHandshake,
  HeartPulse,
  Hourglass,
  Link2,
  type LucideIcon,
  Mountain,
  Scale,
  Scroll,
  Shield,
  ShieldHalf,
  Skull,
  Sparkles,
  Sprout,
  Star,
  Store,
  Swords,
  Sword,
  TreeDeciduous,
  User,
  Users,
  Wand,
  Wind,
  Zap,
  Shirt,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'

export type { Named }

export const MORTAL_ICON: LucideIcon = User
export const KIN_ICON: LucideIcon = TreeDeciduous
export const GEAR_ICON: LucideIcon = Backpack

export const ABILITIES: Record<string, Named & { hint: string }> = {
  endurance: {
    label: 'Endurance',
    icon: HeartPulse,
    tone: 'success',
    hint: 'Health held, wounds mended, marches endured',
  },
  willpower: {
    label: 'Willpower',
    icon: Mountain,
    tone: 'gold',
    hint: 'Resists fear, torture, temptation and the strain of life',
  },
  perception: {
    label: 'Perception',
    icon: Eye,
    tone: 'info',
    hint: 'Sees ambushes, plots and what others miss',
  },
  wisdom: {
    label: 'Wisdom',
    icon: Scroll,
    tone: 'verdigris',
    hint: 'Judgement, counsel and the gift of visions',
  },
  creativity: {
    label: 'Creativity',
    icon: Brush,
    tone: 'warning',
    hint: 'Works, rites and new ideas; a patron of the arts',
  },
  beauty: {
    label: 'Beauty',
    icon: Sparkles,
    tone: 'gold',
    hint: 'The presence others feel, as their culture reads it',
  },
}

export const STAGES: Record<string, Named> = {
  infant: { label: 'Infant', icon: Baby, tone: 'info' },
  child: { label: 'Child', icon: Sprout, tone: 'success' },
  youth: { label: 'Youth', icon: Feather, tone: 'verdigris' },
  adult: { label: 'Adult', icon: User, tone: 'gold' },
  elder: { label: 'Elder', icon: Hourglass, tone: 'warning' },
  ancient: { label: 'Ancient', icon: Ghost, tone: 'muted' },
}

export const SEXES: Record<string, Named> = {
  female: { label: 'Female', icon: User, tone: 'verdigris' },
  male: { label: 'Male', icon: User, tone: 'info' },
  other: { label: 'Other', icon: Sparkles, tone: 'gold' },
}

export const CAREERS: Record<string, Named> = {
  stay: { label: 'Stays the course', icon: Footprints, tone: 'muted' },
  army: { label: 'Took up arms', icon: Swords, tone: 'danger' },
  office: { label: 'Seeks office', icon: Crown, tone: 'gold' },
  apprentice: { label: 'Apprenticed', icon: GraduationCap, tone: 'info' },
  vows: { label: 'Took vows', icon: Star, tone: 'verdigris' },
  trade: { label: 'Turned to trade', icon: Store, tone: 'success' },
  wander: { label: 'Wanders', icon: Compass, tone: 'info' },
  bandit: { label: 'Turned bandit', icon: Skull, tone: 'danger' },
}

export const BREAKS: Record<string, Named> = {
  rage: { label: 'Rage', icon: Flame, tone: 'danger' },
  flight: { label: 'Flight', icon: Wind, tone: 'warning' },
  despair: { label: 'Despair', icon: HeartCrack, tone: 'muted' },
  zeal: { label: 'Zeal', icon: Star, tone: 'gold' },
  vice: { label: 'Vice', icon: Gem, tone: 'warning' },
  revelation: { label: 'Revelation', icon: Zap, tone: 'verdigris' },
}

export const DEATHS: Record<string, Named> = {
  old_age: { label: 'Old age', icon: Hourglass, tone: 'muted' },
  wounds: { label: 'Wounds', icon: HeartCrack, tone: 'danger' },
  battle: { label: 'Battle', icon: Swords, tone: 'danger' },
  duel: { label: 'Duel', icon: Sword, tone: 'danger' },
  execution: { label: 'Execution', icon: Gavel, tone: 'danger' },
  murder: { label: 'Murder', icon: Skull, tone: 'danger' },
  monster: { label: 'A monster', icon: Skull, tone: 'danger' },
  disease: { label: 'Disease', icon: HeartPulse, tone: 'warning' },
  childbirth: { label: 'Childbirth', icon: Baby, tone: 'warning' },
  famine: { label: 'Famine', icon: Sprout, tone: 'warning' },
  accident: { label: 'Accident', icon: Zap, tone: 'warning' },
  disaster: { label: 'Disaster', icon: Mountain, tone: 'warning' },
  exposure: { label: 'Exposure', icon: Wind, tone: 'info' },
  curse: { label: 'A curse', icon: Ghost, tone: 'verdigris' },
  magic: { label: 'Magic', icon: Wand, tone: 'verdigris' },
  divine: { label: 'A god', icon: Star, tone: 'gold' },
  poison: { label: 'Poison', icon: Flame, tone: 'danger' },
  sacrifice: { label: 'Sacrifice', icon: Flame, tone: 'gold' },
  hardship: { label: 'Hardship', icon: Footprints, tone: 'muted' },
  despair: { label: 'Despair', icon: HeartCrack, tone: 'muted' },
  unknown: { label: 'Unknown', icon: Ghost, tone: 'muted' },
}

export const KIN_KINDS: Record<string, Named & { out: string; in: string }> = {
  parent_of: {
    label: 'Parent',
    icon: Users,
    tone: 'gold',
    out: 'Child',
    in: 'Parent',
  },
  spouse_of: {
    label: 'Spouse',
    icon: Heart,
    tone: 'danger',
    out: 'Spouse',
    in: 'Spouse',
  },
  betrothed_to: {
    label: 'Betrothed',
    icon: HeartHandshake,
    tone: 'warning',
    out: 'Promised to',
    in: 'Promised to',
  },
  concubine_of: {
    label: 'Concubine',
    icon: Gem,
    tone: 'muted',
    out: 'Concubine',
    in: 'Keeps as concubine',
  },
  fostered_by: {
    label: 'Fostered',
    icon: HandHeart,
    tone: 'verdigris',
    out: 'Fostered by',
    in: 'Ward',
  },
  sworn_kin: {
    label: 'Sworn kin',
    icon: Link2,
    tone: 'info',
    out: 'Sworn kin',
    in: 'Sworn kin',
  },
}

export const MARRIAGE_KINDS: Record<string, Named> = {
  monogamous: { label: 'Monogamous', icon: Heart, tone: 'danger' },
  plural: { label: 'Plural', icon: Users, tone: 'gold' },
  political: { label: 'Political', icon: Crown, tone: 'info' },
}

export const MARRIAGE_ENDS: Record<string, Named> = {
  death: { label: 'Death', icon: Skull, tone: 'muted' },
  divorce: { label: 'Divorce', icon: HeartCrack, tone: 'warning' },
  annulment: { label: 'Annulment', icon: Scroll, tone: 'info' },
  war: { label: 'War', icon: Swords, tone: 'danger' },
}

export const SLOTS: Record<string, Named> = {
  wielded_main: { label: 'Main hand', icon: Sword, tone: 'danger' },
  wielded_off: { label: 'Off hand', icon: ShieldHalf, tone: 'warning' },
  armour_body: { label: 'Body armour', icon: Shield, tone: 'info' },
  armour_head: { label: 'Helm', icon: Crown, tone: 'gold' },
  armour_under: { label: 'Padding under armour', icon: Shirt, tone: 'muted' },
  armour_cover: { label: 'Cloak over armour', icon: Shirt, tone: 'verdigris' },
  mount: { label: 'Mount', icon: Footprints, tone: 'verdigris' },
  focus: { label: 'Focus', icon: Wand, tone: 'verdigris' },
}

export const SLOT_TYPES: Record<string, readonly string[]> = {
  wielded_main: ['item'],
  wielded_off: ['item'],
  armour_body: ['item'],
  armour_head: ['item'],
  armour_under: ['item'],
  armour_cover: ['item'],
  mount: ['beast', 'species'],
  focus: ['item'],
}

export const CRIMES: Record<string, Named> = {
  theft: { label: 'Theft', icon: HandCoins, tone: 'warning' },
  blasphemy: { label: 'Blasphemy', icon: Flame, tone: 'danger' },
  treason: { label: 'Treason', icon: Crown, tone: 'danger' },
  murder: { label: 'Murder', icon: Skull, tone: 'danger' },
  desertion: { label: 'Desertion', icon: Wind, tone: 'warning' },
}

export const PUNISHMENTS: Record<
  components['schemas']['PunishmentKind'],
  Named
> = {
  fine: { label: 'A fine', icon: Coins, tone: 'muted' },
  flogging: { label: 'Flogging', icon: Zap, tone: 'warning' },
  exile: { label: 'Exile', icon: Compass, tone: 'warning' },
  branding: { label: 'Branding', icon: Flame, tone: 'danger' },
  hand: { label: 'Loss of a hand', icon: HeartCrack, tone: 'danger' },
  tongue: { label: 'Loss of the tongue', icon: HeartCrack, tone: 'danger' },
  eyes: { label: 'Blinding', icon: Eye, tone: 'danger' },
  death: { label: 'Death', icon: Skull, tone: 'danger' },
  public_shaming: { label: 'Public shaming', icon: Users, tone: 'warning' },
}

export const STANDING_FIELDS: Record<
  string,
  Named & { hint: string; harmful?: boolean }
> = {
  wealth: {
    label: 'Wealth',
    icon: Coins,
    tone: 'gold',
    hint: 'Their own purse; funds patronage and bribes',
  },
  renown: {
    label: 'Renown',
    icon: Star,
    tone: 'gold',
    hint: 'Fame among the living; fades unless renewed',
  },
  honour: {
    label: 'Honour',
    icon: Scale,
    tone: 'success',
    hint: 'Oaths kept and broken, as their culture reads them',
  },
  infamy: {
    label: 'Infamy',
    icon: Skull,
    tone: 'danger',
    hint: 'Atrocities and cruelties remembered',
    harmful: true,
  },
  education: {
    label: 'Education',
    icon: BookOpen,
    tone: 'info',
    hint: 'Schooling from parents, schools and temples',
  },
}

export const LOYALTY_FIELDS: Record<string, Named & { hint: string }> = {
  loyalty_liege: {
    label: 'To their liege',
    icon: Crown,
    tone: 'gold',
    hint: 'Shared values, regard and fear of their ruler',
  },
  loyalty_community: {
    label: 'To their people',
    icon: Users,
    tone: 'verdigris',
    hint: 'Shared values and belonging',
  },
  loyalty_god: {
    label: 'To their god',
    icon: Star,
    tone: 'info',
    hint: 'Shared values and a fulfilled faith',
  },
}

export const LIFE_FIELDS: Record<string, Named & { hint: string }> = {
  health: {
    label: 'Health',
    icon: HeartPulse,
    tone: 'success',
    hint: 'Chronic illness, age and open wounds wear it down',
  },
  fertility: {
    label: 'Fertility',
    icon: Sprout,
    tone: 'verdigris',
    hint: 'Within the fertile years of their people and sex',
  },
  stress: {
    label: 'Stress',
    icon: Brain,
    tone: 'warning',
    hint: 'Trauma, unmet needs, war and torn loyalties',
  },
}

export const HELD_LABELS: Record<string, string> = {
  life_stage: 'life stage',
  cause_of_death: 'cause of death',
  death_place_id: 'place of death',
  polity_id: 'realm',
  loyalty_liege: 'loyalty to their liege',
  loyalty_community: 'loyalty to their people',
  loyalty_god: 'loyalty to their god',
  kin: 'marriages',
}

export const PROFESSIONS: Record<string, Named> = {
  soldier: { label: 'Soldier', icon: Swords, tone: 'danger' },
  rider: { label: 'Rider', icon: Footprints, tone: 'info' },
  smith: { label: 'Smith', icon: Flame, tone: 'warning' },
  builder: { label: 'Builder', icon: Mountain, tone: 'muted' },
  weaver: { label: 'Weaver', icon: Feather, tone: 'verdigris' },
  healer: { label: 'Healer', icon: HeartPulse, tone: 'success' },
  scholar: { label: 'Scholar', icon: BookOpen, tone: 'info' },
  priest: { label: 'Priest', icon: Star, tone: 'gold' },
  sorcerer: { label: 'Sorcerer', icon: Wand, tone: 'verdigris' },
  merchant: { label: 'Merchant', icon: Store, tone: 'gold' },
  diplomat: { label: 'Diplomat', icon: HeartHandshake, tone: 'info' },
  hunter: { label: 'Hunter', icon: Compass, tone: 'success' },
  sailor: { label: 'Sailor', icon: Wind, tone: 'info' },
  commander: { label: 'Commander', icon: Crown, tone: 'gold' },
}
