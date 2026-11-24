import {
  type LucideIcon,
  Amphora,
  Anchor,
  Archive,
  ArrowUpFromLine,
  Box,
  BrickWall,
  Clock,
  Cog,
  Compass,
  Construction,
  Cpu,
  Cylinder,
  Droplet,
  Droplets,
  Fan,
  Feather,
  FileText,
  Flame,
  Grid3x3,
  Hammer,
  HardDrive,
  KeyRound,
  Layers,
  Leaf,
  LifeBuoy,
  Lock,
  Map,
  Milk,
  Mountain,
  Package,
  RefreshCw,
  Ribbon,
  Rows3,
  Ruler,
  Satellite,
  Scroll,
  ScrollText,
  Shell,
  Shirt,
  ShoppingBag,
  ShoppingBasket,
  Sparkles,
  Sprout,
  Stamp,
  Star,
  Tablet,
  Telescope,
  Waves,
  Wind,
  Wine,
  Zap,
  IvBag,
  Shield,
  Ship,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const MEANS_ICON: LucideIcon = Hammer

export const TAB_ICONS = {
  writing: ScrollText,
  vaults: Lock,
  water: Droplets,
  pilots: Compass,
  containers: Package,
  building: BrickWall,
} as const

export const MEDIA: Record<Schema['WritingMedium'], Named> = {
  clay_tablet: { label: 'Clay tablet', icon: Tablet, tone: 'gold' },
  wax_tablet: { label: 'Wax tablet', icon: Layers, tone: 'warning' },
  bark: { label: 'Bark', icon: Leaf, tone: 'success' },
  palm_leaf: { label: 'Palm leaf', icon: Feather, tone: 'verdigris' },
  papyrus: { label: 'Papyrus', icon: Scroll, tone: 'gold' },
  parchment: { label: 'Parchment', icon: FileText, tone: 'muted' },
  paper: { label: 'Paper', icon: ScrollText, tone: 'info' },
  metal_plate: { label: 'Metal plate', icon: Stamp, tone: 'info' },
  stone: { label: 'Stone', icon: Mountain, tone: 'muted' },
  knotted_cord: { label: 'Knotted cord', icon: Archive, tone: 'verdigris' },
  calcified_tissue: { label: 'Bone and shell', icon: Shell, tone: 'muted' },
  silk: { label: 'Silk', icon: Ribbon, tone: 'gold' },
  wood_slips: { label: 'Slips of wood or cane', icon: Rows3, tone: 'success' },
  electronic: { label: 'Electronic record', icon: HardDrive, tone: 'info' },
  cloth: { label: 'Cloth', icon: Shirt, tone: 'muted' },
  potsherd: { label: 'Potsherd', icon: Amphora, tone: 'muted' },
}

export const LOCKS: Record<Schema['LockKind'], Named> = {
  bar: { label: 'Bar and bolt', icon: Lock, tone: 'muted' },
  warded: { label: 'Warded lock', icon: Shield, tone: 'info' },
  tumbler: { label: 'Tumbler lock', icon: KeyRound, tone: 'gold' },
  combination: { label: 'Combination lock', icon: Cog, tone: 'success' },
  warded_seal: { label: 'Warded lock with seal', icon: Stamp, tone: 'warning' },
  worked: {
    label: 'Lock held by a working',
    icon: Sparkles,
    tone: 'verdigris',
  },
  electronic: { label: 'Electronic lock', icon: Cpu, tone: 'info' },
  living: { label: 'Living lock', icon: Sprout, tone: 'muted' },
}

export const LIFTS: Record<Schema['WaterLift'], Named> = {
  shaduf: { label: 'Shaduf', icon: ArrowUpFromLine, tone: 'muted' },
  noria: { label: 'Noria', icon: Fan, tone: 'info' },
  screw: { label: 'Water screw', icon: Construction, tone: 'gold' },
  chain_pump: { label: 'Chain pump', icon: Cog, tone: 'warning' },
  steam_pump: { label: 'Steam pump', icon: Waves, tone: 'danger' },
  wind_pump: { label: 'Wind pump', icon: Wind, tone: 'info' },
  electric_pump: { label: 'Electric pump', icon: Zap, tone: 'gold' },
  animal_wheel: { label: 'Animal wheel', icon: RefreshCw, tone: 'muted' },
}

export const AIDS: Record<Schema['NavigationAid'], Named> = {
  compass: { label: 'Compass', icon: Compass, tone: 'info' },
  astrolabe: { label: 'Astrolabe', icon: Telescope, tone: 'gold' },
  log_line: { label: 'Log-line', icon: Ruler, tone: 'muted' },
  charts: { label: 'Charts', icon: Map, tone: 'verdigris' },
  sounding_line: { label: 'Sounding line', icon: Anchor, tone: 'info' },
  wayfinding: { label: 'Wayfinding lore', icon: Star, tone: 'gold' },
  beacons: { label: 'Beacons on the shore', icon: Flame, tone: 'warning' },
  positioning: {
    label: 'Positioning by network',
    icon: Satellite,
    tone: 'verdigris',
  },
  buoys: { label: 'Buoys', icon: LifeBuoy, tone: 'info' },
  pilots: { label: 'Pilots', icon: Ship, tone: 'info' },
}

export const CONTAINERS: Record<Schema['ContainerKind'], Named> = {
  amphora: { label: 'Amphora', icon: Amphora, tone: 'gold' },
  barrel: { label: 'Barrel', icon: Milk, tone: 'warning' },
  sack: { label: 'Sack', icon: ShoppingBag, tone: 'muted' },
  crate: { label: 'Crate', icon: Box, tone: 'info' },
  jar: { label: 'Jar', icon: Wine, tone: 'verdigris' },
  chest: { label: 'Chest', icon: Package, tone: 'success' },
  bale: { label: 'Bale', icon: Layers, tone: 'muted' },
  basket: { label: 'Basket', icon: ShoppingBasket, tone: 'gold' },
  skin: { label: 'Skin', icon: Droplet, tone: 'warning' },
  tank: { label: 'Tank', icon: Cylinder, tone: 'info' },
  cage: { label: 'Cage', icon: Grid3x3, tone: 'muted' },
  net_bag: { label: 'Net bag', icon: IvBag, tone: 'muted' },
}

export const PORT_ICON: LucideIcon = Anchor
export const AGE_ICON: LucideIcon = Clock
