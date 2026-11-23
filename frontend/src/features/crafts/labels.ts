import {
  Anchor,
  Ban,
  Bird,
  BookOpen,
  Box,
  Brush,
  Building2,
  Clock,
  Clover,
  Cog,
  Coins,
  Compass,
  CookingPot,
  Cpu,
  Crosshair,
  Crown,
  Droplet,
  Droplets,
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
  Heart,
  HeartPulse,
  Hourglass,
  Layers,
  Leaf,
  Link,
  Microscope,
  Music,
  Orbit,
  PawPrint,
  PenTool,
  Pill,
  Scale,
  ScanEye,
  Scroll,
  Search,
  Shell,
  Ship,
  Sparkles,
  Sprout,
  Sun,
  Swords,
  Tag,
  Target,
  Telescope,
  TriangleAlert,
  Trophy,
  type LucideIcon,
  Waves,
  Wrench,
  Zap,
  Sparkle,
  Package,
  TestTube,
  Wheat,
  Sailboat,
  Rabbit,
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
  game_hunt: { label: 'Hunt of great game', icon: Target, tone: 'warning' },
  shore_gathering: { label: 'Shore gathering', icon: Shell, tone: 'success' },
  diving: { label: 'Diving the beds', icon: Gem, tone: 'gold' },
  fish_ponds: { label: 'Fish ponds', icon: Droplets, tone: 'info' },
}

export const GEAR: Record<Schema['Gear'], Named> = {
  lines: { label: 'Lines', icon: Link, tone: 'info' },
  nets: { label: 'Nets', icon: Grid3x3, tone: 'info' },
  weirs: { label: 'Weirs', icon: Layers, tone: 'verdigris' },
  traps: { label: 'Traps', icon: Box, tone: 'warning' },
  snares: { label: 'Snares', icon: Link, tone: 'warning' },
  harpoons: { label: 'Harpoons', icon: Anchor, tone: 'danger' },
  missiles: { label: 'Bows and spears', icon: Crosshair, tone: 'warning' },
  trawls: { label: 'Trawls', icon: Ship, tone: 'danger' },
  poison: { label: 'Poison', icon: FlaskConical, tone: 'danger' },
  hunting_animals: {
    label: 'Hunting animals',
    icon: PawPrint,
    tone: 'verdigris',
  },
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
  ink: { label: 'Ink', icon: PenTool, tone: 'muted' },
  glaze: { label: 'Glaze', icon: Sparkle, tone: 'gold' },
  preservative: { label: 'Preservative', icon: Package, tone: 'success' },
  acid: { label: 'Acid', icon: TestTube, tone: 'warning' },
}

export const COVERS: Record<Schema['InsuranceCover'], Named> = {
  cargo: { label: 'Cargo', icon: Ship, tone: 'info' },
  house: { label: 'House', icon: Building2, tone: 'gold' },
  life: { label: 'Life', icon: HeartPulse, tone: 'danger' },
  crop: { label: 'Crop', icon: Wheat, tone: 'gold' },
  vessel: { label: 'Vessel', icon: Sailboat, tone: 'info' },
  livestock: { label: 'Livestock', icon: Rabbit, tone: 'verdigris' },
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
  recipe: { label: 'Recipe', icon: CookingPot, tone: 'warning' },
  technique: { label: 'Technique', icon: Cog, tone: 'info' },
}

export const ACQUIRED: Record<Schema['RightAcquired'], Named> = {
  created: { label: 'Made', icon: PenTool, tone: 'success' },
  inherited: { label: 'Inherited', icon: Crown, tone: 'gold' },
  bought: { label: 'Bought', icon: Coins, tone: 'info' },
  licensed: { label: 'Licensed', icon: Handshake, tone: 'verdigris' },
  stolen: { label: 'Stolen', icon: Swords, tone: 'danger' },
  granted: { label: 'Granted', icon: Scroll, tone: 'gold' },
  won: { label: 'Won in a contest', icon: Trophy, tone: 'success' },
  wed: { label: 'Passed with a union', icon: Heart, tone: 'verdigris' },
}

export const AIDS: Record<Schema['AssistiveAid'], Named> = {
  spectacles: { label: 'Spectacles', icon: Eye, tone: 'info' },
  magnifier: { label: 'Magnifier', icon: Search, tone: 'verdigris' },
  telescope: { label: 'Telescope', icon: Telescope, tone: 'gold' },
  hearing_horn: { label: 'Hearing horn', icon: Ear, tone: 'warning' },
  cane: { label: 'Cane', icon: Footprints, tone: 'muted' },
  microscope: { label: 'Microscope', icon: Microscope, tone: 'info' },
}

export const CLOCKS: Record<Schema['ClockKind'], Named> = {
  sundial: { label: 'Sundial', icon: Sun, tone: 'gold' },
  water_clock: { label: 'Water clock', icon: Droplet, tone: 'info' },
  sand_glass: { label: 'Sand glass', icon: Hourglass, tone: 'warning' },
  candle_clock: { label: 'Candle clock', icon: Flame, tone: 'warning' },
  mechanical: { label: 'Mechanical clock', icon: Clock, tone: 'verdigris' },
  astronomical: { label: 'Astronomical clock', icon: Orbit, tone: 'gold' },
  chronometer: { label: 'Chronometer', icon: Compass, tone: 'info' },
  electronic: { label: 'Electronic clock', icon: Cpu, tone: 'verdigris' },
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
