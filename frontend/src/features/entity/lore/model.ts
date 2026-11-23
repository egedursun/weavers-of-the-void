import {
  Amphora,
  Atom,
  Axe,
  Baby,
  Ban,
  BatteryLow,
  Bone,
  Book,
  BookHeart,
  BookOpen,
  Bot,
  Brain,
  Castle,
  Church,
  CircleCheck,
  CircleDot,
  CircleX,
  CloudLightning,
  CloudRain,
  CloudSun,
  Cog,
  Coins,
  Compass,
  Copy,
  Cpu,
  Crosshair,
  Crown,
  Dices,
  Disc,
  DoorOpen,
  Drama,
  Droplet,
  Droplets,
  Drum,
  Eraser,
  Eye,
  EyeOff,
  FastForward,
  Feather,
  FilePen,
  FileSearch,
  Flag,
  Flame,
  FlaskConical,
  Flower2,
  Footprints,
  Gem,
  Ghost,
  Gift,
  GitBranch,
  Globe,
  Hammer,
  Hand,
  HardHat,
  Heart,
  HeartCrack,
  HeartHandshake,
  HeartPulse,
  Hourglass,
  Key,
  Landmark,
  Leaf,
  Lightbulb,
  Link,
  Lock,
  LockOpen,
  Map as MapIcon,
  MapPin,
  Mic,
  Milestone,
  Monitor,
  Moon,
  Mountain,
  Move,
  Music,
  Orbit,
  Package,
  Paintbrush,
  PartyPopper,
  PersonStanding,
  Pill,
  Puzzle,
  Radio,
  RefreshCcw,
  Scale,
  Scroll,
  ScrollText,
  Shapes,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Shirt,
  Skull,
  Slash,
  Smile,
  Snail,
  Sparkles,
  Spool,
  Sprout,
  Stamp,
  Star,
  Store,
  Sun,
  Sunrise,
  Sword,
  Swords,
  Tag,
  Target,
  Telescope,
  Theater,
  Tornado,
  Trees,
  type LucideIcon,
  Unlink,
  UserCog,
  Users,
  Utensils,
  UtensilsCrossed,
  VenetianMask,
  VolumeX,
  Wand,
  WandSparkles,
  Waypoints,
  Wheat,
  Wind,
  Wrench,
  Zap,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { BRANCH_ICON } from '@/features/languages/languageIcons'
import { useGodAction } from '@/features/pantheon/godAction'
import { VALUE_ICONS } from '../mind/labels'
import { CLASS_SPEC } from '../society/labels'

type Schemas = components['schemas']
export type LoreNamed = {
  label: string
  icon: LucideIcon
  tone: KpiTone
  hint?: string
}

export const LORE_GRID = 'grid min-w-0 grid-cols-1 gap-3 @xl/lore:grid-cols-2'
export const KPI_GRID =
  'grid min-w-0 grid-cols-1 gap-3 @xs/lore:grid-cols-2 @3xl/lore:grid-cols-4'
export const WORKING = 'Working…'
export const PERCENT = 100
export const MAX_POWER = 10
export const MAX_LEVEL = 10
export const LORE_KINDS = [
  'language',
  'legend',
  'tradition',
  'ideology',
  'rite',
  'prophecy',
  'item',
  'artwork',
  'theory',
  'art_form',
] as const
export type LoreKind = (typeof LORE_KINDS)[number]

export const LORE_KIND: Record<LoreKind, LoreNamed> = {
  language: { label: 'Tongue', icon: Mic, tone: 'info' },
  legend: { label: 'Legend', icon: Feather, tone: 'gold' },
  tradition: { label: 'Tradition', icon: Users, tone: 'verdigris' },
  ideology: { label: 'Creed', icon: Lightbulb, tone: 'gold' },
  rite: { label: 'Rite', icon: WandSparkles, tone: 'verdigris' },
  prophecy: { label: 'Prophecy', icon: ScrollText, tone: 'warning' },
  item: { label: 'Item', icon: Gem, tone: 'gold' },
  artwork: { label: 'Artwork', icon: Paintbrush, tone: 'info' },
  theory: { label: 'Theory', icon: Atom, tone: 'info' },
  art_form: { label: 'Art form', icon: Music, tone: 'verdigris' },
}

export const ARCHETYPES: Record<Schemas['LegendArchetype'], LoreNamed> = {
  hero_quest: {
    label: "Hero's quest",
    icon: Swords,
    tone: 'gold',
    hint: 'A hero goes out into danger and comes home changed.',
  },
  monster: {
    label: 'Monster tale',
    icon: Skull,
    tone: 'danger',
    hint: 'Something hungry waits beyond the firelight.',
  },
  trickster: {
    label: 'Trickster tale',
    icon: Drama,
    tone: 'verdigris',
    hint: 'A clever one fools the strong and the proud.',
  },
  creation: {
    label: 'Creation myth',
    icon: Sunrise,
    tone: 'gold',
    hint: 'How the world, or a people, first came to be.',
  },
  world_disaster: {
    label: 'World disaster',
    icon: CloudRain,
    tone: 'info',
    hint: 'A disaster swept an age away.',
  },
  betrayal: {
    label: 'Betrayal',
    icon: HeartCrack,
    tone: 'danger',
    hint: 'Trust given, trust broken, and the price paid.',
  },
  lost_golden_age: {
    label: 'Lost golden age',
    icon: Trees,
    tone: 'success',
    hint: 'Once there was a better time, and it was lost.',
  },
  chosen_one: {
    label: 'Chosen one',
    icon: Star,
    tone: 'gold',
    hint: 'One is marked from birth for something great.',
  },
  cursed_line: {
    label: 'Cursed line',
    icon: Unlink,
    tone: 'danger',
    hint: 'A house carries a doom from one generation to the next; it costs that house prestige.',
  },
  return_of_a_ruler: {
    label: 'Return of a ruler',
    icon: Crown,
    tone: 'gold',
    hint: 'The rightful ruler will come back; a pretender who fits it gains a claim.',
  },
  haunted_place: {
    label: 'Haunted place',
    icon: Ghost,
    tone: 'verdigris',
    hint: 'A place the dead will not leave; settlers shun it while the tale is believed.',
  },
  founding: {
    label: 'Founding',
    icon: Landmark,
    tone: 'gold',
    hint: 'How a people, a town or an order first came to be.',
  },
  exile: {
    label: 'Exile',
    icon: Footprints,
    tone: 'muted',
    hint: 'Someone is driven out and must make a life elsewhere.',
  },
  transformation: {
    label: 'Transformation',
    icon: RefreshCcw,
    tone: 'verdigris',
    hint: 'Someone or something becomes another thing.',
  },
  bargain: {
    label: 'Bargain',
    icon: Scale,
    tone: 'warning',
    hint: 'A deal is struck, and its terms are kept or broken.',
  },
  sacrifice: {
    label: 'Sacrifice',
    icon: HeartHandshake,
    tone: 'danger',
    hint: 'Something dear is given up for the sake of others.',
  },
  rivalry: {
    label: 'Rivalry',
    icon: Crosshair,
    tone: 'danger',
    hint: 'Two sides contend for the same place, prize or name.',
  },
  discovery: {
    label: 'Discovery',
    icon: Compass,
    tone: 'info',
    hint: 'Something unknown is found and changes what people know.',
  },
  deception: {
    label: 'Deception',
    icon: Drama,
    tone: 'warning',
    hint: 'A lie or a disguise turns the course of events.',
  },
  union: {
    label: 'Union',
    icon: Link,
    tone: 'success',
    hint: 'Two people, houses or peoples are joined.',
  },
  ascent: {
    label: 'Ascent',
    icon: Mountain,
    tone: 'gold',
    hint: 'Someone rises from little to great standing.',
  },
  fall: {
    label: 'Fall',
    icon: CloudLightning,
    tone: 'muted',
    hint: 'The great are brought low.',
  },
}

export const RITE_STAGES: Record<Schemas['RiteStage'], LoreNamed> = {
  birth: { label: 'Birth', icon: Baby, tone: 'success' },
  naming: { label: 'Naming', icon: Tag, tone: 'info' },
  coming_of_age: { label: 'Coming of age', icon: Sprout, tone: 'success' },
  union: { label: 'Union', icon: HeartHandshake, tone: 'gold' },
  elderhood: { label: 'Elderhood', icon: Hourglass, tone: 'verdigris' },
  death: { label: 'Death', icon: Flower2, tone: 'muted' },
}

export const TRADITION_KINDS: Record<Schemas['TraditionFunction'], LoreNamed> =
  {
    festival: { label: 'Festival', icon: PartyPopper, tone: 'gold' },
    fast: { label: 'Fast', icon: UtensilsCrossed, tone: 'info' },
    rite_of_passage: {
      label: 'Rite of passage',
      icon: Milestone,
      tone: 'success',
    },
    taboo: { label: 'Taboo', icon: Ban, tone: 'danger' },
    offering: { label: 'Offering', icon: Gift, tone: 'gold' },
    pilgrimage: { label: 'Pilgrimage', icon: Footprints, tone: 'verdigris' },
    hospitality: {
      label: 'Hospitality',
      icon: DoorOpen,
      tone: 'success',
    },
    duel_custom: { label: 'Duelling custom', icon: Swords, tone: 'danger' },
    mourning: { label: 'Mourning', icon: CloudRain, tone: 'muted' },
    seasonal_rite: { label: 'Seasonal rite', icon: Wheat, tone: 'gold' },
    martial_display: { label: 'Martial display', icon: Drum, tone: 'danger' },
    body_marking: { label: 'Body marking', icon: Droplet, tone: 'danger' },
    ancestral_rite: {
      label: 'Ancestral rite',
      icon: Utensils,
      tone: 'verdigris',
    },
    rest_custom: { label: 'Custom of rest', icon: Sun, tone: 'gold' },
    vigil: { label: 'Vigil', icon: Flame, tone: 'info' },
    gift_custom: { label: 'Custom of gifts', icon: Gift, tone: 'success' },
    purification: { label: 'Purification', icon: Droplets, tone: 'verdigris' },
    commemoration: { label: 'Commemoration', icon: Landmark, tone: 'muted' },
    competition: { label: 'Competition', icon: Sparkles, tone: 'gold' },
    fair: { label: 'Fair', icon: Store, tone: 'gold' },
  }

export const TRADITION_TERMS: Record<string, LoreNamed> = {
  food: { label: 'Food', icon: Wheat, tone: 'warning' },
  goods: { label: 'Goods', icon: Package, tone: 'warning' },
  cohesion: { label: 'Cohesion', icon: Users, tone: 'success' },
  satisfaction: { label: 'Satisfaction', icon: Smile, tone: 'success' },
  piety: { label: 'Piety', icon: Church, tone: 'gold' },
  food_saved: { label: 'Food saved', icon: Wheat, tone: 'success' },
  rest: { label: 'Midday rest', icon: Sun, tone: 'gold' },
  vigil: { label: 'Night vigil', icon: Flame, tone: 'info' },
  rite: { label: 'Rites for the dead', icon: Flower2, tone: 'muted' },
  scar: { label: 'Scarring', icon: Droplet, tone: 'danger' },
  fertility: { label: 'Births', icon: Baby, tone: 'success' },
  taboo: { label: 'Taboo kept', icon: Ban, tone: 'danger' },
  hospitality: { label: 'Safer roads', icon: DoorOpen, tone: 'success' },
  duels: { label: 'Duels', icon: Swords, tone: 'danger' },
  harvest: { label: 'Harvest', icon: Wheat, tone: 'gold' },
  martial: { label: 'Martial spirit', icon: Shield, tone: 'danger' },
  placation: { label: 'Spirits placated', icon: Ghost, tone: 'verdigris' },
}

export const TENETS: Record<Schemas['IdeologyTenet'], LoreNamed> = {
  legalism: { label: 'Legalism', icon: Scale, tone: 'info' },
  restraint: { label: 'Restraint', icon: Hand, tone: 'success' },
  egalitarianism: { label: 'Equality', icon: Users, tone: 'success' },
  divine_right: { label: 'Divine right', icon: Crown, tone: 'gold' },
  mercantilism: { label: 'Mercantilism', icon: Coins, tone: 'gold' },
  militarism: { label: 'Militarism', icon: Swords, tone: 'danger' },
  asceticism: { label: 'Asceticism', icon: Feather, tone: 'muted' },
  rationalism: { label: 'Rationalism', icon: Lightbulb, tone: 'info' },
  nature_harmony: { label: 'Harmony with nature', icon: Leaf, tone: 'success' },
  xenophobia: { label: 'Fear of strangers', icon: ShieldAlert, tone: 'danger' },
  cosmopolitanism: { label: 'Cosmopolitanism', icon: Globe, tone: 'info' },
  anti_god: { label: 'Godlessness', icon: Ban, tone: 'danger' },
  creatorism: { label: 'The Creator', icon: Sun, tone: 'gold' },
}

export const CLASSES: Record<Schemas['SocialClass'], LoreNamed> =
  Object.fromEntries(
    Object.entries(CLASS_SPEC).map(([key, spec]) => [
      key,
      { ...spec, tone: 'verdigris' },
    ])
  ) as Record<Schemas['SocialClass'], LoreNamed>

export const VALUES: Record<string, LoreNamed> = Object.fromEntries(
  Object.entries(VALUE_ICONS).map(([key, spec]) => [
    key,
    { ...spec, tone: spec.tone ?? 'muted' },
  ])
)

export const SCHOOLS: Record<Schemas['MagicSchool'], LoreNamed> = {
  elemental_fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  elemental_water: { label: 'Water', icon: Droplets, tone: 'info' },
  earth: { label: 'Earth', icon: Mountain, tone: 'success' },
  storm: { label: 'Storm', icon: CloudLightning, tone: 'info' },
  life: { label: 'Life', icon: Leaf, tone: 'success' },
  death: { label: 'Death', icon: Skull, tone: 'muted' },
  mind: { label: 'Mind', icon: Brain, tone: 'verdigris' },
  illusion: { label: 'Illusion', icon: Drama, tone: 'verdigris' },
  divination: { label: 'Divination', icon: Eye, tone: 'info' },
  warding: { label: 'Warding', icon: Shield, tone: 'gold' },
  binding: { label: 'Binding', icon: Link, tone: 'warning' },
  summoning: { label: 'Summoning', icon: Ghost, tone: 'verdigris' },
  blood: { label: 'Blood', icon: Droplet, tone: 'danger' },
  void: { label: 'Void', icon: Orbit, tone: 'danger' },
}

export const SOURCES: Record<Schemas['MagicSource'], LoreNamed> = {
  ley: { label: 'Ley lines', icon: Waypoints, tone: 'verdigris' },
  divine: { label: 'The divine', icon: Sun, tone: 'gold' },
  blood: { label: 'Blood', icon: Droplet, tone: 'danger' },
  soul: { label: 'Souls', icon: Ghost, tone: 'info' },
  reagent: { label: 'Reagents', icon: FlaskConical, tone: 'success' },
  void: { label: 'The void', icon: Orbit, tone: 'danger' },
}

export const BACKLASHES: Record<Schemas['BacklashKind'], LoreNamed> = {
  injury: { label: 'Injures the caster', icon: HeartCrack, tone: 'danger' },
  madness: { label: 'Madness', icon: Brain, tone: 'warning' },
  leak: { label: 'Magic leaks out', icon: Droplets, tone: 'warning' },
  escape: { label: 'Something escapes', icon: DoorOpen, tone: 'danger' },
  phenomenon: { label: 'Tears the world', icon: Tornado, tone: 'danger' },
}

export const RITE_COSTS: Record<string, LoreNamed> = {
  ley: { label: 'Ley', icon: Waypoints, tone: 'verdigris' },
  essence: { label: 'Essence', icon: Sparkles, tone: 'gold' },
  blood: { label: 'Blood', icon: Droplet, tone: 'danger' },
  souls: { label: 'Souls', icon: Ghost, tone: 'info' },
  reagents: { label: 'Reagents', icon: FlaskConical, tone: 'success' },
  sanity: { label: 'Sanity', icon: Brain, tone: 'warning' },
}

export const EFFECTS: Record<Schemas['RiteEffectKind'], LoreNamed> = {
  damage: { label: 'Destruction', icon: Zap, tone: 'danger' },
  heal: { label: 'Healing', icon: HeartPulse, tone: 'success' },
  weather_change: { label: 'Turns the weather', icon: CloudSun, tone: 'info' },
  curse: { label: 'Curse', icon: Skull, tone: 'danger' },
  bless: { label: 'Blessing', icon: Sparkles, tone: 'gold' },
  ward: { label: 'Ward', icon: Shield, tone: 'info' },
  scry: { label: 'Scrying', icon: Eye, tone: 'verdigris' },
  bind: { label: 'Binding', icon: Link, tone: 'warning' },
  summon: { label: 'Summoning', icon: Ghost, tone: 'verdigris' },
  raise_dead: { label: 'Raises the dead', icon: Bone, tone: 'danger' },
  fertility: { label: 'Fertility', icon: Baby, tone: 'success' },
  harvest_blessing: { label: 'Blesses the harvest', icon: Wheat, tone: 'gold' },
  seal_soul: { label: 'Seals a soul', icon: Lock, tone: 'warning' },
  unseal_soul: { label: 'Breaks a seal', icon: LockOpen, tone: 'info' },
  exorcise: { label: 'Exorcism', icon: Ban, tone: 'gold' },
  dispel: { label: 'Dispelling', icon: Eraser, tone: 'info' },
  longevity: { label: 'Longevity', icon: Hourglass, tone: 'verdigris' },
  move_target: { label: 'Moves another', icon: Move, tone: 'info' },
  move_self: { label: 'Moves oneself', icon: Footprints, tone: 'info' },
  push: { label: 'Pushes', icon: Wind, tone: 'warning' },
  shape_matter: { label: 'Shapes matter', icon: Mountain, tone: 'muted' },
  read_record: { label: 'Reads records', icon: FileSearch, tone: 'info' },
  seize_machine: { label: 'Seizes a machine', icon: Cog, tone: 'warning' },
  alter_record: { label: 'Alters records', icon: FilePen, tone: 'warning' },
  sense_emotion: { label: 'Senses feeling', icon: HeartPulse, tone: 'info' },
  sway_emotion: { label: 'Sways feeling', icon: Heart, tone: 'warning' },
  turn_fortune: { label: 'Turns fortune', icon: Dices, tone: 'gold' },
  drain_life: { label: 'Drains life', icon: Droplets, tone: 'danger' },
  drain_power: { label: 'Drains power', icon: BatteryLow, tone: 'danger' },
  copy_power: { label: 'Copies a power', icon: Copy, tone: 'verdigris' },
  project_self: { label: 'Leaves the body', icon: Ghost, tone: 'verdigris' },
  possess: { label: 'Possesses', icon: UserCog, tone: 'danger' },
  change_form: { label: 'Changes form', icon: Shapes, tone: 'verdigris' },
  conceal: { label: 'Conceals', icon: EyeOff, tone: 'muted' },
  nullify: { label: 'Nullifies powers', icon: Ban, tone: 'warning' },
  hasten: { label: 'Hastens', icon: FastForward, tone: 'success' },
  slow: { label: 'Slows', icon: Snail, tone: 'warning' },
  age: { label: 'Ages', icon: Hourglass, tone: 'danger' },
  renew: { label: 'Renews', icon: RefreshCcw, tone: 'success' },
  foresee: { label: 'Foresees', icon: Telescope, tone: 'gold' },
}

export const PREDICATES: Record<Schemas['ProphecyPredicate'], LoreNamed> = {
  dies: { label: 'A death', icon: Skull, tone: 'danger' },
  falls: { label: 'A city falls', icon: Castle, tone: 'danger' },
  born_in: { label: 'A birth', icon: Baby, tone: 'success' },
  sky_event: { label: 'A sign in the sky', icon: Telescope, tone: 'verdigris' },
  war_between: { label: 'A war', icon: Swords, tone: 'danger' },
  ruler_of: { label: 'A ruler rises', icon: Crown, tone: 'gold' },
  within_epochs: {
    label: 'Before the time runs out',
    icon: Hourglass,
    tone: 'warning',
  },
}

export const PROPHECY_STATES: Record<Schemas['ProphecyState'], LoreNamed> = {
  pending: { label: 'Awaiting', icon: Hourglass, tone: 'warning' },
  fulfilled: { label: 'Fulfilled', icon: CircleCheck, tone: 'success' },
  failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
}

export const PROPHECY_ARGS: Record<string, LoreNamed> = {
  entity: { label: 'Who', icon: Users, tone: 'info' },
  settlement: { label: 'Settlement', icon: Castle, tone: 'info' },
  house: { label: 'House', icon: Landmark, tone: 'gold' },
  kind: { label: 'Kind', icon: Telescope, tone: 'verdigris' },
  first: { label: 'First side', icon: Swords, tone: 'danger' },
  second: { label: 'Second side', icon: Swords, tone: 'danger' },
  polity: { label: 'Realm', icon: Crown, tone: 'gold' },
  chosen: { label: 'The chosen one', icon: Star, tone: 'gold' },
  epochs: { label: 'Epochs', icon: Hourglass, tone: 'warning' },
}

export const ITEM_CLASSES: Record<Schemas['ItemClass'], LoreNamed> = {
  blade: { label: 'Blade', icon: Sword, tone: 'danger' },
  longblade: { label: 'Longsword', icon: Sword, tone: 'danger' },
  axe: { label: 'Axe', icon: Axe, tone: 'danger' },
  spear: { label: 'Spear', icon: Slash, tone: 'danger' },
  polearm: { label: 'Polearm', icon: Slash, tone: 'danger' },
  mace: { label: 'Mace', icon: Hammer, tone: 'danger' },
  bow: { label: 'Bow', icon: Target, tone: 'danger' },
  crossbow: { label: 'Crossbow', icon: Crosshair, tone: 'danger' },
  sling: { label: 'Sling', icon: CircleDot, tone: 'danger' },
  throwing: { label: 'Throwing weapon', icon: Target, tone: 'danger' },
  staff: { label: 'Staff', icon: Wand, tone: 'verdigris' },
  armour: { label: 'Armour', icon: Shield, tone: 'info' },
  padding: { label: 'Padding', icon: Shirt, tone: 'muted' },
  cloak: { label: 'Cloak', icon: Shirt, tone: 'verdigris' },
  shield: { label: 'Shield', icon: ShieldCheck, tone: 'info' },
  helmet: { label: 'Helmet', icon: HardHat, tone: 'info' },
  crown: { label: 'Crown', icon: Crown, tone: 'gold' },
  sceptre: { label: 'Sceptre', icon: WandSparkles, tone: 'gold' },
  seal: { label: 'Seal', icon: Stamp, tone: 'gold' },
  ring: { label: 'Ring', icon: CircleDot, tone: 'gold' },
  standard: { label: 'Standard', icon: Flag, tone: 'gold' },
  holy_relic: { label: 'Holy relic', icon: Sparkles, tone: 'gold' },
  idol: { label: 'Idol', icon: PersonStanding, tone: 'gold' },
  prayer_book: { label: 'Prayer book', icon: BookHeart, tone: 'gold' },
  book: { label: 'Book', icon: Book, tone: 'info' },
  scroll: { label: 'Scroll', icon: Scroll, tone: 'info' },
  map: { label: 'Map', icon: MapIcon, tone: 'info' },
  astrolabe: { label: 'Astrolabe', icon: Compass, tone: 'verdigris' },
  tool: { label: 'Tool', icon: Wrench, tone: 'muted' },
  instrument: { label: 'Instrument', icon: Music, tone: 'verdigris' },
  mirror: { label: 'Mirror', icon: Eye, tone: 'verdigris' },
  vessel_object: { label: 'Vessel', icon: Amphora, tone: 'muted' },
  prosthesis: { label: 'Prosthesis', icon: Bone, tone: 'muted' },
  key: { label: 'Key', icon: Key, tone: 'muted' },
  jewel: { label: 'Jewel', icon: Gem, tone: 'gold' },
  currency: { label: 'Coin', icon: Coins, tone: 'gold' },
  firearm: { label: 'Firearm', icon: Crosshair, tone: 'danger' },
  device: { label: 'Device', icon: Cog, tone: 'info' },
  computer: { label: 'Computer', icon: Monitor, tone: 'info' },
  implant: { label: 'Implant', icon: Cpu, tone: 'verdigris' },
  drug: { label: 'Drug', icon: Pill, tone: 'warning' },
  vehicle_part: { label: 'Vehicle part', icon: Wrench, tone: 'muted' },
  communicator: { label: 'Communicator', icon: Radio, tone: 'info' },
}

export const CURSES: Record<Schemas['CurseKind'], LoreNamed> = {
  none: { label: 'Uncursed', icon: ShieldCheck, tone: 'success' },
  bloodthirst: {
    label: 'Bloodthirst',
    icon: Droplet,
    tone: 'danger',
    hint: 'It drives its bearer to kill.',
  },
  misfortune: {
    label: 'Misfortune',
    icon: CloudLightning,
    tone: 'danger',
    hint: 'Ill luck follows whoever holds it.',
  },
  wasting: {
    label: 'Wasting',
    icon: Hourglass,
    tone: 'danger',
    hint: 'It slowly drains its bearer.',
  },
  madness: {
    label: 'Madness',
    icon: Brain,
    tone: 'danger',
    hint: 'It whispers until the mind breaks.',
  },
  betrayal: {
    label: 'Betrayal',
    icon: HeartCrack,
    tone: 'danger',
    hint: 'Its bearer is betrayed, or betrays.',
  },
  barrenness: { label: 'Barrenness', icon: Ban, tone: 'success' },
  transformation: {
    label: 'Transformation',
    icon: ShieldCheck,
    tone: 'success',
  },
  sleep: { label: 'Sleep', icon: Moon, tone: 'success' },
  silence: { label: 'Silence', icon: VolumeX, tone: 'success' },
  hunger: { label: 'Hunger', icon: Utensils, tone: 'success' },
  forgetting: { label: 'Forgetting', icon: EyeOff, tone: 'success' },
  restlessness: { label: 'Restlessness', icon: Footprints, tone: 'success' },
  line_curse: { label: 'Line curse', icon: GitBranch, tone: 'success' },
  place_curse: { label: 'Place curse', icon: MapPin, tone: 'success' },
  compulsion: { label: 'Compulsion', icon: Link, tone: 'success' },
  aging: { label: 'Aging', icon: Hourglass, tone: 'success' },
  exposure: { label: 'Exposure', icon: Eye, tone: 'success' },
}

export const DEEDS: Record<Schemas['ItemDeed'], LoreNamed> = {
  made: { label: 'Made', icon: Hammer, tone: 'gold' },
  owned: { label: 'Changed hands', icon: Hand, tone: 'info' },
  kill: { label: 'Took a life', icon: Skull, tone: 'danger' },
  battle: { label: 'Went to battle', icon: Swords, tone: 'warning' },
  coronation: { label: 'Worn at an accession', icon: Crown, tone: 'gold' },
  lost: { label: 'Was lost', icon: CircleX, tone: 'danger' },
  theft: { label: 'Was stolen', icon: VenetianMask, tone: 'danger' },
  burial: { label: 'Was buried', icon: Flower2, tone: 'muted' },
  broken: { label: 'Was broken', icon: Unlink, tone: 'danger' },
  repaired: { label: 'Was mended', icon: Wrench, tone: 'success' },
  enchanted: { label: 'Was enchanted', icon: Sparkles, tone: 'verdigris' },
  given: { label: 'Was given away', icon: Gift, tone: 'info' },
  captured: { label: 'Was captured', icon: Flag, tone: 'danger' },
}

export const MEDIUMS: Record<Schemas['ArtMode'], LoreNamed> = {
  verbal: { label: 'Verbal art', icon: ScrollText, tone: 'gold' },
  musical: { label: 'Music', icon: Music, tone: 'info' },
  movement: { label: 'Movement', icon: Footprints, tone: 'success' },
  ritual_performance: {
    label: 'Performance',
    icon: Theater,
    tone: 'verdigris',
  },
  flat_image: { label: 'Flat image', icon: Paintbrush, tone: 'info' },
  solid_image: { label: 'Solid image', icon: PersonStanding, tone: 'muted' },
  built: { label: 'Built form', icon: Landmark, tone: 'gold' },
  textile_image: { label: 'Textile image', icon: Spool, tone: 'gold' },
  worn: { label: 'Worn art', icon: Shirt, tone: 'verdigris' },
  culinary: { label: 'Culinary art', icon: Utensils, tone: 'success' },
  scent: { label: 'Scent art', icon: Wind, tone: 'info' },
  light: { label: 'Light art', icon: Lightbulb, tone: 'gold' },
  recorded: { label: 'Recorded art', icon: Disc, tone: 'info' },
  interactive: { label: 'Interactive art', icon: Puzzle, tone: 'verdigris' },
  landscape: { label: 'Landscape art', icon: Trees, tone: 'success' },
  body: { label: 'Body art', icon: Hand, tone: 'warning' },
  made_mind_art: { label: 'Made-mind art', icon: Bot, tone: 'muted' },
}

export const SPEAKER_KINDS: Record<Schemas['SpeakerKind'], LoreNamed> = {
  native: { label: 'Mother tongue', icon: Users, tone: 'gold' },
  second: { label: 'Second tongue', icon: Globe, tone: 'info' },
  liturgical: { label: 'Tongue of worship', icon: Church, tone: 'verdigris' },
}

export const BRANCH_TONE: Record<Schemas['KnowledgeBranch'], KpiTone> = {
  agriculture: 'success',
  metallurgy: 'warning',
  seafaring: 'info',
  writing: 'gold',
  architecture: 'gold',
  medicine: 'success',
  magic: 'verdigris',
  warfare: 'danger',
  astronomy: 'info',
  trade: 'gold',
  sky_navigation: 'verdigris',
  shipbuilding: 'info',
  gate_lore: 'verdigris',
  pathfinding: 'verdigris',
  void_living: 'verdigris',
  immortality: 'verdigris',
  biomancy: 'verdigris',
  forbidden: 'danger',
  civics: 'gold',
  law: 'gold',
  natural_history: 'success',
  language_lore: 'verdigris',
  mathematics: 'info',
}

const BRANCH_LABEL: Partial<Record<Schemas['KnowledgeBranch'], string>> = {
  forbidden: 'Forbidden arts',
  void_living: 'Living in the void',
}

export function branchOf(branch: string): LoreNamed {
  const key = branch as Schemas['KnowledgeBranch']
  return {
    label: BRANCH_LABEL[key] ?? sentence(branch),
    icon: BRANCH_ICON[key] ?? BookOpen,
    tone: BRANCH_TONE[key] ?? 'muted',
  }
}

export const FIELDS: Record<string, string> = {
  custom_class_id: 'Class of your own',
  prestige: 'Prestige',
  standardisation: 'Standardisation',
  liturgical: 'Tongue of worship',
  lingua_franca: 'Tongue of the trade roads',
  archetype: 'Kind of tale',
  credence: 'Belief',
  distortion: 'Distortion',
  moral: 'Moral',
  kind: 'Kind',
  calendar_slot: 'When it is kept',
  taboo_target: 'What it forbids',
  cost: 'Cost',
  effects: 'Effects',
  value_delta: 'Values',
  appeal: 'Appeal',
  school: 'School',
  source: 'Drawn from',
  backlash: 'Backlash',
  power: 'Power',
  backlash_chance: 'Backlash chance',
  holy: 'Holy',
  heretical: 'Heretical',
  predicate: 'Foretells',
  deadline_epoch: 'Deadline epoch',
  retold: 'Times retold',
  forged: 'Forged by a ruler',
  rival_entity_id: 'Rival prophecy',
  pressure: 'Pressure',
  args: 'Terms',
  item_class: 'Class',
  curse: 'Curse',
  material: 'Material',
  quality: 'Quality',
  condition: 'Condition',
  renown: 'Renown',
  value: 'Worth',
  reach: 'Reach',
  coverage: 'Coverage',
  weight: 'Weight',
  symbol: 'A symbol of its people',
  medium: 'Medium',
  copies: 'Copies',
  performed: 'Performed aloud',
  propaganda: 'Propaganda',
  message: 'Message',
}

export function sentence(value: string): string {
  const text = value.replaceAll('_', ' ').trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function fieldLabel(key: string): string {
  return FIELDS[key] ?? sentence(key)
}

export function lookup(
  table: Record<string, LoreNamed>,
  key: string | null | undefined
): LoreNamed {
  if (key && table[key]) return table[key]
  return { label: sentence(key ?? ''), icon: Sparkles, tone: 'muted' }
}

export function isLoreKind(kind: string): kind is LoreKind {
  return (LORE_KINDS as readonly string[]).includes(kind)
}

export function busyOf(
  blocked: string | null,
  ...pending: boolean[]
): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

export function useLoreEdit(entityId: number) {
  return useGodAction<{ values: Record<string, unknown>; release?: string[] }>({
    run: ({ values, release }) =>
      unwrap(
        api.POST('/api/actions/lore:edit', {
          body: {
            entity_id: entityId,
            values: values as Record<string, never>,
            release: release ?? [],
          },
        })
      ),
  })
}
