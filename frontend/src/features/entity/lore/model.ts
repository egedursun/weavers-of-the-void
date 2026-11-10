import {
  Amphora,
  Axe,
  Baby,
  Ban,
  Bone,
  Book,
  BookHeart,
  BookOpen,
  Brain,
  Castle,
  Church,
  CircleCheck,
  CircleDot,
  CircleX,
  CloudLightning,
  CloudRain,
  CloudSun,
  Coins,
  Compass,
  Crosshair,
  Crown,
  DoorOpen,
  Drama,
  Droplet,
  Droplets,
  Drum,
  Eye,
  Feather,
  Flag,
  Flame,
  FlaskConical,
  Flower2,
  Footprints,
  Gem,
  Ghost,
  Gift,
  Globe,
  Hammer,
  Hand,
  HardHat,
  HeartCrack,
  HeartHandshake,
  HeartPulse,
  Hourglass,
  Key,
  Landmark,
  LayoutGrid,
  Leaf,
  Lightbulb,
  Link,
  Map as MapIcon,
  Mic,
  Mountain,
  Music,
  Orbit,
  Package,
  Paintbrush,
  PartyPopper,
  PersonStanding,
  Scale,
  Scroll,
  ScrollText,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Skull,
  Slash,
  Smile,
  Sparkles,
  Spool,
  Sprout,
  Stamp,
  Star,
  Sun,
  Sunrise,
  Sword,
  Swords,
  Target,
  Telescope,
  Theater,
  Tornado,
  Trees,
  Unlink,
  Users,
  Utensils,
  UtensilsCrossed,
  VenetianMask,
  Wand,
  WandSparkles,
  Waypoints,
  Wheat,
  Wrench,
  Zap,
  type LucideIcon,
  Lock,
  LockOpen,
  Shirt,
  Atom,
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
  flood: {
    label: 'Great flood',
    icon: CloudRain,
    tone: 'info',
    hint: 'The waters rose and washed an age away.',
  },
  betrayal: {
    label: 'Betrayal',
    icon: HeartCrack,
    tone: 'danger',
    hint: 'Trust given, trust broken, and the price paid.',
  },
  lost_paradise: {
    label: 'Lost paradise',
    icon: Trees,
    tone: 'success',
    hint: 'Once there was a better place, and it was lost.',
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
  return_of_the_king: {
    label: 'Return of the king',
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
}

export const TRADITION_KINDS: Record<Schemas['TraditionKind'], LoreNamed> = {
  festival: { label: 'Festival', icon: PartyPopper, tone: 'gold' },
  fast: { label: 'Fast', icon: UtensilsCrossed, tone: 'info' },
  funeral_rite: { label: 'Funeral rite', icon: Flower2, tone: 'muted' },
  initiation: { label: 'Initiation', icon: Flame, tone: 'warning' },
  marriage_rite: {
    label: 'Marriage rite',
    icon: HeartHandshake,
    tone: 'success',
  },
  coming_of_age: { label: 'Coming of age', icon: Sprout, tone: 'success' },
  taboo: { label: 'Taboo', icon: Ban, tone: 'danger' },
  offering: { label: 'Offering', icon: Gift, tone: 'gold' },
  pilgrimage: { label: 'Pilgrimage', icon: Footprints, tone: 'verdigris' },
  hospitality_law: {
    label: 'Law of hospitality',
    icon: DoorOpen,
    tone: 'success',
  },
  duel_custom: { label: 'Duelling custom', icon: Swords, tone: 'danger' },
  mourning: { label: 'Mourning', icon: CloudRain, tone: 'muted' },
  harvest_rite: { label: 'Harvest rite', icon: Wheat, tone: 'gold' },
  war_dance: { label: 'War dance', icon: Drum, tone: 'danger' },
  scar_rite: { label: 'Scar rite', icon: Droplet, tone: 'danger' },
  ancestor_feast: {
    label: 'Feast of ancestors',
    icon: Utensils,
    tone: 'verdigris',
  },
  siesta: { label: 'Midday rest', icon: Sun, tone: 'gold' },
  night_vigil: { label: 'Night vigil', icon: Flame, tone: 'info' },
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
}

export const DEEDS: Record<Schemas['ItemDeed'], LoreNamed> = {
  made: { label: 'Made', icon: Hammer, tone: 'gold' },
  owned: { label: 'Changed hands', icon: Hand, tone: 'info' },
  kill: { label: 'Took a life', icon: Skull, tone: 'danger' },
  battle: { label: 'Went to battle', icon: Swords, tone: 'warning' },
  coronation: { label: 'Crowned a ruler', icon: Crown, tone: 'gold' },
  lost: { label: 'Was lost', icon: CircleX, tone: 'danger' },
  theft: { label: 'Was stolen', icon: VenetianMask, tone: 'danger' },
  burial: { label: 'Was buried', icon: Flower2, tone: 'muted' },
  broken: { label: 'Was broken', icon: Unlink, tone: 'danger' },
  repaired: { label: 'Was mended', icon: Wrench, tone: 'success' },
  enchanted: { label: 'Was enchanted', icon: Sparkles, tone: 'verdigris' },
  given: { label: 'Was given away', icon: Gift, tone: 'info' },
  captured: { label: 'Was captured', icon: Flag, tone: 'danger' },
}

export const MEDIUMS: Record<Schemas['ArtMedium'], LoreNamed> = {
  song: { label: 'Song', icon: Music, tone: 'info' },
  epic_poem: { label: 'Epic poem', icon: ScrollText, tone: 'gold' },
  play: { label: 'Play', icon: Theater, tone: 'verdigris' },
  statue: { label: 'Statue', icon: PersonStanding, tone: 'muted' },
  fresco: { label: 'Fresco', icon: Paintbrush, tone: 'info' },
  tapestry: { label: 'Tapestry', icon: Spool, tone: 'gold' },
  mosaic: { label: 'Mosaic', icon: LayoutGrid, tone: 'verdigris' },
  book: { label: 'Book', icon: BookOpen, tone: 'info' },
  dance: { label: 'Dance', icon: Footprints, tone: 'success' },
  music: { label: 'Music', icon: Music, tone: 'info' },
  carving: { label: 'Carving', icon: Hammer, tone: 'muted' },
  architecture_ornament: {
    label: 'Ornament in stone',
    icon: Landmark,
    tone: 'gold',
  },
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
