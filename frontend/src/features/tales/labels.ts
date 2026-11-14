import {
  Ban,
  BookOpen,
  CircleCheck,
  CircleDot,
  CircleX,
  Crown,
  Droplets,
  Eye,
  Flag,
  Flame,
  GraduationCap,
  HandHeart,
  Heart,
  HeartCrack,
  Hourglass,
  Infinity as InfinityIcon,
  Landmark,
  type LucideIcon,
  MapPin,
  Moon,
  MoveRight,
  Mountain,
  Orbit,
  RefreshCcw,
  Scale,
  Route,
  Scroll,
  ScrollText,
  Shield,
  Shuffle,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Target,
  Telescope,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const TALES_ICON: LucideIcon = BookOpen

export const TAB_ICONS = {
  tales: BookOpen,
  world: Orbit,
  ages: RefreshCcw,
} as const

export const ZONES: Record<Schema['FormationZone'], Named> = {
  inner: { label: 'Inside the snow line', icon: Sun, tone: 'warning' },
  snow_line: { label: 'At the snow line', icon: Snowflake, tone: 'info' },
  outer: { label: 'Beyond the snow line', icon: Moon, tone: 'verdigris' },
}

export const MIGRATIONS: Record<Schema['GiantMigration'], Named> = {
  none: { label: 'The giants stayed', icon: CircleDot, tone: 'muted' },
  inward: {
    label: 'The giants moved inward',
    icon: TrendingDown,
    tone: 'info',
  },
  outward: {
    label: 'The giants moved outward',
    icon: TrendingUp,
    tone: 'gold',
  },
}

export const SEASON_CAUSES: Record<Schema['SeasonCause'], Named> = {
  orbit: { label: 'A chaotic orbit', icon: Orbit, tone: 'info' },
  natural_law: { label: 'A natural law', icon: Scale, tone: 'warning' },
  divine: { label: 'A god', icon: Sparkles, tone: 'gold' },
}

export const SPELLS: Record<Schema['SeasonSpell'], Named> = {
  summer: { label: 'Long summer', icon: Sun, tone: 'gold' },
  winter: { label: 'Long winter', icon: Snowflake, tone: 'info' },
}

export const CYCLES: Record<Schema['AgeCycle'], Named> = {
  linear: { label: 'Runs on to its end', icon: MoveRight, tone: 'muted' },
  cyclic: { label: 'Turns in ages', icon: RefreshCcw, tone: 'gold' },
}

export const TEMPLATES: Record<Schema['ArcTemplate'], Named> = {
  rise_and_fall: {
    label: 'Rise and fall',
    icon: TrendingDown,
    tone: 'warning',
  },
  rags_to_riches: { label: 'Rags to riches', icon: TrendingUp, tone: 'gold' },
  revenge: { label: 'Revenge', icon: Swords, tone: 'danger' },
  redemption: { label: 'Redemption', icon: HandHeart, tone: 'success' },
  quest: { label: 'Quest', icon: Route, tone: 'info' },
  tragedy: { label: 'Tragedy', icon: HeartCrack, tone: 'danger' },
  forbidden_love: { label: 'Forbidden love', icon: Heart, tone: 'warning' },
  rivalry: { label: 'Rivalry', icon: Zap, tone: 'warning' },
  mentor_and_heir: {
    label: 'Mentor and heir',
    icon: GraduationCap,
    tone: 'verdigris',
  },
  exile_and_return: { label: 'Exile and return', icon: MapPin, tone: 'info' },
  corruption: { label: 'Corruption', icon: Skull, tone: 'danger' },
  coming_of_age: { label: 'Coming of age', icon: Sprout, tone: 'success' },
  fall_of_a_house: { label: 'Fall of a house', icon: Landmark, tone: 'muted' },
  founding: { label: 'Founding', icon: Flag, tone: 'gold' },
  apotheosis: { label: 'Apotheosis', icon: Star, tone: 'gold' },
}

export const STAGES: Record<Schema['ArcStage'], Named> = {
  inciting: { label: 'Inciting', icon: Flame, tone: 'warning' },
  rising: { label: 'Rising', icon: TrendingUp, tone: 'info' },
  crisis: { label: 'Crisis', icon: Zap, tone: 'danger' },
  climax: { label: 'Climax', icon: Mountain, tone: 'gold' },
  resolution: { label: 'Resolution', icon: CircleCheck, tone: 'success' },
}

export const OUTCOMES: Record<Schema['ArcOutcome'], Named> = {
  open: { label: 'Under way', icon: Hourglass, tone: 'info' },
  fulfilled: { label: 'Fulfilled', icon: CircleCheck, tone: 'success' },
  failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
  twisted: { label: 'Twisted', icon: Shuffle, tone: 'warning' },
  ironic: { label: 'Ironic', icon: InfinityIcon, tone: 'verdigris' },
}

export const ROLES: Record<Schema['ArcRole'], Named> = {
  rival: { label: 'Rival', icon: Zap, tone: 'warning' },
  mentor: { label: 'Mentor', icon: GraduationCap, tone: 'verdigris' },
  beloved: { label: 'Beloved', icon: Heart, tone: 'gold' },
  betrayer: { label: 'Betrayer', icon: Ban, tone: 'danger' },
  heir: { label: 'Heir', icon: Crown, tone: 'gold' },
  foe: { label: 'Foe', icon: Target, tone: 'danger' },
  ally: { label: 'Ally', icon: Shield, tone: 'success' },
}

export const SETUP_KINDS: Record<Schema['SetupKind'], Named> = {
  prophecy: { label: 'Prophecy', icon: Scroll, tone: 'gold' },
  omen: { label: 'Omen', icon: Eye, tone: 'info' },
  dream: { label: 'Dream', icon: Moon, tone: 'verdigris' },
  foresight: { label: 'Foresight', icon: Telescope, tone: 'info' },
  thread: { label: 'Open story', icon: ScrollText, tone: 'muted' },
}

export const PAYOFFS: Record<Schema['PayoffKind'], Named> = {
  open: { label: 'Waiting', icon: Hourglass, tone: 'info' },
  fulfilled: { label: 'Fulfilled', icon: CircleCheck, tone: 'success' },
  subverted: { label: 'Subverted', icon: Shuffle, tone: 'warning' },
  lapsed: { label: 'Lapsed', icon: CircleX, tone: 'muted' },
}

export const VARIANTS: Record<Schema['ApocalypseVariant'], Named> = {
  ruin: { label: 'Ruin', icon: Mountain, tone: 'warning' },
  world_war: { label: 'A war of worlds', icon: Swords, tone: 'danger' },
  outer_descent: { label: 'A descent from outside', icon: Eye, tone: 'danger' },
  twilight_of_gods: {
    label: 'The twilight of the gods',
    icon: Moon,
    tone: 'muted',
  },
  dimensional_collapse: {
    label: 'The veils gave way',
    icon: Shuffle,
    tone: 'verdigris',
  },
  galactic_death: { label: 'A galaxy died', icon: Orbit, tone: 'danger' },
}

export const WATER_ICON: LucideIcon = Droplets
export const CRATER_ICON: LucideIcon = Target
