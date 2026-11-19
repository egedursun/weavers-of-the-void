import {
  Anchor,
  Ban,
  Clover,
  TriangleAlert,
  Bird,
  BookOpen,
  Box,
  Brush,
  Building2,
  Clock,
  Coins,
  Crown,
  Droplet,
  Ear,
  Eye,
  Fish,
  Flame,
  FlaskConical,
  Footprints,
  Gem,
  Grid3x3,
  Hammer,
  Handshake,
  Hash,
  HeartPulse,
  Hourglass,
  Layers,
  Leaf,
  Link,
  type LucideIcon,
  Music,
  Orbit,
  PenTool,
  Pill,
  Scale,
  ScanEye,
  Scroll,
  Search,
  Ship,
  Sparkles,
  Sprout,
  Sun,
  Swords,
  Tag,
  Telescope,
  Waves,
  Wrench,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const CRAFTS_ICON: LucideIcon = Wrench

export const TAB_ICONS = {
  trades: Fish,
  money: Coins,
  learning: Telescope,
  arcane: Sparkles,
} as const

export const GROUNDS: Record<Schema['CatchGround'], Named> = {
  fishery: { label: 'Fishery', icon: Fish, tone: 'info' },
  trapping: { label: 'Trapping', icon: Box, tone: 'warning' },
  fowling: { label: 'Fowling', icon: Bird, tone: 'success' },
  marine_hunt: {
    label: 'Hunt of great sea beasts',
    icon: Waves,
    tone: 'danger',
  },
}

export const GEAR: Record<Schema['Gear'], Named> = {
  lines: { label: 'Lines', icon: Link, tone: 'info' },
  nets: { label: 'Nets', icon: Grid3x3, tone: 'info' },
  weirs: { label: 'Weirs', icon: Layers, tone: 'verdigris' },
  traps: { label: 'Traps', icon: Box, tone: 'warning' },
  snares: { label: 'Snares', icon: Link, tone: 'warning' },
  harpoons: { label: 'Harpoons', icon: Anchor, tone: 'danger' },
}

export const CATCH_RIGHTS: Record<Schema['CatchRight'], Named> = {
  commons: { label: 'Common to all', icon: Handshake, tone: 'success' },
  owned: { label: 'Owned', icon: Crown, tone: 'gold' },
}

export const PRODUCTS: Record<Schema['ChemicalProduct'], Named> = {
  dye: { label: 'Dye', icon: Brush, tone: 'info' },
  soap: { label: 'Soap', icon: Droplet, tone: 'success' },
  mordant: { label: 'Mordant', icon: FlaskConical, tone: 'verdigris' },
  tanning: { label: 'Tanning', icon: Leaf, tone: 'warning' },
  fertiliser: { label: 'Fertiliser', icon: Sprout, tone: 'success' },
  medicine: { label: 'Medicine', icon: Pill, tone: 'info' },
  incendiary: { label: 'Incendiary', icon: Flame, tone: 'danger' },
  explosive: { label: 'Explosive', icon: Zap, tone: 'danger' },
}

export const COVERS: Record<Schema['InsuranceCover'], Named> = {
  cargo: { label: 'Cargo', icon: Ship, tone: 'info' },
  house: { label: 'House', icon: Building2, tone: 'gold' },
  life: { label: 'Life', icon: HeartPulse, tone: 'danger' },
}

export const RIGHT_KINDS: Record<Schema['RightKind'], Named> = {
  song: { label: 'Song', icon: Music, tone: 'info' },
  dance: { label: 'Dance', icon: Footprints, tone: 'verdigris' },
  story: { label: 'Story', icon: BookOpen, tone: 'gold' },
  rite: { label: 'Rite', icon: Sparkles, tone: 'verdigris' },
  design: { label: 'Design', icon: PenTool, tone: 'info' },
  name: { label: 'Name', icon: Tag, tone: 'muted' },
  title: { label: 'Title', icon: Crown, tone: 'gold' },
  trademark: { label: 'Mark of a maker', icon: Hammer, tone: 'warning' },
  market_privilege: { label: 'Market privilege', icon: Scale, tone: 'success' },
}

export const ACQUIRED: Record<Schema['RightAcquired'], Named> = {
  created: { label: 'Made', icon: PenTool, tone: 'success' },
  inherited: { label: 'Inherited', icon: Crown, tone: 'gold' },
  bought: { label: 'Bought', icon: Coins, tone: 'info' },
  licensed: { label: 'Licensed', icon: Handshake, tone: 'verdigris' },
  stolen: { label: 'Stolen', icon: Swords, tone: 'danger' },
  granted: { label: 'Granted', icon: Scroll, tone: 'gold' },
}

export const AIDS: Record<Schema['AssistiveAid'], Named> = {
  spectacles: { label: 'Spectacles', icon: Eye, tone: 'info' },
  magnifier: { label: 'Magnifier', icon: Search, tone: 'verdigris' },
  telescope: { label: 'Telescope', icon: Telescope, tone: 'gold' },
  hearing_horn: { label: 'Hearing horn', icon: Ear, tone: 'warning' },
  cane: { label: 'Cane', icon: Footprints, tone: 'muted' },
}

export const CLOCKS: Record<Schema['ClockKind'], Named> = {
  sundial: { label: 'Sundial', icon: Sun, tone: 'gold' },
  water_clock: { label: 'Water clock', icon: Droplet, tone: 'info' },
  sand_glass: { label: 'Sand glass', icon: Hourglass, tone: 'warning' },
  candle_clock: { label: 'Candle clock', icon: Flame, tone: 'warning' },
  mechanical: { label: 'Mechanical clock', icon: Clock, tone: 'verdigris' },
  astronomical: { label: 'Astronomical clock', icon: Orbit, tone: 'gold' },
}

export const NOTATIONS: Record<Schema['Notation'], Named> = {
  additive: { label: 'Added up', icon: Hash, tone: 'muted' },
  positional: { label: 'By place', icon: Grid3x3, tone: 'gold' },
}

export const READINGS: Record<Schema['NumberReading'], Named> = {
  lucky: { label: 'Lucky', icon: Clover, tone: 'gold' },
  unlucky: { label: 'Unlucky', icon: TriangleAlert, tone: 'warning' },
  sacred: { label: 'Sacred', icon: Sparkles, tone: 'info' },
  forbidden: { label: 'Forbidden', icon: Ban, tone: 'danger' },
}

export const MODES: Record<Schema['AffinityMode'], Named> = {
  consumed: { label: 'Consumed', icon: Flame, tone: 'danger' },
  worn: { label: 'Worn', icon: Gem, tone: 'gold' },
  inscribed: { label: 'Inscribed', icon: PenTool, tone: 'info' },
  ground: { label: 'Ground to powder', icon: Hammer, tone: 'warning' },
}

export const TOKENS: Record<Schema['LinkToken'], Named> = {
  hair: { label: 'Hair', icon: Link, tone: 'muted' },
  blood: { label: 'Blood', icon: Droplet, tone: 'danger' },
  name: { label: 'True name', icon: Tag, tone: 'gold' },
  portrait: { label: 'Likeness', icon: ScanEye, tone: 'info' },
  fragment: { label: 'Fragment', icon: Box, tone: 'warning' },
}
