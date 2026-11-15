import {
  Amphora,
  Anchor,
  Archive,
  Box,
  BrickWall,
  Clock,
  Compass,
  Construction,
  Droplets,
  FileText,
  Feather,
  Hammer,
  KeyRound,
  Layers,
  Leaf,
  Lock,
  type LucideIcon,
  Map,
  Milk,
  Mountain,
  Package,
  Ruler,
  Scroll,
  ScrollText,
  ShoppingBag,
  Stamp,
  Tablet,
  Telescope,
  Waves,
  Wine,
  Cog,
  Fan,
  ArrowUpFromLine,
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
}

export const LOCKS: Record<Schema['LockKind'], Named> = {
  bar: { label: 'Bar and bolt', icon: Lock, tone: 'muted' },
  warded: { label: 'Warded lock', icon: KeyRound, tone: 'info' },
  tumbler: { label: 'Tumbler lock', icon: KeyRound, tone: 'gold' },
  combination: { label: 'Combination lock', icon: Cog, tone: 'success' },
  warded_seal: { label: 'Warded lock with seal', icon: Stamp, tone: 'warning' },
}

export const LIFTS: Record<Schema['WaterLift'], Named> = {
  shaduf: { label: 'Shaduf', icon: ArrowUpFromLine, tone: 'muted' },
  noria: { label: 'Noria', icon: Fan, tone: 'info' },
  screw: { label: 'Water screw', icon: Construction, tone: 'gold' },
  chain_pump: { label: 'Chain pump', icon: Cog, tone: 'warning' },
  steam_pump: { label: 'Steam pump', icon: Waves, tone: 'danger' },
}

export const AIDS: Record<Schema['NavigationAid'], Named> = {
  compass: { label: 'Compass', icon: Compass, tone: 'info' },
  astrolabe: { label: 'Astrolabe', icon: Telescope, tone: 'gold' },
  log_line: { label: 'Log-line', icon: Ruler, tone: 'muted' },
  charts: { label: 'Charts', icon: Map, tone: 'verdigris' },
}

export const CONTAINERS: Record<Schema['ContainerKind'], Named> = {
  amphora: { label: 'Amphora', icon: Amphora, tone: 'gold' },
  barrel: { label: 'Barrel', icon: Milk, tone: 'warning' },
  sack: { label: 'Sack', icon: ShoppingBag, tone: 'muted' },
  crate: { label: 'Crate', icon: Box, tone: 'info' },
  jar: { label: 'Jar', icon: Wine, tone: 'verdigris' },
  chest: { label: 'Chest', icon: Package, tone: 'success' },
}

export const PORT_ICON: LucideIcon = Anchor
export const AGE_ICON: LucideIcon = Clock
