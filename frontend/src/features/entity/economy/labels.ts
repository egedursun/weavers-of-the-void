import {
  Anchor,
  Apple,
  Carrot,
  Milk,
  Anvil,
  Axe,
  Beef,
  Beer,
  Bird,
  Box,
  Bug,
  Castle,
  CircleCheck,
  CircleDashed,
  CircleX,
  CloudLightning,
  Coins,
  Construction,
  Cross,
  Croissant,
  DoorClosed,
  Factory,
  Fish,
  FlaskConical,
  Flame,
  Footprints,
  Gem,
  Gift,
  Hammer,
  HandCoins,
  HandHeart,
  Hourglass,
  Landmark,
  Leaf,
  Link,
  Lock,
  Mountain,
  Orbit,
  Package,
  PackageMinus,
  PartyPopper,
  PawPrint,
  Pickaxe,
  Route,
  Scale,
  Shield,
  ShieldAlert,
  Ship,
  Shirt,
  Skull,
  Slice,
  Sparkles,
  Sprout,
  Store,
  Sun,
  Swords,
  Tent,
  Trash2,
  Trees,
  Utensils,
  Warehouse,
  Waves,
  Weight,
  Wheat,
  Wind,
  Wrench,
  Zap,
  type LucideIcon,
  Thermometer,
  Target,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { BRANCH_ICON } from '@/features/languages/languageIcons'

type Schemas = components['schemas']
export type CommodityKind = Schemas['CommodityKind']
export type WorkshopKind = Schemas['WorkshopKind']
export type TradeMode = Schemas['TradeMode']
export type TradeRouteStatus = Schemas['TradeRouteStatus']
export type MaterialFamily = Schemas['MaterialFamily']
export type MaterialKind = Schemas['MaterialKind']
export type MaterialOrigin = Schemas['MaterialOrigin']
export type KnowledgeBranch = Schemas['KnowledgeBranch']
export type TradeLoss = Schemas['TradeLoss']
export type LoanStatus = Schemas['LoanStatus']
export type MaterialSlot = Schemas['MaterialSlot']
export type DebtRemedy = Schemas['DebtRemedy']
export type FoeNature = Schemas['FoeNature']
export type GoodsFamily = 'subsistence' | 'industrial' | 'strategic' | 'luxury'
export type StoreKind = 'food' | 'ore' | 'goods'

export type Named = { label: string; icon: LucideIcon; tone: KpiTone }
type BadgeVariant = 'success' | 'info' | 'warning' | 'destructive' | 'outline'

export const COMMODITY: Record<
  CommodityKind,
  { label: string; icon: LucideIcon; family: GoodsFamily; store: StoreKind }
> = {
  grain: { label: 'Grain', icon: Wheat, family: 'subsistence', store: 'food' },
  livestock: {
    label: 'Livestock',
    icon: Beef,
    family: 'subsistence',
    store: 'food',
  },
  fish: { label: 'Fish', icon: Fish, family: 'subsistence', store: 'food' },
  fodder: {
    label: 'Fodder',
    icon: Sprout,
    family: 'subsistence',
    store: 'food',
  },
  timber: {
    label: 'Timber',
    icon: Trees,
    family: 'subsistence',
    store: 'goods',
  },
  fuel: { label: 'Fuel', icon: Flame, family: 'subsistence', store: 'goods' },
  bread: {
    label: 'Bread',
    icon: Croissant,
    family: 'subsistence',
    store: 'food',
  },
  ore: { label: 'Ore', icon: Mountain, family: 'industrial', store: 'ore' },
  stone: { label: 'Stone', icon: Box, family: 'industrial', store: 'ore' },
  cloth: { label: 'Cloth', icon: Shirt, family: 'industrial', store: 'goods' },
  tools: {
    label: 'Tools',
    icon: Wrench,
    family: 'industrial',
    store: 'goods',
  },
  weapons: {
    label: 'Weapons',
    icon: Swords,
    family: 'strategic',
    store: 'goods',
  },
  armour: {
    label: 'Armour',
    icon: Shield,
    family: 'strategic',
    store: 'goods',
  },
  mounts: {
    label: 'Mounts',
    icon: PawPrint,
    family: 'strategic',
    store: 'goods',
  },
  siege_materiel: {
    label: 'Siege materiel',
    icon: Castle,
    family: 'strategic',
    store: 'goods',
  },
  medicine: {
    label: 'Medicine',
    icon: FlaskConical,
    family: 'strategic',
    store: 'goods',
  },
  luxuries: { label: 'Luxuries', icon: Gem, family: 'luxury', store: 'goods' },
  incense: { label: 'Incense', icon: Wind, family: 'luxury', store: 'goods' },
  sacred_goods: {
    label: 'Sacred goods',
    icon: Cross,
    family: 'luxury',
    store: 'goods',
  },
  magical_reagents: {
    label: 'Magical reagents',
    icon: Sparkles,
    family: 'luxury',
    store: 'goods',
  },
  meat: { label: 'Meat', icon: Beef, family: 'subsistence', store: 'food' },
  milk: { label: 'Milk', icon: Milk, family: 'subsistence', store: 'food' },
  cheese: {
    label: 'Cheese',
    icon: Croissant,
    family: 'subsistence',
    store: 'food',
  },
  fruit: { label: 'Fruit', icon: Apple, family: 'subsistence', store: 'food' },
  tubers: {
    label: 'Tubers',
    icon: Carrot,
    family: 'subsistence',
    store: 'food',
  },
  coal: { label: 'Coal', icon: Flame, family: 'industrial', store: 'goods' },
  peat: { label: 'Peat', icon: Leaf, family: 'subsistence', store: 'goods' },
  dung: { label: 'Dung', icon: Flame, family: 'subsistence', store: 'goods' },
}

export const GOODS_FAMILY: Record<GoodsFamily, Named & { note: string }> = {
  subsistence: {
    label: 'Staples',
    icon: Wheat,
    tone: 'success',
    note: 'Food, fodder, timber and fuel',
  },
  industrial: {
    label: 'Crafts',
    icon: Hammer,
    tone: 'info',
    note: 'Ore, stone, cloth and tools',
  },
  strategic: {
    label: 'War goods',
    icon: Swords,
    tone: 'warning',
    note: 'Arms, armour, mounts, siege and medicine',
  },
  luxury: {
    label: 'Luxuries',
    icon: Gem,
    tone: 'gold',
    note: 'Fine goods, incense, relics and reagents',
  },
}

export const STORE: Record<
  StoreKind,
  Named & { keeper: WorkshopKind; room: string }
> = {
  food: {
    label: 'Food',
    icon: Wheat,
    tone: 'success',
    keeper: 'granary',
    room: 'granary room',
  },
  ore: {
    label: 'Ore and stone',
    icon: Mountain,
    tone: 'info',
    keeper: 'warehouse',
    room: 'warehouse room',
  },
  goods: {
    label: 'Goods',
    icon: Package,
    tone: 'gold',
    keeper: 'warehouse',
    room: 'warehouse room',
  },
}

export const STORE_KINDS: readonly StoreKind[] = ['food', 'ore', 'goods']

export const WORKSHOP: Record<WorkshopKind, Named> = {
  market: { label: 'Market', icon: Store, tone: 'gold' },
  granary: { label: 'Granary', icon: Warehouse, tone: 'success' },
  warehouse: { label: 'Warehouse', icon: Warehouse, tone: 'info' },
  mine: { label: 'Mine', icon: Pickaxe, tone: 'muted' },
  lumber_camp: { label: 'Lumber camp', icon: Axe, tone: 'verdigris' },
  fishery: { label: 'Fishery', icon: Fish, tone: 'info' },
  charcoal_kiln: { label: 'Charcoal kiln', icon: Flame, tone: 'warning' },
  forge: { label: 'Forge', icon: Anvil, tone: 'warning' },
  tannery: { label: 'Tannery', icon: Shirt, tone: 'gold' },
  mill: { label: 'Mill', icon: Wheat, tone: 'success' },
  brewery: { label: 'Brewery', icon: Beer, tone: 'gold' },
  weavery: { label: 'Weavery', icon: Shirt, tone: 'verdigris' },
  stable: { label: 'Stable', icon: PawPrint, tone: 'gold' },
  mason_yard: { label: 'Mason yard', icon: Box, tone: 'muted' },
  shipyard: { label: 'Shipyard', icon: Anchor, tone: 'info' },
  siege_yard: { label: 'Siege yard', icon: Castle, tone: 'danger' },
  alchemist: { label: 'Alchemist', icon: FlaskConical, tone: 'verdigris' },
  shrine_workshop: { label: 'Shrine workshop', icon: Cross, tone: 'gold' },
  mint: { label: 'Mint', icon: Coins, tone: 'gold' },
}

export const MODE: Record<TradeMode, Named> = {
  road: { label: 'Road', icon: Footprints, tone: 'gold' },
  river: { label: 'River way', icon: Waves, tone: 'info' },
  sea: { label: 'Sea lane', icon: Ship, tone: 'info' },
  caravan: { label: 'Caravan way', icon: Tent, tone: 'warning' },
  sky: { label: 'Sky lane', icon: Bird, tone: 'verdigris' },
}

export const ROUTE_STATUS: Record<
  TradeRouteStatus,
  Named & { variant: BadgeVariant }
> = {
  forming: {
    label: 'Forming',
    icon: CircleDashed,
    tone: 'info',
    variant: 'info',
  },
  open: { label: 'Open', icon: Route, tone: 'success', variant: 'success' },
  blockaded: {
    label: 'Blockaded',
    icon: ShieldAlert,
    tone: 'danger',
    variant: 'destructive',
  },
  closed: {
    label: 'Closed',
    icon: DoorClosed,
    tone: 'warning',
    variant: 'warning',
  },
  decayed: {
    label: 'Fallen out of use',
    icon: Hourglass,
    tone: 'muted',
    variant: 'outline',
  },
}

export const ROUTE_STATUSES: readonly TradeRouteStatus[] = [
  'open',
  'forming',
  'blockaded',
  'closed',
  'decayed',
]

export const TRADE_LOSS: Record<TradeLoss, Named> = {
  bandits: { label: 'bandits', icon: Skull, tone: 'danger' },
  sea: { label: 'the sea', icon: Waves, tone: 'info' },
  beasts: { label: 'beasts', icon: PawPrint, tone: 'warning' },
  weather: { label: 'the weather', icon: CloudLightning, tone: 'muted' },
}

export const LOAN_STATUS: Record<
  LoanStatus,
  Named & { variant: BadgeVariant }
> = {
  open: {
    label: 'Owed',
    icon: Hourglass,
    tone: 'warning',
    variant: 'warning',
  },
  repaid: {
    label: 'Repaid',
    icon: CircleCheck,
    tone: 'success',
    variant: 'success',
  },
  defaulted: {
    label: 'Defaulted',
    icon: CircleX,
    tone: 'danger',
    variant: 'destructive',
  },
  forgiven: {
    label: 'Forgiven',
    icon: HandHeart,
    tone: 'verdigris',
    variant: 'info',
  },
}

export const MATERIAL_FAMILY: Record<MaterialFamily, Named> = {
  organic: { label: 'Organic', icon: Leaf, tone: 'verdigris' },
  stone: { label: 'Stone', icon: Mountain, tone: 'muted' },
  metal: { label: 'Metal', icon: Anvil, tone: 'info' },
  precious: { label: 'Precious', icon: Gem, tone: 'gold' },
  exotic: { label: 'Exotic', icon: Sparkles, tone: 'warning' },
}

export const FAMILY_TONE: Record<MaterialFamily, KpiTone> = {
  organic: MATERIAL_FAMILY.organic.tone,
  stone: MATERIAL_FAMILY.stone.tone,
  metal: MATERIAL_FAMILY.metal.tone,
  precious: MATERIAL_FAMILY.precious.tone,
  exotic: MATERIAL_FAMILY.exotic.tone,
}

export const MATERIAL_ORIGIN: Record<MaterialOrigin, Named> = {
  catalog: { label: 'Of the world', icon: Mountain, tone: 'muted' },
  god_remains: { label: 'From a dead god', icon: Skull, tone: 'danger' },
  dead_star: { label: 'From a dead star', icon: Sun, tone: 'warning' },
  beast: { label: 'From a great beast', icon: PawPrint, tone: 'gold' },
  leak_crystal: { label: 'From a leak', icon: Gem, tone: 'verdigris' },
  research: { label: 'Discovered', icon: FlaskConical, tone: 'info' },
  divine: { label: 'Forged by a god', icon: Sparkles, tone: 'gold' },
}

export const MATERIAL_LABEL: Record<MaterialKind, string> = {
  wood: 'Wood',
  bone: 'Bone',
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
  ivory: 'Ivory',
  chitin: 'Chitin',
  dragonbone: 'Dragonbone',
  star_metal: 'Star metal',
  void_glass: 'Void glass',
  godflesh: 'Godflesh',
  living_wood: 'Living wood',
  salt: 'Salt',
  amber: 'Amber',
  lead: 'Lead',
  skysteel: 'Skysteel',
  sulfur: 'Sulfur',
  clay: 'Clay',
  gems: 'Gems',
}

export const MATERIAL_KINDS = Object.keys(MATERIAL_LABEL) as MaterialKind[]

export const BRANCH_LABEL: Record<KnowledgeBranch, string> = {
  agriculture: 'Agriculture',
  metallurgy: 'Metallurgy',
  seafaring: 'Seafaring',
  writing: 'Writing',
  architecture: 'Architecture',
  medicine: 'Medicine',
  magic: 'Magic',
  warfare: 'Warfare',
  astronomy: 'Astronomy',
  trade: 'Trade',
  sky_navigation: 'Sky navigation',
  shipbuilding: 'Shipbuilding',
  gate_lore: 'Gate lore',
  pathfinding: 'Pathfinding',
  void_living: 'Void living',
  immortality: 'Immortality',
  biomancy: 'Biomancy',
  forbidden: 'Forbidden lore',
  civics: 'Civics',
}

export function branch(kind: KnowledgeBranch): Named {
  return { label: BRANCH_LABEL[kind], icon: BRANCH_ICON[kind], tone: 'info' }
}

export const MATERIAL_PROPERTIES = [
  {
    key: 'hardness',
    label: 'Hardness',
    abbr: 'Hardness',
    icon: Shield,
    hint: 'Cuts and protects',
  },
  {
    key: 'toughness',
    label: 'Toughness',
    abbr: 'Toughness',
    icon: Hammer,
    hint: 'Takes blows without breaking',
  },
  {
    key: 'weight',
    label: 'Weight',
    abbr: 'Weight',
    icon: Weight,
    hint: 'Slows armies and burns them in heat',
  },
  {
    key: 'edge',
    label: 'Edge',
    abbr: 'Edge',
    icon: Slice,
    hint: 'How keen a blade gets',
  },
  {
    key: 'conductivity',
    label: 'Conductivity',
    abbr: 'Conducts',
    icon: Zap,
    hint: 'Holds enchantment',
  },
  {
    key: 'sanctity',
    label: 'Sanctity',
    abbr: 'Sanctity',
    icon: Sun,
    hint: 'Draws the gods',
  },
  {
    key: 'corruption',
    label: 'Corruption',
    abbr: 'Corruption',
    icon: Skull,
    hint: 'Draws outer beings',
  },
  {
    key: 'rarity',
    label: 'Rarity',
    abbr: 'Rarity',
    icon: Gem,
    hint: 'How seldom it is found',
  },
  {
    key: 'base_value',
    label: 'Worth',
    abbr: 'Worth',
    icon: Coins,
    hint: 'What it fetches at market',
  },
  {
    key: 'decay',
    label: 'Decay',
    abbr: 'Decay',
    icon: Hourglass,
    hint: 'How fast it wears away',
  },
  {
    key: 'melting_point',
    label: 'Melting point',
    abbr: 'Melts at',
    icon: Flame,
    hint: 'Heat a forge needs to work it; armour melts in fire this hot',
  },
  {
    key: 'ignition_point',
    label: 'Ignition point',
    abbr: 'Ignites at',
    icon: Flame,
    hint: 'Heat that sets it alight; 100 never burns',
  },
  {
    key: 'boiling_point',
    label: 'Boiling point',
    abbr: 'Boils at',
    icon: Thermometer,
    hint: 'Heat at which it is gone entirely',
  },
  {
    key: 'density',
    label: 'Density',
    abbr: 'Density',
    icon: Weight,
    hint: 'How heavy armour of it sits on the wearer',
  },
  {
    key: 'impact_yield',
    label: 'Impact yield',
    abbr: 'Blunt yield',
    icon: Hammer,
    hint: 'Blunt force it turns aside',
  },
  {
    key: 'impact_fracture',
    label: 'Impact fracture',
    abbr: 'Blunt break',
    icon: Hammer,
    hint: 'Blunt force that breaks it',
  },
  {
    key: 'shear_yield',
    label: 'Shear yield',
    abbr: 'Cut yield',
    icon: Slice,
    hint: 'Edges it turns aside',
  },
  {
    key: 'shear_fracture',
    label: 'Shear fracture',
    abbr: 'Cut break',
    icon: Slice,
    hint: 'Edges that cut through it',
  },
  {
    key: 'elasticity',
    label: 'Elasticity',
    abbr: 'Spring',
    icon: Target,
    hint: 'Draw of a bow made from it',
  },
  {
    key: 'thermal_conductivity',
    label: 'Heat conduction',
    abbr: 'Conducts heat',
    icon: Thermometer,
    hint: 'How much fire burns through armour of it',
  },
  {
    key: 'solid_density',
    label: 'Solid density',
    abbr: 'Solid mass',
    icon: Weight,
    hint: 'Mass behind a strike with a weapon of it',
  },
  {
    key: 'max_edge',
    label: 'Sharpness cap',
    abbr: 'Edge cap',
    icon: Slice,
    hint: 'The keenest edge it can hold',
  },
] as const

export const FLOW: Record<string, Named> = {
  extraction: { label: 'Dug and gathered', icon: Pickaxe, tone: 'info' },
  harvest: { label: 'Harvested', icon: Wheat, tone: 'success' },
  production: { label: 'Made in workshops', icon: Factory, tone: 'gold' },
  seed: { label: 'Seed and young stock', icon: Sprout, tone: 'verdigris' },
  input: { label: 'Used up by workshops', icon: Factory, tone: 'muted' },
  consumption: { label: 'Eaten and used', icon: Utensils, tone: 'muted' },
  trade: { label: 'Traded', icon: Scale, tone: 'gold' },
  tribute: { label: 'Tribute', icon: Landmark, tone: 'gold' },
  aid: { label: 'Aid', icon: HandHeart, tone: 'success' },
  loot: { label: 'Loot', icon: Swords, tone: 'danger' },
  loss: { label: 'Lost', icon: PackageMinus, tone: 'danger' },
  siege: { label: 'Spent in siege', icon: Castle, tone: 'danger' },
  war: { label: 'Spent at war', icon: Swords, tone: 'danger' },
  construction: { label: 'Built with', icon: Construction, tone: 'info' },
  overflow: {
    label: 'Spoiled for lack of room',
    icon: Trash2,
    tone: 'warning',
  },
  decay: { label: 'Rotted and rusted', icon: Bug, tone: 'warning' },
  player: { label: 'Your hand', icon: Sparkles, tone: 'gold' },
  tool: { label: 'Worn out as tools', icon: Wrench, tone: 'muted' },
  offering: { label: 'Offered to gods', icon: Gift, tone: 'gold' },
}

export const SPOILING_FLOWS = new Set(['overflow', 'decay'])

export function flow(kind: string): Named {
  return (
    FLOW[kind] ?? {
      label: kind.replaceAll('_', ' '),
      icon: Package,
      tone: 'muted',
    }
  )
}

export function qualityTier(quality: number): {
  label: string
  tone: KpiTone
  meter: 'muted' | 'default' | 'success' | 'verdigris'
} {
  if (quality >= 85)
    return { label: 'Masterwork', tone: 'verdigris', meter: 'verdigris' }
  if (quality >= 65) return { label: 'Fine', tone: 'success', meter: 'success' }
  if (quality >= 35) return { label: 'Common', tone: 'gold', meter: 'default' }
  return { label: 'Crude', tone: 'muted', meter: 'muted' }
}

export const ECONOMY_ICONS = {
  route: Route,
  bank: Landmark,
  coin: HandCoins,
  factory: Factory,
  goods: Package,
}

export function commodityLabel(kind: CommodityKind): string {
  return COMMODITY[kind].label
}

export function materialLabel(kind: MaterialKind | null): string | null {
  return kind === null ? null : MATERIAL_LABEL[kind]
}

export const MATERIAL_SLOT: Record<MaterialSlot, Named & { note: string }> = {
  body: {
    label: 'Body',
    icon: Box,
    tone: 'gold',
    note: 'What the thing itself is made of',
  },
  weapons: {
    label: 'Weapons',
    icon: Swords,
    tone: 'danger',
    note: 'What its blades and points are made of',
  },
  armour: {
    label: 'Armour',
    icon: Shield,
    tone: 'info',
    note: 'What its harness and shields are made of',
  },
  hull: {
    label: 'Hull',
    icon: Anchor,
    tone: 'info',
    note: 'What its hull is built from',
  },
  fabric: {
    label: 'Sails and fabric',
    icon: Wind,
    tone: 'verdigris',
    note: 'What its sails and rigging are woven from',
  },
}

export const DEBT_REMEDY: Record<
  DebtRemedy,
  Named & { variant: BadgeVariant; law: string; note: string }
> = {
  bondage: {
    label: 'Bondage law',
    law: 'Bondage',
    icon: Link,
    tone: 'danger',
    variant: 'destructive',
    note: 'Defaulters are bound into serfdom to work off what they owe.',
  },
  prison: {
    label: "Debtors' prison",
    law: 'Prison',
    icon: Lock,
    tone: 'warning',
    variant: 'warning',
    note: 'A notable of the defaulter is jailed until the debt is ransomed.',
  },
  jubilee: {
    label: 'Jubilee',
    law: 'Jubilee',
    icon: PartyPopper,
    tone: 'verdigris',
    variant: 'info',
    note: 'Every debt is wiped clean after a set number of epochs.',
  },
}

export const DEBT_REMEDIES = Object.keys(DEBT_REMEDY) as DebtRemedy[]

export const FOE_NATURE: Record<FoeNature, Named> = {
  undead: { label: 'Undead', icon: Skull, tone: 'danger' },
  cursed: { label: 'Cursed', icon: Bug, tone: 'warning' },
  void: { label: 'Of the void', icon: Orbit, tone: 'verdigris' },
}

export const LUXURY_METALS: readonly MaterialKind[] = [
  'gold',
  'silver',
  'gems',
  'ivory',
  'amber',
  'glass',
  'crystal',
]

export const SLOT_EFFECT: Record<
  string,
  Named & { phrase: (value: number) => string }
> = {
  worth_pct: {
    label: 'Worth',
    icon: Coins,
    tone: 'gold',
    phrase: (value) => `Worth ${value}% of the plain make`,
  },
  price_pct: {
    label: 'Market price',
    icon: Store,
    tone: 'gold',
    phrase: (value) => `Sells at ${value}% of the base price`,
  },
  battle_wear: {
    label: 'Battle wear',
    icon: Swords,
    tone: 'warning',
    phrase: (value) => `Loses ${value} condition in each battle`,
  },
  wet_wear: {
    label: 'Rust and rot',
    icon: Waves,
    tone: 'warning',
    phrase: (value) => `Loses ${value} condition each wet epoch`,
  },
  damage: {
    label: 'Damage',
    icon: Slice,
    tone: 'danger',
    phrase: (value) => `Strikes for ${value} damage`,
  },
  protection: {
    label: 'Protection',
    icon: Shield,
    tone: 'info',
    phrase: (value) => `Wards off ${value} damage`,
  },
  holy_edge_pct: {
    label: 'Holy edge',
    icon: Sun,
    tone: 'verdigris',
    phrase: (value) =>
      `Holy edge vs the undead, the cursed and the void ${value}%`,
  },
  risk_kept_pct: {
    label: 'Storm and raider guard',
    icon: Anchor,
    tone: 'info',
    phrase: (value) =>
      `Turns aside ${Math.max(0, 100 - value)}% of storm and raider risk`,
  },
  armour_wear: {
    label: 'Hull wear',
    icon: ShieldAlert,
    tone: 'warning',
    phrase: (value) => `Loses ${value} armour on a hard voyage`,
  },
  wind_kept_pct: {
    label: 'Wind guard',
    icon: Wind,
    tone: 'verdigris',
    phrase: (value) =>
      `Shrugs off ${Math.max(0, 100 - value)}% of the wind's damage`,
  },
  stage_saved: {
    label: 'Light sails',
    icon: Bird,
    tone: 'success',
    phrase: (value) =>
      value > 0
        ? 'Light enough to save a stage on every voyage'
        : 'Too heavy to save a stage on a voyage',
  },
}

export function slotEffect(key: string, value: number) {
  const spec = SLOT_EFFECT[key]
  if (spec) return { ...spec, text: spec.phrase(value) }
  return {
    label: key.replaceAll('_', ' '),
    icon: Package,
    tone: 'muted' as KpiTone,
    text: `${key.replaceAll('_', ' ')} ${value}`,
  }
}

export function premiumTone(pct: number): KpiTone {
  if (pct > 100) return 'gold'
  if (pct < 100) return 'muted'
  return 'info'
}
