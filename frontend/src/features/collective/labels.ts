import {
  Anchor,
  Baby,
  BookMarked,
  BookOpen,
  Bug,
  CalendarClock,
  CalendarDays,
  Castle,
  Church,
  Coins,
  Crown,
  Drama,
  Eye,
  EyeOff,
  Feather,
  Flag,
  Flame,
  Footprints,
  Gavel,
  Gem,
  Globe,
  Hammer,
  HandCoins,
  Handshake,
  Heart,
  HeartCrack,
  Home,
  KeyRound,
  Landmark,
  type LucideIcon,
  Megaphone,
  MessageCircle,
  Moon,
  Mountain,
  PartyPopper,
  Scale,
  ScrollText,
  Shield,
  ShieldAlert,
  Ship,
  Shirt,
  Skull,
  Sparkles,
  Star,
  Sun,
  Sword,
  Swords,
  Tent,
  Trophy,
  User,
  UserMinus,
  Users,
  Utensils,
  Wheat,
  Wind,
  Wrench,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const COLLECTIVE_ICON: LucideIcon = Users

export const ACTS: Record<Schema['CollectiveActKind'], Named> = {
  riot: { label: 'Riot', icon: Flame, tone: 'danger' },
  panic: { label: 'Panic', icon: Wind, tone: 'warning' },
  lynching: { label: 'Lynching', icon: Skull, tone: 'danger' },
  conversion: { label: 'Mass conversion', icon: Sparkles, tone: 'gold' },
  revolt: { label: 'Revolt', icon: Swords, tone: 'danger' },
  strike: { label: 'Strike', icon: Hammer, tone: 'warning' },
  procession: { label: 'Procession', icon: Megaphone, tone: 'info' },
  revival: { label: 'Revival', icon: Church, tone: 'gold' },
}

export const TRIGGERS: Record<Schema['CollectiveTrigger'], Named> = {
  price_spike: { label: 'Dear food', icon: Coins, tone: 'warning' },
  execution: { label: 'An execution', icon: Gavel, tone: 'danger' },
  sermon: { label: 'A preacher', icon: Megaphone, tone: 'gold' },
  omen: { label: 'An omen', icon: Eye, tone: 'verdigris' },
  rumour: { label: 'A rumour', icon: MessageCircle, tone: 'muted' },
  fire: { label: 'A fire', icon: Flame, tone: 'danger' },
  plague: { label: 'A plague', icon: Bug, tone: 'danger' },
  beast: { label: 'A beast at hand', icon: Footprints, tone: 'warning' },
  eclipse: { label: 'An eclipse', icon: Moon, tone: 'verdigris' },
  miracle: { label: 'A miracle', icon: Sparkles, tone: 'gold' },
  famine: { label: 'Hunger', icon: Wheat, tone: 'warning' },
  unpaid_wages: { label: 'Unpaid wages', icon: HandCoins, tone: 'warning' },
}

export const OUTCOMES: Record<Schema['CascadeOutcome'], Named> = {
  fizzled: { label: 'Fizzled', icon: Wind, tone: 'muted' },
  mob: { label: 'Became a mob', icon: Flame, tone: 'danger' },
  panic: { label: 'Became a panic', icon: ShieldAlert, tone: 'warning' },
  movement: { label: 'Became a movement', icon: Flag, tone: 'gold' },
}

export const MOB_TARGETS: Record<Schema['MobTarget'], Named> = {
  district: { label: 'A district', icon: Home, tone: 'warning' },
  granary: { label: 'The granary', icon: Wheat, tone: 'warning' },
  scapegoat: { label: 'A scapegoat', icon: UserMinus, tone: 'danger' },
  gate: { label: 'The gate', icon: Castle, tone: 'warning' },
  temple: { label: 'The temple', icon: Church, tone: 'info' },
  palace: { label: 'The palace', icon: Crown, tone: 'danger' },
  workshop: { label: 'The workshops', icon: Hammer, tone: 'warning' },
}

export const MOB_STATES: Record<Schema['MobStatus'], Named> = {
  gathering: { label: 'Gathering', icon: Users, tone: 'warning' },
  rampaging: { label: 'Rampaging', icon: Flame, tone: 'danger' },
  dispersed: { label: 'Dispersed', icon: Wind, tone: 'muted' },
}

export const MOB_ENDS: Record<Schema['MobEnd'], Named> = {
  fatigue: { label: 'Tired and went home', icon: Wind, tone: 'muted' },
  force: { label: 'Broken by force', icon: Shield, tone: 'danger' },
  concession: { label: 'Given its demands', icon: Handshake, tone: 'success' },
}

export const ACCOUNT_KINDS: Record<Schema['AccountKind'], Named> = {
  official_chronicle: {
    label: 'Official chronicle',
    icon: Landmark,
    tone: 'gold',
  },
  folk_memory: { label: 'Folk memory', icon: Users, tone: 'info' },
  foreign_account: { label: 'Foreign account', icon: Globe, tone: 'verdigris' },
  gospel: { label: 'Gospel', icon: Church, tone: 'gold' },
  epic: { label: 'Epic', icon: Trophy, tone: 'gold' },
  inscription: { label: 'Inscription', icon: Mountain, tone: 'muted' },
  founding_myth: { label: 'Founding myth', icon: Star, tone: 'gold' },
}

export const STANCES: Record<Schema['AccountStance'], Named> = {
  glorify: { label: 'Glorifies', icon: Trophy, tone: 'success' },
  vilify: { label: 'Vilifies', icon: HeartCrack, tone: 'danger' },
  omit: { label: 'Leaves out', icon: EyeOff, tone: 'muted' },
  neutral: { label: 'Tells plainly', icon: Scale, tone: 'info' },
}

export const MEDIA: Record<Schema['AccountMedium'], Named> = {
  artwork: { label: 'A work of art', icon: Feather, tone: 'verdigris' },
  book: { label: 'A book', icon: BookOpen, tone: 'info' },
  oral: { label: 'Told aloud', icon: MessageCircle, tone: 'muted' },
  inscription: { label: 'An inscription', icon: Mountain, tone: 'gold' },
}

export const STORYLET_STATES: Record<Schema['StoryletStatus'], Named> = {
  open: { label: 'Waiting for a choice', icon: CalendarClock, tone: 'warning' },
  resolved: { label: 'Chosen', icon: BookMarked, tone: 'success' },
  expired: { label: 'Lapsed', icon: Wind, tone: 'muted' },
}

export const STORYLETS: Record<Schema['StoryletId'], Named> = {
  lost_heir: { label: 'The lost heir', icon: Crown, tone: 'gold' },
  hoarded_store: { label: 'The hoarded store', icon: Wheat, tone: 'warning' },
  beast_demand: {
    label: "The beast's demand",
    icon: Footprints,
    tone: 'danger',
  },
  forbidden_text: {
    label: 'The forbidden text',
    icon: ScrollText,
    tone: 'verdigris',
  },
  defiled_site: { label: 'The defiled site', icon: Church, tone: 'danger' },
  wedding_challenge: {
    label: 'The wedding challenge',
    icon: Swords,
    tone: 'warning',
  },
  dying_ruler: { label: 'The dying ruler', icon: Skull, tone: 'muted' },
  insulted_envoy: { label: 'The insulted envoy', icon: Flag, tone: 'warning' },
}

export const ROLES_IN_STORY: Record<Schema['StoryletRole'], string> = {
  ruler: 'Ruler',
  claimant: 'Claimant',
  realm: 'Realm',
  town: 'Town',
  beast: 'Beast',
  scholar: 'Scholar',
  text: 'Text',
  cult: 'Cult',
  site: 'Site',
  challenger: 'Challenger',
  challenged: 'Challenged',
  elder_heir: 'Elder heir',
  younger_heir: 'Younger heir',
  envoy: 'Envoy',
  host_realm: 'Host realm',
}

export const SITUATIONS: Record<Schema['NormSituation'], Named> = {
  funeral: { label: 'At a funeral', icon: Skull, tone: 'muted' },
  feast: { label: 'At a feast', icon: Utensils, tone: 'gold' },
  wedding: { label: 'At a wedding', icon: Heart, tone: 'success' },
  court: { label: 'At court', icon: Crown, tone: 'gold' },
  temple: { label: 'In a temple', icon: Church, tone: 'info' },
  market: { label: 'At market', icon: Coins, tone: 'info' },
  battle: { label: 'In battle', icon: Swords, tone: 'danger' },
  duel: { label: 'In a duel', icon: Sword, tone: 'danger' },
  hospitality: { label: 'As a guest or host', icon: Home, tone: 'success' },
  mourning: { label: 'In mourning', icon: HeartCrack, tone: 'muted' },
  sacred_day: { label: 'On a sacred day', icon: Sun, tone: 'gold' },
  stranger: { label: 'With a stranger', icon: Globe, tone: 'verdigris' },
  superior: { label: 'Before a superior', icon: Landmark, tone: 'warning' },
}

export const BEHAVIOURS: Record<Schema['NormBehaviour'], Named> = {
  jest: { label: 'Jesting', icon: PartyPopper, tone: 'gold' },
  boast: { label: 'Boasting', icon: Trophy, tone: 'warning' },
  insult: { label: 'Insults', icon: HeartCrack, tone: 'danger' },
  flattery: { label: 'Flattery', icon: Sparkles, tone: 'info' },
  flirting: { label: 'Flirting', icon: Heart, tone: 'success' },
  gifts: { label: 'Gifts', icon: Gem, tone: 'gold' },
  quarrels: { label: 'Quarrels', icon: MessageCircle, tone: 'warning' },
  blows: { label: 'Blows', icon: Swords, tone: 'danger' },
  weapons_carried: { label: 'Carrying weapons', icon: Sword, tone: 'danger' },
  fine_dress: { label: 'Fine dress', icon: Shirt, tone: 'gold' },
  plain_speech: { label: 'Plain speech', icon: MessageCircle, tone: 'info' },
  forbidden_food: { label: 'Forbidden food', icon: Utensils, tone: 'danger' },
  secrets: { label: 'Telling secrets', icon: KeyRound, tone: 'verdigris' },
}

export const ETHICS: Record<Schema['EthicalStance'], Named> = {
  required: { label: 'Required', icon: Star, tone: 'gold' },
  admirable: { label: 'Admirable', icon: Trophy, tone: 'success' },
  acceptable: { label: 'Acceptable', icon: Scale, tone: 'info' },
  frowned_upon: { label: 'Frowned upon', icon: EyeOff, tone: 'warning' },
  shameful: { label: 'Shameful', icon: HeartCrack, tone: 'danger' },
  unthinkable: { label: 'Unthinkable', icon: Skull, tone: 'danger' },
}

export const BIASES: Record<Schema['SocialBias'], Named> = {
  prestige: { label: 'Copies the renowned', icon: Crown, tone: 'gold' },
  conformity: { label: 'Copies the many', icon: Users, tone: 'info' },
  content: { label: 'Copies the gripping', icon: Flame, tone: 'warning' },
}

export const FORMATIVE: Record<Schema['FormativeKind'], Named> = {
  great_war: { label: 'A great war', icon: Swords, tone: 'danger' },
  victory: { label: 'A victory', icon: Trophy, tone: 'success' },
  defeat: { label: 'A defeat', icon: Flag, tone: 'danger' },
  plague: { label: 'A plague', icon: Bug, tone: 'danger' },
  famine: { label: 'A famine', icon: Wheat, tone: 'warning' },
  golden_age: { label: 'A golden age', icon: Sun, tone: 'gold' },
  conquest: { label: 'A conquest', icon: Castle, tone: 'warning' },
}

export const ROLES: Record<Schema['RoleKind'], Named> = {
  office: { label: 'Office', icon: Landmark, tone: 'gold' },
  profession: { label: 'A craft or trade', icon: Wrench, tone: 'info' },
  combat: { label: 'Fighting', icon: Swords, tone: 'danger' },
  priesthood: { label: 'Serving the gods', icon: Church, tone: 'gold' },
  inheritance: { label: 'Inheriting', icon: Coins, tone: 'success' },
}

export const ELIGIBILITY: Record<Schema['RoleEligibility'], Named> = {
  any: { label: 'Open to all', icon: Users, tone: 'success' },
  female_only: { label: 'Women only', icon: User, tone: 'warning' },
  male_only: { label: 'Men only', icon: User, tone: 'warning' },
  female_preferred: { label: 'Women first', icon: User, tone: 'info' },
  male_preferred: { label: 'Men first', icon: User, tone: 'info' },
}

export const DATING: Record<Schema['DatingSystemKind'], Named> = {
  regnal: { label: 'By reign', icon: Crown, tone: 'gold' },
  founding: { label: 'Since the founding', icon: Landmark, tone: 'info' },
  religious: { label: 'By a holy era', icon: Church, tone: 'gold' },
  celestial_cycle: {
    label: 'By the cycles of the sky',
    icon: CalendarDays,
    tone: 'verdigris',
  },
}

export const TINCTURES: Record<Schema['Tincture'], string> = {
  gold: 'Or (gold)',
  silver: 'Argent (silver)',
  red: 'Gules (red)',
  blue: 'Azure (blue)',
  green: 'Vert (green)',
  black: 'Sable (black)',
  purple: 'Purpure (purple)',
  orange: 'Tenné (orange)',
}

export const DIVISIONS: Record<Schema['HeraldicDivision'], string> = {
  plain: 'Plain',
  per_pale: 'Per pale',
  per_fess: 'Per fess',
  per_bend: 'Per bend',
  quarterly: 'Quarterly',
  chevron: 'A chevron',
  bordure: 'Within a border',
}

export const CHARGES: Record<Schema['HeraldicCharge'], string> = {
  none: 'No charge',
  beast: 'A beast',
  bird: 'A bird',
  tree: 'A tree',
  tower: 'A tower',
  sword: 'A sword',
  crown: 'A crown',
  star: 'A star',
  sun: 'A sun',
  moon: 'A moon',
  eye: 'An eye',
  hand: 'A hand',
  wheel: 'A wheel',
  wave: 'Waves',
  flame: 'A flame',
  key: 'A key',
}

export const BEARERS: Record<Schema['HeraldryHolderKind'], Named> = {
  house: { label: 'A house', icon: Home, tone: 'gold' },
  polity: { label: 'A realm', icon: Crown, tone: 'gold' },
  title: { label: 'A title', icon: Landmark, tone: 'info' },
  army: { label: 'An army', icon: Swords, tone: 'danger' },
  guild: { label: 'A guild or order', icon: Hammer, tone: 'verdigris' },
}

export const DESIGN_KINDS: Record<Schema['DesignKind'], Named> = {
  vessel: { label: 'A vessel', icon: Ship, tone: 'info' },
  skyship: { label: 'A skyship', icon: Wind, tone: 'verdigris' },
  siege_engine: { label: 'A siege engine', icon: Castle, tone: 'warning' },
}

export const PARTS: Record<Schema['DesignComponentKind'], Named> = {
  hull: { label: 'Hull', icon: Ship, tone: 'info' },
  propulsion: { label: 'Propulsion', icon: Wind, tone: 'info' },
  hold: { label: 'Hold', icon: Coins, tone: 'gold' },
  quarters: { label: 'Quarters', icon: Tent, tone: 'muted' },
  armour: { label: 'Armour', icon: Shield, tone: 'warning' },
  weapon: { label: 'Weapons', icon: Sword, tone: 'danger' },
  ward: { label: 'Wards', icon: Sparkles, tone: 'verdigris' },
  navigation: { label: 'Navigation', icon: Anchor, tone: 'info' },
  frame: { label: 'Frame', icon: Wrench, tone: 'muted' },
  counterweight: { label: 'Counterweight', icon: Mountain, tone: 'muted' },
}

export const SECTION_ICONS = {
  crowds: Flame,
  history: ScrollText,
  storylets: Drama,
  norms: Scale,
  generations: Baby,
  dating: CalendarDays,
  heraldry: Shield,
  designs: Ship,
} as const
