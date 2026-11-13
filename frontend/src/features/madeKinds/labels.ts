import {
  Anchor,
  ArrowDown,
  ArrowUp,
  ArrowLeftRight,
  Axe,
  Ban,
  Bomb,
  Bot,
  BowArrow,
  Building2,
  Car,
  Castle,
  CircleCheck,
  CircleDashed,
  CircleDot,
  CircleOff,
  Cloud,
  Cog,
  Construction,
  CookingPot,
  Cpu,
  Croissant,
  Crosshair,
  Crown,
  Disc3,
  Drill,
  Droplets,
  Egg,
  Fan,
  Fish,
  Flame,
  Footprints,
  Gem,
  Globe,
  Hammer,
  HardHat,
  Heart,
  HeartCrack,
  Layers,
  Leaf,
  Map as MapIcon,
  Milk,
  Mountain,
  Orbit,
  Package,
  PartyPopper,
  PawPrint,
  Pill,
  Plane,
  Radar,
  Rocket,
  Rotate3d,
  Sailboat,
  Scroll,
  Shield,
  ShieldHalf,
  Ship,
  ShipWheel,
  Skull,
  Soup,
  Sparkles,
  Sun,
  Sword,
  Swords,
  Target,
  Tent,
  TowerControl,
  TrainFront,
  Truck,
  Utensils,
  Waves,
  Wheat,
  Wind,
  Wine,
  Wrench,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import {
  type components,
  equipmentFamilyValues,
  structureSectionValues,
  vehicleFrameValues,
  vehicleSectionValues,
} from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']
export type VehicleFamily = Schema['VehicleFamily']
export type VehicleFrame = Schema['VehicleFrame']
export type VehicleSection = Schema['VehicleSection']
export type StructureSection = Schema['StructureSection']
export type SectionState = Schema['SectionState']
export type Criticality = Schema['Criticality']
export type EquipmentFamily = Schema['EquipmentFamily']
export type ArmamentSlot = Schema['ArmamentSlot']

function words(value: string): string {
  return value
    .replaceAll('_', ' ')
    .replace(/^./, (first) => first.toUpperCase())
}

export const VEHICLE_FAMILY: Record<VehicleFamily, Named> = {
  mount: { label: 'Mount', icon: PawPrint, tone: 'gold' },
  cart: { label: 'Cart', icon: Package, tone: 'muted' },
  wagon: { label: 'Wagon', icon: Truck, tone: 'gold' },
  chariot: { label: 'Chariot', icon: Disc3, tone: 'warning' },
  motor: { label: 'Motor vehicle', icon: Car, tone: 'info' },
  tracked: { label: 'Tracked vehicle', icon: Construction, tone: 'danger' },
  walker: { label: 'Walker', icon: Footprints, tone: 'verdigris' },
  rail: { label: 'Rail vehicle', icon: TrainFront, tone: 'info' },
  ram: { label: 'Ram', icon: Axe, tone: 'warning' },
  tower: { label: 'Siege tower', icon: TowerControl, tone: 'warning' },
  thrower: { label: 'Engine of war', icon: Target, tone: 'danger' },
  gun: { label: 'Gun', icon: Bomb, tone: 'danger' },
  boat: { label: 'Boat', icon: Sailboat, tone: 'info' },
  galley: { label: 'Galley', icon: ShipWheel, tone: 'gold' },
  sailing_ship: { label: 'Sailing ship', icon: Ship, tone: 'info' },
  steam_ship: { label: 'Steam ship', icon: Ship, tone: 'warning' },
  submarine: { label: 'Submarine', icon: Waves, tone: 'info' },
  balloon: { label: 'Balloon', icon: Cloud, tone: 'verdigris' },
  airship: { label: 'Airship', icon: Wind, tone: 'verdigris' },
  aircraft: { label: 'Aircraft', icon: Plane, tone: 'info' },
  rotorcraft: { label: 'Rotorcraft', icon: Fan, tone: 'info' },
  spacecraft: { label: 'Spacecraft', icon: Rocket, tone: 'verdigris' },
  burrower: { label: 'Burrower', icon: Drill, tone: 'muted' },
  construct: { label: 'Construct', icon: Bot, tone: 'verdigris' },
  living: { label: 'Living vehicle', icon: Heart, tone: 'success' },
}

export const VEHICLE_DOMAIN: Record<Schema['VehicleDomain'], Named> = {
  land: { label: 'Land', icon: Mountain, tone: 'gold' },
  water: { label: 'Water', icon: Waves, tone: 'info' },
  underwater: { label: 'Under water', icon: Droplets, tone: 'info' },
  air: { label: 'Air', icon: Wind, tone: 'verdigris' },
  space: { label: 'Space', icon: Orbit, tone: 'verdigris' },
  gas_giant: { label: 'Gas giant', icon: Globe, tone: 'warning' },
  underground: { label: 'Underground', icon: Drill, tone: 'muted' },
  planar: { label: 'Between planes', icon: Sparkles, tone: 'verdigris' },
  amphibious: { label: 'Land and water', icon: Anchor, tone: 'info' },
}

export const PROPULSION: Record<Schema['Propulsion'], Named> = {
  crew: { label: 'Pushed by its crew', icon: HardHat, tone: 'muted' },
  draft_animals: { label: 'Draft animals', icon: PawPrint, tone: 'gold' },
  ridden: { label: 'Ridden', icon: PawPrint, tone: 'gold' },
  oars: { label: 'Oars', icon: ShipWheel, tone: 'muted' },
  sail: { label: 'Sail', icon: Sailboat, tone: 'info' },
  sail_and_oar: { label: 'Sail and oar', icon: Sailboat, tone: 'info' },
  steam: { label: 'Steam', icon: Cloud, tone: 'warning' },
  combustion: { label: 'Combustion', icon: Flame, tone: 'danger' },
  electric: { label: 'Electric', icon: Zap, tone: 'info' },
  reaction: { label: 'Reaction drive', icon: Rocket, tone: 'warning' },
  solar_sail: { label: 'Solar sail', icon: Sun, tone: 'gold' },
  fold_drive: { label: 'Fold drive', icon: Rotate3d, tone: 'verdigris' },
  buoyancy: { label: 'Buoyancy', icon: Cloud, tone: 'verdigris' },
  magic: { label: 'Magic', icon: Sparkles, tone: 'verdigris' },
  divine: { label: 'Divine power', icon: Crown, tone: 'gold' },
  self: { label: 'Moves itself', icon: Heart, tone: 'success' },
  current: { label: 'Current', icon: Waves, tone: 'info' },
  towed: { label: 'Towed', icon: Truck, tone: 'muted' },
}

export const VEHICLE_SIZE: Record<Schema['VehicleSize'], Named> = {
  small: { label: 'Small', icon: CircleDot, tone: 'muted' },
  medium: { label: 'Medium', icon: CircleDot, tone: 'info' },
  large: { label: 'Large', icon: CircleDot, tone: 'gold' },
  huge: { label: 'Huge', icon: CircleDot, tone: 'warning' },
  colossal: { label: 'Colossal', icon: CircleDot, tone: 'danger' },
}

export const FIRE_CONTROL: Record<Schema['FireControl'], Named> = {
  manual: { label: 'By hand', icon: Hammer, tone: 'muted' },
  drilled: { label: 'Drilled crews', icon: Swords, tone: 'gold' },
  sighted: { label: 'Sighted', icon: Crosshair, tone: 'info' },
  directed: { label: 'Directed', icon: Target, tone: 'info' },
  computed: { label: 'Computed', icon: Cpu, tone: 'verdigris' },
  automatic: { label: 'Automatic', icon: Cog, tone: 'verdigris' },
  guided: { label: 'Guided', icon: Radar, tone: 'success' },
}

export const MOUNT: Record<Schema['MountKind'], Named> = {
  bow: { label: 'Bow mount', icon: ArrowUp, tone: 'info' },
  stern: { label: 'Stern mount', icon: ArrowDown, tone: 'info' },
  broadside: { label: 'Broadside', icon: ArrowLeftRight, tone: 'danger' },
  deck: { label: 'Deck mount', icon: Layers, tone: 'gold' },
  turret: { label: 'Turret', icon: Rotate3d, tone: 'danger' },
  spinal: { label: 'Spinal mount', icon: Zap, tone: 'danger' },
  hardpoint: { label: 'Hardpoint', icon: Wrench, tone: 'warning' },
  wing: { label: 'Wing mount', icon: Plane, tone: 'info' },
  crew_station: { label: 'Crew station', icon: HardHat, tone: 'muted' },
  rider: { label: 'Rider', icon: PawPrint, tone: 'gold' },
  ram: { label: 'Ram', icon: Axe, tone: 'warning' },
  bay: { label: 'Bay', icon: Package, tone: 'muted' },
  ward_node: { label: 'Ward node', icon: Sparkles, tone: 'verdigris' },
}

export const ARC: Record<Schema['MountArc'], Named> = {
  forward: { label: 'Forward', icon: ArrowUp, tone: 'info' },
  aft: { label: 'Aft', icon: ArrowDown, tone: 'info' },
  side: { label: 'Sides', icon: ArrowLeftRight, tone: 'info' },
  all_round: { label: 'All round', icon: Rotate3d, tone: 'gold' },
}

export const VEHICLE_STATUS: Record<Schema['VehicleStatus'], Named> = {
  ready: { label: 'Ready', icon: CircleCheck, tone: 'success' },
  moving: { label: 'Moving', icon: Footprints, tone: 'info' },
  engaged: { label: 'Engaged', icon: Swords, tone: 'danger' },
  laid_up: { label: 'Laid up', icon: Anchor, tone: 'muted' },
  building: { label: 'Being built', icon: Construction, tone: 'gold' },
  wrecked: { label: 'Wrecked', icon: Skull, tone: 'danger' },
}

export const CRITICALITY: Record<Criticality, Named> = {
  critical: { label: 'Critical', icon: HeartCrack, tone: 'danger' },
  major: { label: 'Major', icon: ShieldHalf, tone: 'warning' },
  minor: { label: 'Minor', icon: CircleDot, tone: 'muted' },
}

export const HAZARD: Record<Schema['SectionHazard'], Named> = {
  none: { label: 'No hazard', icon: Ban, tone: 'muted' },
  fire: { label: 'Catches fire', icon: Flame, tone: 'danger' },
  explosion: { label: 'Explodes', icon: Bomb, tone: 'danger' },
  flooding: { label: 'Floods', icon: Waves, tone: 'info' },
  breach: { label: 'Breaches', icon: HeartCrack, tone: 'warning' },
  crash: { label: 'Brings it down', icon: ArrowDown, tone: 'danger' },
  panic: { label: 'Panics', icon: PawPrint, tone: 'warning' },
  collapse: { label: 'Collapses', icon: Building2, tone: 'danger' },
}

export const SECTION_STATE: Record<SectionState, Named> = {
  sound: { label: 'Sound', icon: CircleCheck, tone: 'success' },
  damaged: { label: 'Damaged', icon: CircleDashed, tone: 'warning' },
  disabled: { label: 'Disabled', icon: CircleOff, tone: 'danger' },
  destroyed: { label: 'Destroyed', icon: Skull, tone: 'danger' },
}

export const SLOT: Record<ArmamentSlot, Named> = {
  hand_weapon: { label: 'Hand weapon', icon: Sword, tone: 'danger' },
  missile_weapon: { label: 'Missile weapon', icon: BowArrow, tone: 'info' },
  armour: { label: 'Armour', icon: ShieldHalf, tone: 'gold' },
  shield: { label: 'Shield', icon: Shield, tone: 'gold' },
  helmet: { label: 'Helmet', icon: HardHat, tone: 'muted' },
  barding: { label: 'Barding', icon: PawPrint, tone: 'muted' },
  vehicle_weapon: { label: 'Vehicle weapon', icon: Bomb, tone: 'warning' },
}

export const METHOD: Record<Schema['CookingMethod'], Named> = {
  raw: { label: 'Raw', icon: Leaf, tone: 'success' },
  boiled: { label: 'Boiled', icon: CookingPot, tone: 'info' },
  stewed: { label: 'Stewed', icon: Soup, tone: 'gold' },
  steamed: { label: 'Steamed', icon: Cloud, tone: 'info' },
  roasted: { label: 'Roasted', icon: Flame, tone: 'warning' },
  grilled: { label: 'Grilled', icon: Flame, tone: 'danger' },
  baked: { label: 'Baked', icon: Croissant, tone: 'gold' },
  fried: { label: 'Fried', icon: Flame, tone: 'warning' },
  smoked: { label: 'Smoked', icon: Cloud, tone: 'muted' },
  dried: { label: 'Dried', icon: Sun, tone: 'gold' },
  cured: { label: 'Cured', icon: Gem, tone: 'muted' },
  pickled: { label: 'Pickled', icon: Droplets, tone: 'verdigris' },
  fermented: { label: 'Fermented', icon: Wine, tone: 'verdigris' },
  braised: { label: 'Braised', icon: Soup, tone: 'warning' },
  simmered: { label: 'Simmered', icon: CookingPot, tone: 'gold' },
  ground: { label: 'Ground', icon: Wheat, tone: 'gold' },
  pressed: { label: 'Pressed', icon: Layers, tone: 'muted' },
}

export const COURSE: Record<Schema['DishCourse'], Named> = {
  staple: { label: 'Staple', icon: Wheat, tone: 'gold' },
  side: { label: 'Side dish', icon: Utensils, tone: 'muted' },
  festive: { label: 'Feast dish', icon: PartyPopper, tone: 'gold' },
  rite: { label: 'Rite dish', icon: Scroll, tone: 'verdigris' },
  ration: { label: 'Ration', icon: Package, tone: 'info' },
  delicacy: { label: 'Delicacy', icon: Gem, tone: 'warning' },
  remedy: { label: 'Remedy', icon: Pill, tone: 'success' },
  drink: { label: 'Drink', icon: Milk, tone: 'info' },
}

export const FORM: Record<Schema['BuildingForm'], Named> = {
  hall: { label: 'Hall', icon: Building2, tone: 'gold' },
  longhouse: { label: 'Longhouse', icon: Building2, tone: 'muted' },
  tower: { label: 'Tower', icon: TowerControl, tone: 'info' },
  keep: { label: 'Keep', icon: Castle, tone: 'danger' },
  dome: { label: 'Dome', icon: CircleDot, tone: 'verdigris' },
  spire: { label: 'Spire', icon: ArrowUp, tone: 'verdigris' },
  stepped: { label: 'Stepped', icon: Layers, tone: 'gold' },
  pyramid: { label: 'Pyramid', icon: Mountain, tone: 'gold' },
  courtyard: { label: 'Courtyard', icon: MapIcon, tone: 'success' },
  ring: { label: 'Ring', icon: Orbit, tone: 'info' },
  tent: { label: 'Tent', icon: Tent, tone: 'muted' },
  mound: { label: 'Mound', icon: Mountain, tone: 'muted' },
  arcade: { label: 'Arcade', icon: Layers, tone: 'info' },
  terrace: { label: 'Terrace', icon: Layers, tone: 'success' },
  platform: { label: 'Platform', icon: Layers, tone: 'muted' },
  bridge_form: { label: 'Bridge', icon: ArrowLeftRight, tone: 'info' },
  wall_line: { label: 'Wall line', icon: Shield, tone: 'warning' },
  tunnel_form: { label: 'Tunnel', icon: Drill, tone: 'muted' },
  orbital: { label: 'Orbital', icon: Orbit, tone: 'verdigris' },
}

export const ROLE: Record<Schema['SectionRole'], Named> = {
  support: { label: 'Bears the weight', icon: Layers, tone: 'muted' },
  defence: { label: 'Defends', icon: Shield, tone: 'danger' },
  entry: { label: 'Lets folk in', icon: ArrowDown, tone: 'info' },
  shelter: { label: 'Shelters', icon: Building2, tone: 'gold' },
  storage: { label: 'Stores', icon: Package, tone: 'gold' },
  worship: { label: 'Holds worship', icon: Sparkles, tone: 'verdigris' },
  knowledge: { label: 'Keeps knowledge', icon: Scroll, tone: 'info' },
  production: { label: 'Makes things', icon: Hammer, tone: 'warning' },
  passage: { label: 'Carries passage', icon: ArrowLeftRight, tone: 'info' },
  water: { label: 'Moves water', icon: Droplets, tone: 'info' },
  display: { label: 'Shows and seats', icon: PartyPopper, tone: 'gold' },
  power: { label: 'Gives power', icon: Zap, tone: 'warning' },
  command: { label: 'Commands', icon: Crown, tone: 'gold' },
  motion: { label: 'Moves it', icon: Rocket, tone: 'verdigris' },
}

export const FOOD_ICON: Partial<Record<Schema['CommodityKind'], LucideIcon>> = {
  grain: Wheat,
  tubers: Leaf,
  fruit: Leaf,
  meat: Utensils,
  fish: Fish,
  milk: Milk,
  cheese: Milk,
  eggs: Egg,
  herbs: Leaf,
  brew_base: Wine,
  bread: Croissant,
}

export const DISH_FOODS = Object.keys(FOOD_ICON) as Schema['CommodityKind'][]

export const FRAME_OPTIONS: readonly VehicleFrame[] = vehicleFrameValues
export const VEHICLE_SECTIONS: readonly VehicleSection[] = vehicleSectionValues
export const STRUCTURE_SECTIONS: readonly StructureSection[] =
  structureSectionValues
export const EQUIPMENT_FAMILIES: readonly EquipmentFamily[] =
  equipmentFamilyValues

export function wordTable(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}

export function namedTable(
  table: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(table).map(([key, value]) => [key, value.label])
  )
}

export function sectionLabel(section: string): string {
  return words(section)
}

export function familyLabel(family: string): string {
  return words(family)
}

export const STATE_FILL: Record<SectionState, string> = {
  sound: 'fill-success/25 stroke-success',
  damaged: 'fill-warning/30 stroke-warning',
  disabled: 'fill-destructive/30 stroke-destructive',
  destroyed: 'fill-muted stroke-destructive',
}

export function frameTable(
  frames: readonly {
    frame: VehicleFrame
    label: string
    family: VehicleFamily
  }[]
): Record<string, Named> {
  const known = new Map(frames.map((spec) => [spec.frame, spec]))
  return Object.fromEntries(
    vehicleFrameValues.map((frame) => {
      const spec = known.get(frame)
      const family = VEHICLE_FAMILY[spec?.family ?? 'cart']
      return [
        frame,
        {
          label: spec?.label ?? words(frame),
          icon: family.icon,
          tone: family.tone,
        },
      ]
    })
  )
}
