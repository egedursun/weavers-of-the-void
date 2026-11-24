import {
  Anchor,
  Apple,
  Axe,
  Beef,
  Biohazard,
  Bird,
  BookOpen,
  Bug,
  Building2,
  Castle,
  CircleDashed,
  Coins,
  DoorOpen,
  Drill,
  Droplets,
  Eye,
  Factory,
  Fence,
  Fish,
  Flame,
  FlaskConical,
  Footprints,
  Gem,
  Grape,
  Hammer,
  HandHeart,
  HeartPulse,
  Home,
  Landmark,
  Layers,
  Leaf,
  Map as MapIcon,
  Mountain,
  MountainSnow,
  MoveRight,
  Orbit,
  Package,
  Palmtree,
  Pickaxe,
  RadioTower,
  RefreshCw,
  Route,
  Ruler,
  Scale,
  Shell,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sparkles,
  Sprout,
  Store,
  Sun,
  Syringe,
  Telescope,
  Tent,
  Ticket,
  TreeDeciduous,
  TreePine,
  Trees,
  Truck,
  type LucideIcon,
  Users,
  Waves,
  Wheat,
  Wind,
  Bean,
  Pyramid,
  Ship,
  Activity,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const AGRARIAN_ICON: LucideIcon = Wheat

export const RINGS: Record<Schema['LandUseRing'], Named> = {
  gardens: { label: 'Gardens and dairy', icon: Sprout, tone: 'success' },
  forestry: { label: 'Fuel wood', icon: TreePine, tone: 'verdigris' },
  grain: { label: 'Grain', icon: Wheat, tone: 'gold' },
  ranching: { label: 'Herds', icon: Beef, tone: 'warning' },
  wilds: { label: 'Beyond the markets', icon: Mountain, tone: 'muted' },
  industry: { label: 'Works and mines', icon: Factory, tone: 'danger' },
  fallow: { label: 'Fallow', icon: Leaf, tone: 'muted' },
}

export const RANKS: Record<Schema['CentralityRank'], Named> = {
  daily: { label: 'Daily needs', icon: Tent, tone: 'muted' },
  weekly: { label: 'Weekly market', icon: Store, tone: 'info' },
  rare: { label: 'Rare goods', icon: Gem, tone: 'gold' },
  seasonal: { label: 'Fair town', icon: Leaf, tone: 'verdigris' },
  metropolitan: { label: 'Metropolis', icon: Landmark, tone: 'gold' },
  regional: { label: 'Regional market', icon: Coins, tone: 'verdigris' },
}

export const NUTRIENTS: Record<Schema['NutrientKind'], Named> = {
  fixed: { label: 'Fixed element', icon: Leaf, tone: 'success' },
  mineral: { label: 'Minerals', icon: Mountain, tone: 'info' },
  organic: { label: 'Organic matter', icon: Sprout, tone: 'verdigris' },
  salinity: { label: 'Salt', icon: Droplets, tone: 'danger' },
  seed_bank: { label: 'Seeds in the soil', icon: Bean, tone: 'success' },
  soil_life: { label: 'Life of the soil', icon: Bug, tone: 'verdigris' },
}

export const PERENNIALS: Record<Schema['PerennialKind'], Named> = {
  orchard: { label: 'Orchard', icon: Apple, tone: 'success' },
  vineyard: { label: 'Vineyard', icon: Grape, tone: 'verdigris' },
  grove: { label: 'Grove', icon: TreeDeciduous, tone: 'gold' },
  timber: { label: 'Timber plantation', icon: Trees, tone: 'info' },
  plantation: { label: 'Plantation', icon: Sprout, tone: 'success' },
  forest_garden: { label: 'Forest garden', icon: Trees, tone: 'success' },
  coppice: { label: 'Coppice', icon: Axe, tone: 'warning' },
  hedgerow: { label: 'Hedgerow', icon: Fence, tone: 'verdigris' },
  palm_stand: { label: 'Palm stand', icon: Palmtree, tone: 'gold' },
}

export const COMMONS_KINDS: Record<Schema['CommonsKind'], Named> = {
  pasture: { label: 'Pasture', icon: Fence, tone: 'success' },
  woods: { label: 'Woods', icon: Trees, tone: 'verdigris' },
  fishery: { label: 'Fishery', icon: Fish, tone: 'info' },
  water: { label: 'Water', icon: Droplets, tone: 'success' },
  hunting_ground: {
    label: 'Hunting ground',
    icon: Footprints,
    tone: 'success',
  },
  quarry: { label: 'Quarry', icon: Pickaxe, tone: 'success' },
  spectrum: { label: 'Spectrum', icon: RadioTower, tone: 'success' },
  orbits: { label: 'Orbits', icon: Orbit, tone: 'success' },
  source_ground: { label: 'Source ground', icon: Sparkles, tone: 'success' },
  turbary: { label: 'Peat cutting', icon: Layers, tone: 'muted' },
  foraging_ground: { label: 'Foraging ground', icon: Leaf, tone: 'success' },
  shore: { label: 'Shore', icon: Shell, tone: 'info' },
}

export const COMMONS_RULES: Record<Schema['CommonsRule'], Named> = {
  open: { label: 'Open to all', icon: Wind, tone: 'warning' },
  customary: { label: 'By custom', icon: Users, tone: 'muted' },
  council: { label: 'Ruled by a council', icon: Shield, tone: 'success' },
  enclosed: { label: 'Enclosed', icon: Fence, tone: 'danger' },
  state: { label: 'Held by officials', icon: Scale, tone: 'warning' },
  licensed: { label: 'Sold by permit', icon: Ticket, tone: 'info' },
  rotational: { label: 'Taken in turns', icon: RefreshCw, tone: 'success' },
}

export const WORKS: Record<Schema['PreparednessKind'], Named> = {
  levee: { label: 'Levees', icon: Waves, tone: 'info' },
  firebreak: { label: 'Firebreaks', icon: Flame, tone: 'danger' },
  stockpile: { label: 'Stockpiles', icon: Package, tone: 'gold' },
  drill: { label: 'Drills', icon: Drill, tone: 'warning' },
  watchtower: { label: 'Watchtowers', icon: Eye, tone: 'verdigris' },
  seawall: { label: 'Seawalls', icon: Anchor, tone: 'info' },
  quarantine_plan: {
    label: 'Quarantine plan',
    icon: ShieldAlert,
    tone: 'info',
  },
  shelters: { label: 'Shelters', icon: Home, tone: 'info' },
  warning_network: { label: 'Warning network', icon: Siren, tone: 'info' },
  evacuation_routes: { label: 'Evacuation routes', icon: Route, tone: 'info' },
  ward: { label: 'Ward', icon: ShieldCheck, tone: 'info' },
  reserves_of_energy: {
    label: 'Reserves of energy',
    icon: Waves,
    tone: 'info',
  },
  immunisation_plan: {
    label: 'Plan of immunisation',
    icon: Syringe,
    tone: 'info',
  },
  quake_building: {
    label: 'Building against quakes',
    icon: Building2,
    tone: 'info',
  },
}

export const AID_KINDS: Record<Schema['AidKind'], Named> = {
  goods: { label: 'Goods', icon: Package, tone: 'gold' },
  healers: { label: 'Healers', icon: HeartPulse, tone: 'success' },
  labour: { label: 'Labour', icon: Hammer, tone: 'info' },
  money: { label: 'Money', icon: Coins, tone: 'gold' },
  credit: { label: 'Credit', icon: Landmark, tone: 'gold' },
  food: { label: 'Food', icon: Wheat, tone: 'gold' },
  shelter: { label: 'Shelter', icon: Home, tone: 'gold' },
  medicine: { label: 'Medicine', icon: Activity, tone: 'gold' },
  soldiers: { label: 'Soldiers', icon: Shield, tone: 'gold' },
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'gold' },
  transport: { label: 'Transport', icon: Truck, tone: 'gold' },
}

export const PLANS: Record<Schema['RebuildPlan'], Named> = {
  planned: { label: 'Planned anew', icon: Ruler, tone: 'success' },
  opportunistic: { label: 'Hasty, as before', icon: Axe, tone: 'warning' },
  relocated: {
    label: 'Rebuilt on a safer site',
    icon: MoveRight,
    tone: 'info',
  },
  abandoned: { label: 'Left to ruin', icon: DoorOpen, tone: 'danger' },
  restored: { label: 'Restored as it was', icon: Hammer, tone: 'success' },
}

export const CAUSES: Record<Schema['RebuildCause'], Named> = {
  fire: { label: 'A fire', icon: Flame, tone: 'danger' },
  flood: { label: 'A flood', icon: Waves, tone: 'info' },
  quake: { label: 'An earthquake', icon: Mountain, tone: 'warning' },
  storm: { label: 'A storm', icon: Wind, tone: 'verdigris' },
  sack: { label: 'A sack', icon: Castle, tone: 'danger' },
  eruption: { label: 'An eruption', icon: MountainSnow, tone: 'danger' },
  sea_wave: { label: 'A sea wave', icon: Ship, tone: 'warning' },
  landslide: { label: 'A landslide', icon: Pyramid, tone: 'danger' },
  plague: { label: 'A plague', icon: Biohazard, tone: 'danger' },
  sinkhole: { label: 'A sinkhole', icon: CircleDashed, tone: 'danger' },
}

export const USES: Record<Schema['KeystoneUse'], Named> = {
  navigation: { label: 'Navigation', icon: MapIcon, tone: 'info' },
  longevity: { label: 'Longevity', icon: HeartPulse, tone: 'success' },
  prescience: { label: 'Prescience', icon: Telescope, tone: 'verdigris' },
  rite: { label: 'Rites', icon: Sun, tone: 'gold' },
}

export const TAB_ICONS = {
  land: MapIcon,
  holdings: Bird,
  readiness: HandHeart,
  staples: FlaskConical,
} as const
