import {
  ArrowDown,
  ArrowUp,
  Ban,
  Bell,
  BookOpen,
  CircleCheck,
  CircleDot,
  CircleX,
  Crosshair,
  Crown,
  DoorOpen,
  Droplets,
  Eye,
  Factory,
  Flag,
  Flame,
  Gift,
  Globe,
  GraduationCap,
  HandHeart,
  Handshake,
  Heart,
  HeartCrack,
  Hourglass,
  Infinity as InfinityIcon,
  Landmark,
  MapPin,
  Minus,
  Moon,
  Mountain,
  MoveRight,
  Orbit,
  RefreshCcw,
  Repeat,
  Route,
  Scale,
  Scroll,
  ScrollText,
  Search,
  Shield,
  Shuffle,
  Signpost,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Target,
  Telescope,
  Timer,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
  Undo2,
  Waves,
  Zap,
  Building2,
  HeartHandshake,
  Sword,
  Shell,
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
  impact: { label: 'An impact', icon: Crosshair, tone: 'danger' },
  eruption: { label: 'An eruption', icon: Mountain, tone: 'danger' },
  stellar: { label: 'Its star', icon: Star, tone: 'warning' },
  ocean_shift: { label: 'A turned current', icon: Waves, tone: 'info' },
  made: { label: 'Works of peoples', icon: Factory, tone: 'warning' },
}

export const SPELL_SHAPES: Record<Schema['SeasonSpellShape'], Named> = {
  cycling: { label: 'Cycling', icon: Repeat, tone: 'info' },
  single: { label: 'A single spell', icon: Timer, tone: 'warning' },
}

export const SPELL_REACHES: Record<Schema['LongSeasonReach'], Named> = {
  world: { label: 'The whole world', icon: Globe, tone: 'gold' },
  north: { label: 'The northern half', icon: ArrowUp, tone: 'info' },
  south: { label: 'The southern half', icon: ArrowDown, tone: 'info' },
  equator: { label: 'The equator', icon: Minus, tone: 'warning' },
  poles: { label: 'The poles', icon: Snowflake, tone: 'info' },
}

export const SPELLS: Record<Schema['SeasonSpell'], Named> = {
  summer: { label: 'Long summer', icon: Sun, tone: 'gold' },
  winter: { label: 'Long winter', icon: Snowflake, tone: 'info' },
}

export const CYCLES: Record<Schema['AgeCycle'], Named> = {
  linear: { label: 'Runs on to its end', icon: MoveRight, tone: 'muted' },
  cyclic: { label: 'Turns in ages', icon: RefreshCcw, tone: 'gold' },
  spiral: { label: 'Spiral', icon: Shell, tone: 'gold' },
}

export const TEMPLATES: Record<Schema['ArcTemplate'], Named> = {
  rise_and_fall: {
    label: 'Rise and fall',
    icon: TrendingDown,
    tone: 'warning',
  },
  rags_to_riches: {
    label: 'From poverty to wealth',
    icon: TrendingUp,
    tone: 'gold',
  },
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
  overcoming: { label: 'Overcoming', icon: Shield, tone: 'success' },
  reconciliation: {
    label: 'Reconciliation',
    icon: Handshake,
    tone: 'verdigris',
  },
  sacrifice: { label: 'Sacrifice', icon: Flame, tone: 'gold' },
  discovery: { label: 'Discovery', icon: Search, tone: 'info' },
  betrayal: {
    label: 'Betrayal',
    icon: Sword,
    tone: 'danger',
  },
  friendship: {
    label: 'Friendship',
    icon: HeartHandshake,
    tone: 'success',
  },
  legacy: {
    label: 'Legacy',
    icon: Building2,
    tone: 'gold',
  },
}

export const STAGES: Record<Schema['ArcStage'], Named> = {
  inciting: { label: 'Inciting', icon: Flame, tone: 'warning' },
  rising: { label: 'Rising', icon: TrendingUp, tone: 'info' },
  crisis: { label: 'Crisis', icon: Zap, tone: 'danger' },
  climax: { label: 'Climax', icon: Mountain, tone: 'gold' },
  call: { label: 'The call', icon: Bell, tone: 'warning' },
  refusal: { label: 'The refusal', icon: Ban, tone: 'muted' },
  mentor: {
    label: 'Meeting the mentor',
    icon: GraduationCap,
    tone: 'verdigris',
  },
  threshold: { label: 'The threshold', icon: DoorOpen, tone: 'info' },
  ordeal: { label: 'The ordeal', icon: Swords, tone: 'danger' },
  return: { label: 'The return', icon: Undo2, tone: 'gold' },
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
  witness: { label: 'Witness', icon: Eye, tone: 'info' },
  guide: { label: 'Guide', icon: Signpost, tone: 'verdigris' },
}

export const SETUP_KINDS: Record<Schema['SetupKind'], Named> = {
  prophecy: { label: 'Prophecy', icon: Scroll, tone: 'gold' },
  omen: { label: 'Omen', icon: Eye, tone: 'info' },
  dream: { label: 'Dream', icon: Moon, tone: 'verdigris' },
  foresight: { label: 'Foresight', icon: Telescope, tone: 'info' },
  portent: { label: 'Portent of a god', icon: Sparkles, tone: 'gold' },
  incident_arc: { label: 'Open incident arc', icon: ScrollText, tone: 'muted' },
  inheritance: { label: 'Inheritance', icon: Gift, tone: 'gold' },
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
  end_of_the_gods: {
    label: 'The end of the gods',
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
