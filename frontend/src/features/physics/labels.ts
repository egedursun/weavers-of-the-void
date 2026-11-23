import {
  ArrowDown,
  Atom,
  Bird,
  Ban,
  Check,
  CircleDot,
  CloudFog,
  Compass,
  Droplets,
  Eye,
  Flame,
  Fish,
  Footprints,
  Gem,
  Globe2,
  HelpCircle,
  Leaf,
  Map as MapIcon,
  Microscope,
  Mountain,
  Orbit,
  Radar,
  ShieldCheck,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  SunDim,
  Telescope,
  Users,
  Wind,
  Zap,
  Cog,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: typeof Star; tone: KpiTone }

export const FEATURE_KINDS: Record<
  Schema['CosmicFeatureKind'],
  Named & { hint: string }
> = {
  asteroid_field: {
    label: 'Asteroid field',
    icon: Gem,
    tone: 'gold',
    hint: 'Feeds miners with ore, hides pirates and sends bodies at the worlds of its star',
  },
  wormhole: {
    label: 'Wormhole',
    icon: Orbit,
    tone: 'verdigris',
    hint: 'A road between two worlds that opens and closes by its instability',
  },
  periodic_comet: {
    label: 'Periodic comet',
    icon: Sparkles,
    tone: 'info',
    hint: 'Returns at its period as an omen, and can strike a world of its star',
  },
  rogue_world: {
    label: 'Rogue world',
    icon: Globe2,
    tone: 'warning',
    hint: 'Drifts from star to star, stirring orbits and sending bodies at the worlds it passes',
  },
  gravity_well: {
    label: 'Gravity well',
    icon: CircleDot,
    tone: 'danger',
    hint: 'The pull around a black hole: it shortens routes past it, slows time for travellers and swallows near worlds',
  },
  wandering_star: {
    label: 'Wandering star',
    icon: Star,
    tone: 'gold',
    hint: 'A light that crosses the sky of its star and returns at its period, raising festivals and prophecies',
  },
}

export const SURVEY_LEVELS: Record<
  Schema['SurveyLevel'],
  Named & { rank: number }
> = {
  unknown: { label: 'Unknown', icon: HelpCircle, tone: 'muted', rank: 0 },
  rumoured: { label: 'Rumoured', icon: Users, tone: 'muted', rank: 1 },
  detected: { label: 'Detected', icon: Radar, tone: 'info', rank: 2 },
  observed: { label: 'Observed', icon: Telescope, tone: 'info', rank: 3 },
  surveyed: { label: 'Surveyed', icon: Footprints, tone: 'verdigris', rank: 4 },
  mapped: { label: 'Mapped', icon: MapIcon, tone: 'success', rank: 5 },
}

export const SYSTEM_ROLES: Record<Schema['SystemRole'], Named> = {
  primary: { label: 'Primary', icon: Sun, tone: 'gold' },
  companion: { label: 'Companion', icon: SunDim, tone: 'info' },
}

export const IMPACT_BODIES: Record<Schema['ImpactBody'], Named> = {
  asteroid: { label: 'Asteroid', icon: Gem, tone: 'warning' },
  comet: { label: 'Comet', icon: Sparkles, tone: 'info' },
  rogue_world: { label: 'Rogue world', icon: Globe2, tone: 'danger' },
  called: { label: 'Called by a god', icon: Zap, tone: 'gold' },
  moon_fragment: {
    label: 'Fragment of a broken moon',
    icon: CircleDot,
    tone: 'warning',
  },
  wreck: { label: 'Fallen made thing', icon: Cog, tone: 'danger' },
}

export const IMPACT_OUTCOMES: Record<Schema['ImpactOutcome'], Named> = {
  pending: { label: 'Coming', icon: ArrowDown, tone: 'warning' },
  struck: { label: 'Struck', icon: Flame, tone: 'danger' },
  deflected: { label: 'Turned aside', icon: ShieldCheck, tone: 'success' },
  missed: { label: 'Missed', icon: Ban, tone: 'muted' },
  airburst: { label: 'Burst in the air', icon: Wind, tone: 'danger' },
}

export const TERRAFORM_AIMS: Record<Schema['TerraformAim'], Named> = {
  thicken_air: { label: 'Thicken the air', icon: CloudFog, tone: 'info' },
  thin_air: { label: 'Thin the air', icon: Wind, tone: 'muted' },
  breathable_air: {
    label: 'Make the air breathable',
    icon: Leaf,
    tone: 'success',
  },
  warm: { label: 'Warm it', icon: Flame, tone: 'warning' },
  cool: { label: 'Cool it', icon: Snowflake, tone: 'info' },
  water: { label: 'Give it water', icon: Droplets, tone: 'info' },
  dry: { label: 'Dry it', icon: Sun, tone: 'gold' },
  brighten: { label: 'Brighten its face', icon: Sparkles, tone: 'gold' },
  darken: { label: 'Darken its face', icon: Eye, tone: 'muted' },
}

export const COMPLEXITY: Record<
  Schema['LifeComplexity'],
  Named & { rank: number }
> = {
  none: { label: 'No life', icon: Ban, tone: 'muted', rank: 0 },
  microbial: { label: 'Microbial', icon: Microscope, tone: 'info', rank: 1 },
  simple: { label: 'Simple', icon: Sprout, tone: 'verdigris', rank: 2 },
  complex: { label: 'Complex', icon: Leaf, tone: 'success', rank: 3 },
  sapient: { label: 'Sapient', icon: Users, tone: 'gold', rank: 4 },
}

export const ENVIRONMENTS: Record<Schema['LifeEnvironment'], Named> = {
  marine: { label: 'Seas', icon: Fish, tone: 'info' },
  terrestrial: { label: 'Land', icon: Mountain, tone: 'verdigris' },
  aerial: { label: 'Air', icon: Bird, tone: 'muted' },
  subterranean: { label: 'Underground', icon: Compass, tone: 'warning' },
  under_ice: { label: 'Oceans under ice', icon: Snowflake, tone: 'info' },
  cloud: { label: 'Cloud layers', icon: CloudFog, tone: 'muted' },
}

export const AIR_NEEDS: Record<Schema['AirNeed'], Named> = {
  oxygen: { label: 'Breathes oxygen', icon: Wind, tone: 'info' },
  carbon_dioxide: {
    label: 'Breathes carbon dioxide',
    icon: CloudFog,
    tone: 'verdigris',
  },
  methane: { label: 'Breathes methane', icon: Atom, tone: 'warning' },
  ammonia: { label: 'Breathes ammonia', icon: Atom, tone: 'danger' },
  hydrogen: { label: 'Breathes hydrogen', icon: Atom, tone: 'info' },
  none: { label: 'Needs no air', icon: Check, tone: 'muted' },
}

export const STAR_STAGES: Record<Schema['StarAge'], string> = {
  young: 'Young',
  main: 'Main life',
  old: 'Old',
  dying: 'Dying',
  dead: 'Dead',
  reborn: 'Reborn',
}

export function table(
  record: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(record).map(([key, value]) => [key, value.label])
  )
}
