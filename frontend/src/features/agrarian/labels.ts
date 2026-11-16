import {
  Sparkles,
  Siren,
  ShieldCheck,
  ShieldAlert,
  Route,
  RadioTower,
  Pickaxe,
  Orbit,
  Landmark,
  Home,
  Footprints,
  Coins,
  BookOpen,
  Anchor,
  Apple,
  Axe,
  Beef,
  Bird,
  Castle,
  Drill,
  Droplets,
  Eye,
  Fence,
  Fish,
  Flame,
  FlaskConical,
  Gem,
  Grape,
  Hammer,
  HandHeart,
  HeartPulse,
  Leaf,
  type LucideIcon,
  Map as MapIcon,
  Mountain,
  Package,
  Ruler,
  Shield,
  Sprout,
  Store,
  Sun,
  Telescope,
  Tent,
  TreeDeciduous,
  TreePine,
  Trees,
  Users,
  Waves,
  Wheat,
  Wind,
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
}

export const RANKS: Record<Schema['CentralityRank'], Named> = {
  daily: { label: 'Daily needs', icon: Tent, tone: 'muted' },
  weekly: { label: 'Weekly market', icon: Store, tone: 'info' },
  rare: { label: 'Rare goods', icon: Gem, tone: 'gold' },
}

export const NUTRIENTS: Record<Schema['NutrientKind'], Named> = {
  fixed: { label: 'Fixed element', icon: Leaf, tone: 'success' },
  mineral: { label: 'Minerals', icon: Mountain, tone: 'info' },
  organic: { label: 'Organic matter', icon: Sprout, tone: 'verdigris' },
  salinity: { label: 'Salt', icon: Droplets, tone: 'danger' },
}

export const PERENNIALS: Record<Schema['PerennialKind'], Named> = {
  orchard: { label: 'Orchard', icon: Apple, tone: 'success' },
  vineyard: { label: 'Vineyard', icon: Grape, tone: 'verdigris' },
  grove: { label: 'Grove', icon: TreeDeciduous, tone: 'gold' },
  timber: { label: 'Timber plantation', icon: Trees, tone: 'info' },
  plantation: { label: 'Plantation', icon: Sprout, tone: 'success' },
  forest_garden: { label: 'Forest garden', icon: Trees, tone: 'success' },
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
}

export const COMMONS_RULES: Record<Schema['CommonsRule'], Named> = {
  open: { label: 'Open to all', icon: Wind, tone: 'warning' },
  customary: { label: 'By custom', icon: Users, tone: 'muted' },
  council: { label: 'Ruled by a council', icon: Shield, tone: 'success' },
  enclosed: { label: 'Enclosed', icon: Fence, tone: 'danger' },
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
}

export const AID_KINDS: Record<Schema['AidKind'], Named> = {
  goods: { label: 'Goods', icon: Package, tone: 'gold' },
  healers: { label: 'Healers', icon: HeartPulse, tone: 'success' },
  labour: { label: 'Labour', icon: Hammer, tone: 'info' },
  money: { label: 'Money', icon: Coins, tone: 'gold' },
  credit: { label: 'Credit', icon: Landmark, tone: 'gold' },
  food: { label: 'Food', icon: Wheat, tone: 'gold' },
  shelter: { label: 'Shelter', icon: Home, tone: 'gold' },
  medicine: { label: 'Medicine', icon: HeartPulse, tone: 'gold' },
  soldiers: { label: 'Soldiers', icon: Shield, tone: 'gold' },
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'gold' },
}

export const PLANS: Record<Schema['RebuildPlan'], Named> = {
  planned: { label: 'Planned anew', icon: Ruler, tone: 'success' },
  opportunistic: { label: 'Hasty, as before', icon: Axe, tone: 'warning' },
}

export const CAUSES: Record<Schema['RebuildCause'], Named> = {
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  flood: { label: 'Flood', icon: Waves, tone: 'info' },
  quake: { label: 'Quake', icon: Mountain, tone: 'warning' },
  storm: { label: 'Storm', icon: Wind, tone: 'verdigris' },
  sack: { label: 'Sack', icon: Castle, tone: 'danger' },
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
