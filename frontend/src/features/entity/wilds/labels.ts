import {
  type LucideIcon,
  Angry,
  Apple,
  Axe,
  Baby,
  Beef,
  Beer,
  Biohazard,
  Bird,
  Blend,
  Bone,
  Brain,
  Bug,
  Candy,
  Carrot,
  Coffee,
  Crosshair,
  Dna,
  Dog,
  Drama,
  Droplet,
  Droplets,
  Drumstick,
  Ear,
  Eclipse,
  Egg,
  Eye,
  EyeOff,
  Feather,
  Fence,
  Fish,
  Flame,
  FlaskConical,
  Footprints,
  Gem,
  Ghost,
  Grape,
  Hand,
  HandHeart,
  HeartCrack,
  HeartPulse,
  Hexagon,
  History,
  Hourglass,
  House,
  Infinity as InfinityIcon,
  Layers,
  Leaf,
  LeafyGreen,
  Link2,
  Lock,
  Milk,
  Minus,
  Moon,
  Mountain,
  MountainSnow,
  Network,
  Nut,
  Palette,
  PartyPopper,
  PawPrint,
  Pill,
  Rabbit,
  Radar,
  Rat,
  Recycle,
  Repeat,
  ScanEye,
  Send,
  Shield,
  ShieldHalf,
  ShieldOff,
  Shovel,
  Shrimp,
  Shrub,
  Skull,
  Snowflake,
  Sparkle,
  Sparkles,
  Spline,
  Split,
  Sprout,
  Sun,
  Swords,
  Syringe,
  Target,
  Tractor,
  TreeDeciduous,
  TreePine,
  Trees,
  TrendingDown,
  TrendingUp,
  Triangle,
  Trophy,
  User,
  Users,
  Utensils,
  WandSparkles,
  Waves,
  Wheat,
  WheatOff,
  Wind,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type ProgressTone } from '@/components/ui/progress'
import { type KpiTone } from '@/components/domain'
import { type Named, named, plain } from '../environment/labels'

export { named, plain }
export type { Named }

export type BadgeTone =
  'secondary' | 'info' | 'success' | 'warning' | 'destructive' | 'default'

const PERCENT = 100

export const BADGE_OF: Record<KpiTone, BadgeTone> = {
  gold: 'default',
  verdigris: 'info',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'secondary',
}

export const BAR_OF: Record<KpiTone, ProgressTone> = {
  gold: 'default',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
}

export const ECOLOGY_ICON = Leaf
export const BEAST_ICON = Footprints
export const HERDS_ICON = Fence
export const WEB_ICON = Network

export const SIZE: Record<string, Named & { rank: number; hint: string }> = {
  tiny: {
    label: 'Tiny',
    icon: Bug,
    tone: 'muted',
    rank: 1,
    hint: 'Fits in a hand',
  },
  small: {
    label: 'Small',
    icon: Rabbit,
    tone: 'success',
    rank: 2,
    hint: 'Hare to hound',
  },
  medium: {
    label: 'Medium',
    icon: Dog,
    tone: 'info',
    rank: 3,
    hint: 'Wolf to deer',
  },
  large: {
    label: 'Large',
    icon: PawPrint,
    tone: 'gold',
    rank: 4,
    hint: 'Horse to bear',
  },
  huge: {
    label: 'Huge',
    icon: Mountain,
    tone: 'warning',
    rank: 5,
    hint: 'Towers over riders',
  },
  colossal: {
    label: 'Colossal',
    icon: MountainSnow,
    tone: 'danger',
    rank: 6,
    hint: 'Shakes the ground it walks',
  },
}

export const SIZE_STEPS = 6

export const DIET: Record<components['schemas']['Diet'], Named> = {
  herbivore: { label: 'Grazer', icon: Leaf, tone: 'success' },
  carnivore: { label: 'Hunter', icon: Beef, tone: 'danger' },
  omnivore: { label: 'Omnivore', icon: Utensils, tone: 'gold' },
  scavenger: { label: 'Scavenger', icon: Bone, tone: 'muted' },
  filter: { label: 'Filterer', icon: Shrimp, tone: 'info' },
  piscivore: { label: 'Fisher', icon: Fish, tone: 'info' },
  sanguivore: { label: 'Blood drinker', icon: Droplet, tone: 'danger' },
  photosynthetic: { label: 'Sun-fed', icon: Sun, tone: 'success' },
  mineral: { label: 'Stone-fed', icon: Gem, tone: 'verdigris' },
  soul: { label: 'Soul-fed', icon: Ghost, tone: 'verdigris' },
  void: { label: 'Void-fed', icon: Eclipse, tone: 'danger' },
  parasite: { label: 'Parasite', icon: Bug, tone: 'danger' },
  decomposer: { label: 'Decomposer', icon: Recycle, tone: 'muted' },
  chemosynthetic: {
    label: 'Ground-fed',
    icon: FlaskConical,
    tone: 'verdigris',
  },
  energy: { label: 'Power-fed', icon: Zap, tone: 'gold' },
}

export const SOCIALITY: Record<string, Named> = {
  solitary: { label: 'Lives alone', icon: User, tone: 'muted' },
  pack: { label: 'Runs in packs', icon: PawPrint, tone: 'warning' },
  herd: { label: 'Lives in herds', icon: Users, tone: 'success' },
  hive: { label: 'Lives in a hive', icon: Hexagon, tone: 'gold' },
  colony: { label: 'Lives in colonies', icon: Network, tone: 'info' },
  swarm: { label: 'Moves in swarms', icon: Wind, tone: 'warning' },
}

export const STAGE: Record<string, Named & { step: number; hint: string }> = {
  wild: {
    label: 'Wild',
    icon: Trees,
    tone: 'muted',
    step: 0,
    hint: 'No one keeps it',
  },
  tamed: {
    label: 'Tamed',
    icon: Hand,
    tone: 'info',
    step: 2,
    hint: 'Caught and gentled one by one',
  },
  herded: {
    label: 'Herded',
    icon: Fence,
    tone: 'verdigris',
    step: 3,
    hint: 'Kept and fed in herds',
  },
  domesticated: {
    label: 'Domesticated',
    icon: House,
    tone: 'success',
    step: 4,
    hint: 'Bred by people for generations',
  },
  breed: {
    label: 'A breed of its own',
    icon: Dna,
    tone: 'gold',
    step: 5,
    hint: 'A kind people made',
  },
  commensal: {
    label: 'Lives beside people',
    icon: House,
    tone: 'verdigris',
    step: 1,
    hint: 'Lives off what towns leave behind and tames more easily',
  },
  feral: {
    label: 'Gone feral',
    icon: TreeDeciduous,
    tone: 'warning',
    step: 0,
    hint: 'Once kept, now wild again where its keepers are gone',
  },
}

export type ProductPart = components['schemas']['ProductPart']

export const PRODUCT_PARTS: Record<ProductPart, Named> = {
  flesh: { label: 'Flesh', icon: Drumstick, tone: 'warning' },
  hide: { label: 'Hide', icon: Layers, tone: 'muted' },
  bone: { label: 'Bone', icon: Bone, tone: 'muted' },
  tusk: { label: 'Tusk or horn', icon: Triangle, tone: 'gold' },
  shell: { label: 'Shell', icon: Shield, tone: 'muted' },
  venom: { label: 'Venom', icon: Droplet, tone: 'danger' },
  fibre: { label: 'Fibre', icon: Spline, tone: 'muted' },
  milk: { label: 'Milk', icon: Milk, tone: 'success' },
  eggs: { label: 'Eggs', icon: Egg, tone: 'gold' },
  feathers: { label: 'Feathers', icon: Feather, tone: 'info' },
  reagent: { label: 'Reagent', icon: WandSparkles, tone: 'verdigris' },
  seed: { label: 'Seed or grain', icon: Wheat, tone: 'gold' },
  root: { label: 'Root', icon: Carrot, tone: 'warning' },
  fruit: { label: 'Fruit', icon: Apple, tone: 'success' },
  leaf: { label: 'Leaf', icon: Leaf, tone: 'success' },
  wood: { label: 'Wood', icon: TreePine, tone: 'muted' },
  sap: { label: 'Sap', icon: Droplets, tone: 'gold' },
  dye: { label: 'Dye', icon: Palette, tone: 'info' },
  toxin: { label: 'Toxin', icon: Skull, tone: 'danger' },
  oil: { label: 'Oil', icon: Droplet, tone: 'gold' },
  sugar: { label: 'Sugar', icon: Candy, tone: 'success' },
  spice: { label: 'Spice', icon: Sparkle, tone: 'warning' },
  resin: { label: 'Resin', icon: Droplets, tone: 'gold' },
  stimulant: { label: 'Stimulant', icon: Coffee, tone: 'warning' },
  fodder: { label: 'Fodder', icon: Wheat, tone: 'success' },
}

export const USE: Record<string, Named> = {
  draft: { label: 'Draught work', icon: Tractor, tone: 'gold' },
  mount: { label: 'Mount', icon: Footprints, tone: 'info' },
  dairy: { label: 'Dairy', icon: Milk, tone: 'success' },
  fibre: { label: 'Fibre', icon: Spline, tone: 'muted' },
  meat: { label: 'Meat', icon: Drumstick, tone: 'warning' },
  guard: { label: 'Guard', icon: Shield, tone: 'info' },
  hunting: { label: 'Hunting', icon: Target, tone: 'warning' },
  war: { label: 'War beast', icon: Swords, tone: 'danger' },
  companion: { label: 'Companion', icon: HandHeart, tone: 'success' },
  sacred: { label: 'Kept for rites', icon: Flame, tone: 'gold' },
  pest_control: { label: 'Pest hunter', icon: Rat, tone: 'success' },
  messenger: { label: 'Messenger', icon: Send, tone: 'info' },
  sensing: { label: 'Senses danger', icon: Radar, tone: 'info' },
  entertainment: { label: 'Entertainment', icon: PartyPopper, tone: 'gold' },
  reagent_source: {
    label: 'Source of reagents',
    icon: WandSparkles,
    tone: 'verdigris',
  },
  sport: { label: 'Sport and racing', icon: Trophy, tone: 'gold' },
  medicine: { label: 'Source of remedies', icon: Pill, tone: 'success' },
}

export const SPECIES_CLASS: Record<string, Named & { hint: string }> = {
  animal: {
    label: 'Animal',
    icon: PawPrint,
    tone: 'info',
    hint: 'Lives, hunts or grazes and can be herded',
  },
  plant: {
    label: 'Plant',
    icon: Sprout,
    tone: 'success',
    hint: 'Grows from the ground; it is gathered, sown and harvested',
  },
  fungus: {
    label: 'Fungus',
    icon: Shrub,
    tone: 'verdigris',
    hint: 'Grows without light; it is gathered and sown like a plant',
  },
  vermin: {
    label: 'Vermin',
    icon: Rat,
    tone: 'warning',
    hint: 'Spoils stores, eats crops and spreads sickness',
  },
}

export const BIOCHEMISTRY: Record<string, Named & { hint: string }> = {
  carbon_water: {
    label: 'Carbon and water',
    icon: Droplets,
    tone: 'info',
    hint: 'Life built on carbon in water',
  },
  carbon_ammonia: {
    label: 'Carbon and ammonia',
    icon: Snowflake,
    tone: 'verdigris',
    hint: 'Life built on carbon in ammonia',
  },
  silicon: {
    label: 'Silicon',
    icon: Mountain,
    tone: 'warning',
    hint: 'Life built on silicon',
  },
  crystal: {
    label: 'Crystal',
    icon: Gem,
    tone: 'gold',
    hint: 'Life that grows as crystal',
  },
  void: {
    label: 'Void',
    icon: Eclipse,
    tone: 'muted',
    hint: 'Life of the void; it lives on any world',
  },
  spirit: {
    label: 'Spirit',
    icon: Ghost,
    tone: 'gold',
    hint: 'Life of spirit; it lives on any world',
  },
  carbon_methane: {
    label: 'Carbon and methane',
    icon: Flame,
    tone: 'warning',
    hint: 'Life built on carbon in liquid methane',
  },
  plasma: {
    label: 'Plasma',
    icon: Zap,
    tone: 'gold',
    hint: 'Life held in charged gas',
  },
}

export const GROWTH_CYCLE: Record<string, Named & { hint: string }> = {
  annual: {
    label: 'Annual',
    icon: Sprout,
    tone: 'success',
    hint: 'Sown and harvested within a year',
  },
  perennial: {
    label: 'Perennial',
    icon: Repeat,
    tone: 'verdigris',
    hint: 'Lives on from year to year',
  },
  tree: {
    label: 'Tree',
    icon: TreePine,
    tone: 'gold',
    hint: 'Grows for years before it bears',
  },
}

export const CULTIVATION: Record<
  string,
  Named & { step: number; hint: string }
> = {
  wild: {
    label: 'Wild',
    icon: Trees,
    tone: 'muted',
    step: 0,
    hint: 'No one tends it',
  },
  gathered: {
    label: 'Gathered',
    icon: Hand,
    tone: 'info',
    step: 1,
    hint: 'Foragers gather it where it grows',
  },
  cultivated: {
    label: 'Cultivated',
    icon: Wheat,
    tone: 'success',
    step: 2,
    hint: 'Sown in fields',
  },
  cultivar: {
    label: 'Cultivar',
    icon: Dna,
    tone: 'gold',
    step: 3,
    hint: 'Bred by farmers for a better harvest',
  },
}

export const PLANT_YIELD: Record<components['schemas']['PlantYield'], Named> = {
  grain: { label: 'Grain', icon: Wheat, tone: 'gold' },
  tuber: { label: 'Tubers', icon: Nut, tone: 'warning' },
  fruit: { label: 'Fruit', icon: Grape, tone: 'success' },
  fibre: { label: 'Fibre', icon: Spline, tone: 'info' },
  dye: { label: 'Dye', icon: Palette, tone: 'verdigris' },
  timber: { label: 'Timber', icon: Axe, tone: 'warning' },
  herb: { label: 'Herbs', icon: LeafyGreen, tone: 'success' },
  brew_base: { label: 'Brew base', icon: Beer, tone: 'gold' },
  reagent: {
    label: 'Alchemical reagent',
    icon: FlaskConical,
    tone: 'verdigris',
  },
  poison: { label: 'Poison', icon: Skull, tone: 'danger' },
  fodder: { label: 'Fodder', icon: Sprout, tone: 'success' },
  oil: { label: 'Oil', icon: Droplet, tone: 'gold' },
  resin: { label: 'Resin', icon: Droplets, tone: 'warning' },
  spice: { label: 'Spice', icon: Flame, tone: 'danger' },
  stimulant: { label: 'Stimulant', icon: Zap, tone: 'warning' },
  sugar: { label: 'Sugar', icon: Candy, tone: 'gold' },
}

export const TREND: Record<string, Named & { badge: BadgeTone }> = {
  rising: {
    label: 'Rising',
    icon: TrendingUp,
    tone: 'success',
    badge: 'success',
  },
  steady: { label: 'Steady', icon: Minus, tone: 'muted', badge: 'secondary' },
  falling: {
    label: 'Falling',
    icon: TrendingDown,
    tone: 'danger',
    badge: 'destructive',
  },
}

export const TEMPER: Record<string, Named & { hint: string }> = {
  hungry: {
    label: 'Hungry',
    icon: Drumstick,
    tone: 'warning',
    hint: 'Awake and raiding for food',
  },
  territorial: {
    label: 'Territorial',
    icon: Shield,
    tone: 'warning',
    hint: 'Guards its lair against all comers',
  },
  sleeping: {
    label: 'Sleeping',
    icon: Moon,
    tone: 'muted',
    hint: 'Dormant in its lair',
  },
  enraged: {
    label: 'Enraged',
    icon: Angry,
    tone: 'danger',
    hint: 'Raging across the land',
  },
  bound: {
    label: 'Bound',
    icon: Lock,
    tone: 'verdigris',
    hint: 'Held by a master or a place',
  },
  tamed: {
    label: 'Tamed',
    icon: Hand,
    tone: 'success',
    hint: 'Ridden or kept by a master',
  },
  companion: {
    label: 'Companion',
    icon: HandHeart,
    tone: 'success',
    hint: 'Kept at a mortal’s side as a pet',
  },
  wounded: {
    label: 'Wounded',
    icon: HeartCrack,
    tone: 'danger',
    hint: 'Keeps to its lair to heal, and strikes harder if cornered',
  },
  brooding: {
    label: 'Brooding',
    icon: Egg,
    tone: 'warning',
    hint: 'Guards its young in its lair against all who come near',
  },
  cowed: {
    label: 'Cowed',
    icon: ShieldOff,
    tone: 'muted',
    hint: 'Keeps away from where it was driven off',
  },
}

export const HERD_TRAINING: Record<string, Named & { hint: string }> = {
  war: {
    label: 'War',
    icon: Swords,
    tone: 'danger',
    hint: 'Trained beasts join the community’s armies',
  },
  hunting: {
    label: 'Hunting',
    icon: Crosshair,
    tone: 'warning',
    hint: 'Trained beasts bring home more from the hunt',
  },
  guard: {
    label: 'Guard',
    icon: Shield,
    tone: 'info',
    hint: 'Trained beasts keep raiders from the herds',
  },
}

export const TRAIT: Record<components['schemas']['CreatureTrait'], Named> = {
  flying: { label: 'Flies', icon: Bird, tone: 'info' },
  venomous: { label: 'Venomous', icon: Syringe, tone: 'danger' },
  soul_eater: { label: 'Eats souls', icon: Ghost, tone: 'danger' },
  radiant: { label: 'Radiant', icon: Sun, tone: 'gold' },
  fissiparous: { label: 'Splits to breed', icon: Split, tone: 'verdigris' },
  hive_mind: { label: 'Hive mind', icon: Network, tone: 'gold' },
  stoneskin: { label: 'Stone skin', icon: Mountain, tone: 'muted' },
  time_rewinder: { label: 'Turns back time', icon: History, tone: 'verdigris' },
  shapeshifter: { label: 'Shapeshifter', icon: Blend, tone: 'verdigris' },
  mind_reader: { label: 'Reads minds', icon: Brain, tone: 'info' },
  armoured: { label: 'Armoured', icon: ShieldHalf, tone: 'muted' },
  burrowing: { label: 'Burrows', icon: Shovel, tone: 'warning' },
  aquatic: { label: 'Lives in water', icon: Fish, tone: 'info' },
  amphibious: { label: 'Amphibious', icon: Waves, tone: 'info' },
  pack_hunter: { label: 'Hunts in packs', icon: PawPrint, tone: 'danger' },
  ambush_predator: { label: 'Ambush hunter', icon: Crosshair, tone: 'danger' },
  regenerating: { label: 'Regrows wounds', icon: HeartPulse, tone: 'success' },
  poisonous_flesh: {
    label: 'Poisonous flesh',
    icon: Biohazard,
    tone: 'warning',
  },
  fire_breathing: { label: 'Breathes fire', icon: Flame, tone: 'danger' },
  cold_breathing: { label: 'Breathes frost', icon: Snowflake, tone: 'info' },
  echolocation: { label: 'Hears its way', icon: Radar, tone: 'info' },
  camouflage: { label: 'Camouflaged', icon: EyeOff, tone: 'verdigris' },
  swarm_breeder: { label: 'Breeds in swarms', icon: Egg, tone: 'warning' },
  long_lived: { label: 'Long-lived', icon: InfinityIcon, tone: 'gold' },
  mimic: { label: 'Mimic', icon: Drama, tone: 'verdigris' },
  spirit_sight: { label: 'Sees spirits', icon: ScanEye, tone: 'verdigris' },
  iron_eating: { label: 'Eats iron', icon: Nut, tone: 'muted' },
  crop_pest: { label: 'Crop pest', icon: WheatOff, tone: 'warning' },
  plague_bearer: { label: 'Plague bearer', icon: Biohazard, tone: 'danger' },
  sacred_animal: { label: 'Sacred', icon: Sparkles, tone: 'gold' },
  horned: { label: 'Horned', icon: Mountain, tone: 'warning' },
  tailed: { label: 'Tailed', icon: Footprints, tone: 'muted' },
}

export const MATERIAL: Record<string, string> = {
  wood: 'Wood',
  calcified_tissue: 'Calcified tissue',
  hide: 'Hide',
  leather: 'Leather',
  cloth: 'Cloth',
  stone: 'Stone',
  flint: 'Flint',
  obsidian: 'Obsidian',
  copper: 'Copper',
  tin: 'Tin',
  bronze: 'Bronze',
  iron: 'Iron',
  steel: 'Steel',
  silver: 'Silver',
  gold: 'Gold',
  glass: 'Glass',
  crystal: 'Crystal',
  ceramic: 'Ceramic',
  composite: 'Composite',
  polymer: 'Polymer',
  resin: 'Resin',
  shell: 'Shell',
  silk: 'Silk',
  ivory: 'Ivory',
  chitin: 'Chitin',
  great_beast_tissue: 'Great beast tissue',
  star_metal: 'Star metal',
  void_glass: 'Void glass',
  divine_tissue: 'Divine tissue',
  living_wood: 'Living wood',
  halite: 'Halite',
  amber: 'Amber',
  lead: 'Lead',
  skysteel: 'Skysteel',
  sulfur: 'Sulfur',
  clay: 'Clay',
  gems: 'Gems',
  mud_brick: 'Mud brick',
  fired_brick: 'Fired brick',
  dressed_stone: 'Dressed stone',
  rubble: 'Rubble',
  lime_mortar: 'Lime mortar',
  hydraulic_concrete: 'Hydraulic concrete',
  thatch: 'Thatch',
  tile: 'Tile',
}

export const TEMPERAMENT: {
  key: 'aggression' | 'territoriality' | 'cunning' | 'fear_of_people'
  label: string
  icon: LucideIcon
  tone: ProgressTone
}[] = [
  { key: 'aggression', label: 'Aggression', icon: Swords, tone: 'destructive' },
  {
    key: 'territoriality',
    label: 'Territoriality',
    icon: Shield,
    tone: 'warning',
  },
  { key: 'cunning', label: 'Cunning', icon: Brain, tone: 'info' },
  {
    key: 'fear_of_people',
    label: 'Fear of people',
    icon: Ghost,
    tone: 'muted',
  },
]

export const MIGHT: {
  key: 'endurance' | 'perception' | 'willpower' | 'intelligence'
  label: string
  icon: LucideIcon
  tone: ProgressTone
}[] = [
  { key: 'endurance', label: 'Endurance', icon: HeartPulse, tone: 'success' },
  { key: 'perception', label: 'Perception', icon: Eye, tone: 'info' },
  { key: 'willpower', label: 'Willpower', icon: Flame, tone: 'warning' },
  { key: 'intelligence', label: 'Cunning', icon: Brain, tone: 'verdigris' },
]

export const FIELD_LABELS: Record<string, string> = {
  size_class: 'Size',
  diet: 'Diet',
  sociality: 'Social life',
  stage: 'Taming stage',
  body_plan: 'Body plan',
  lifespan_years: 'Lifespan in years',
  maturity_years: 'Years to grow up',
  litter_size: 'Young per litter',
  breeding_seasons: 'Litters a year',
  metabolism: 'Metabolism',
  temperature_min: 'Coldest it bears',
  temperature_max: 'Hottest it bears',
  water_need: 'Water need',
  altitude_min: 'Lowest ground',
  altitude_max: 'Highest ground',
  aggression: 'Aggression',
  territoriality: 'Territoriality',
  cunning: 'Cunning',
  fear_of_people: 'Fear of people',
  tameability: 'Tameability',
  nocturnal: 'Active at night',
  migratory: 'Migrates',
  habitat: 'Lands it loves',
  temper: 'Temper',
  endurance: 'Endurance',
  perception: 'Perception',
  willpower: 'Willpower',
  intelligence: 'Cunning',
  age: 'Age in years',
  lifespan: 'Lifespan in years',
  raids: 'Raids',
  hoard: 'Hoard',
  abundance: 'Abundance',
  trend: 'Trend',
  fit: 'Fit to the land',
  hunted: 'Hunting pressure',
  head: 'Head count',
  fed_epochs: 'Epochs fed',
  species_class: 'Kind of life',
  biochemistry: 'What its life is built on',
  growth_cycle: 'Growth cycle',
  growing_seasons: 'Growing seasons needed',
  soil_need: 'Soil it needs',
  cultivation: 'Cultivation',
  share: 'Share of the fields',
  training: 'Trained for',
  trained: 'Head trained',
}

export function fieldLabel(key: string): string {
  return plain(FIELD_LABELS, key)
}

export function labelsOf(
  table: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}

export function titled(value: string): string {
  return plain({}, value)
}

export const LIFE_ICONS = {
  lifespan: Hourglass,
  maturity: Sprout,
  litter: Baby,
  seasons: Repeat,
  metabolism: Flame,
  water: Droplets,
  bound: Link2,
  hearing: Ear,
  herd: PawPrint,
}

export function barTone(value: number, tone: KpiTone = 'gold'): ProgressTone {
  return value >= PERCENT / 2
    ? BAR_OF[tone]
    : value >= PERCENT / 5
      ? 'warning'
      : 'destructive'
}
