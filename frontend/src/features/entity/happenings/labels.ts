import {
  type LucideIcon,
  Activity,
  Ban,
  Biohazard,
  BookMarked,
  Building2,
  CircleDot,
  CloudLightning,
  CloudRain,
  Crown,
  Droplets,
  Eclipse,
  Flame,
  Footprints,
  Gem,
  Hammer,
  Heart,
  Hourglass,
  Landmark,
  Layers,
  Mountain,
  MountainSnow,
  PartyPopper,
  Shield,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Sun,
  Swords,
  TrendingUp,
  Users,
  Waves,
  Wheat,
  Wind,
  Droplet,
  FlameKindling,
  GlassWater,
  HeartCrack,
  Leaf,
  Sword,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Spec } from '../society/labels'

type Schemas = components['schemas']
export type EventPhase = Schemas['EventPhase']
export type SoilKind = Schemas['SoilKind']
export type RiverClass = Schemas['RiverClass']
export type RiverShiftCause = Schemas['RiverShiftCause']

export const EVENT_ICON: LucideIcon = Hourglass
export const LAND_ICON: LucideIcon = Mountain

export const KIND_SPEC: Record<string, Spec> = {
  war: { label: 'War', icon: Sword, tone: 'danger' },
  battle: { label: 'Battle', icon: Swords, tone: 'danger' },
  siege: { label: 'Siege', icon: Shield, tone: 'warning' },
  magic_storm: { label: 'Magic storm', icon: Sparkles, tone: 'verdigris' },
  earthquake: { label: 'Earthquake', icon: Activity, tone: 'warning' },
  flood: { label: 'Flood', icon: Waves, tone: 'info' },
  plague: { label: 'Plague', icon: Biohazard, tone: 'danger' },
  drought: { label: 'Drought', icon: Sun, tone: 'warning' },
  storm: { label: 'Storm', icon: CloudLightning, tone: 'info' },
  famine: { label: 'Famine', icon: Wheat, tone: 'danger' },
  uprising: { label: 'Uprising', icon: Users, tone: 'warning' },
  migration: { label: 'Migration', icon: Footprints, tone: 'muted' },
  festival_of_note: {
    label: 'Festival of note',
    icon: PartyPopper,
    tone: 'success',
    hint: 'Calms the town and brings it prosperity',
  },
  coronation: {
    label: 'Accession',
    icon: Crown,
    tone: 'gold',
    hint: 'A new ruler takes office; the realm takes heart',
  },
  wedding: {
    label: 'Wedding',
    icon: Heart,
    tone: 'success',
    hint: 'Joins two houses; goodwill between their peoples',
  },
  massacre: {
    label: 'Massacre',
    icon: Skull,
    tone: 'danger',
    hint: 'No quarter given; the ground stays haunted',
  },
  sack: {
    label: 'Sack',
    icon: Flame,
    tone: 'danger',
    hint: 'A city plundered and burned',
  },
  fire: {
    label: 'Great fire',
    icon: FlameKindling,
    tone: 'warning',
    hint: 'Burns districts and leaves burned ground',
  },
  eruption: {
    label: 'Eruption',
    icon: MountainSnow,
    tone: 'danger',
    hint: 'Buries the land in ash that later turns to rich soil',
  },
  riot: {
    label: 'Riot',
    icon: Ban,
    tone: 'warning',
    hint: 'Vents unrest at the cost of lives and prosperity',
  },
  schism_council: {
    label: 'Schism council',
    icon: Landmark,
    tone: 'verdigris',
    hint: 'A faith breaks apart in council',
  },
  eclipse_watch: {
    label: 'Eclipse watch',
    icon: Eclipse,
    tone: 'info',
    hint: 'The people watch the sun go dark; piety rises',
  },
}

export function kindSpec(kind: string | null | undefined): Spec {
  return (
    (kind ? KIND_SPEC[kind] : undefined) ?? {
      label: 'Event',
      icon: EVENT_ICON,
      tone: 'muted',
    }
  )
}

export const PHASE_SPEC: Record<EventPhase, Spec> = {
  onset: {
    label: 'Beginning',
    icon: CircleDot,
    tone: 'warning',
    hint: 'It has broken out',
  },
  peak: {
    label: 'Height',
    icon: TrendingUp,
    tone: 'danger',
    hint: 'At its worst; famines, plagues and sieges kill each age',
  },
  aftermath: {
    label: 'Aftermath',
    icon: Sprout,
    tone: 'success',
    hint: 'The worst is over; its traces remain',
  },
  memory: {
    label: 'Memory',
    icon: BookMarked,
    tone: 'muted',
    hint: 'It is over; the communities it struck keep it',
  },
}
export const PHASE_ORDER: EventPhase[] = [
  'onset',
  'peak',
  'aftermath',
  'memory',
]

export const SOIL_SPEC: Record<SoilKind, Spec> = {
  thin: { label: 'Thin soil', icon: Mountain, tone: 'muted' },
  loam: { label: 'Loam', icon: Sprout, tone: 'success' },
  clay: { label: 'Clay', icon: CircleDot, tone: 'gold' },
  sand: { label: 'Sand', icon: Wind, tone: 'warning' },
  volcanic: { label: 'Volcanic soil', icon: MountainSnow, tone: 'success' },
  peat: { label: 'Peat', icon: Droplets, tone: 'verdigris' },
  saline: { label: 'Saline soil', icon: Gem, tone: 'danger' },
  tephra: { label: 'Tephra', icon: Flame, tone: 'warning' },
  crystalline: { label: 'Crystalline soil', icon: Gem, tone: 'info' },
  calcareous: { label: 'Calcareous soil', icon: CircleDot, tone: 'muted' },
  laterite: { label: 'Laterite', icon: Layers, tone: 'warning' },
  permafrost: { label: 'Permafrost', icon: Snowflake, tone: 'info' },
  regolith: { label: 'Regolith', icon: Mountain, tone: 'muted' },
  artificial: { label: 'Made ground', icon: Building2, tone: 'gold' },
  humic: { label: 'Humic soil', icon: Leaf, tone: 'success' },
  leached: { label: 'Leached soil', icon: Droplet, tone: 'muted' },
  silt: { label: 'Silt', icon: Waves, tone: 'info' },
  gley: { label: 'Gley', icon: GlassWater, tone: 'verdigris' },
  cracking_clay: { label: 'Cracking clay', icon: HeartCrack, tone: 'warning' },
}

export const RIVER_SPEC: Record<RiverClass, Spec> = {
  none: { label: 'No river', icon: Sun, tone: 'muted' },
  stream: { label: 'Stream', icon: Droplets, tone: 'info' },
  river: { label: 'River', icon: Waves, tone: 'info' },
  great_river: { label: 'Great river', icon: Waves, tone: 'verdigris' },
}

export const CAUSE_SPEC: Record<RiverShiftCause, Spec> = {
  flood: { label: 'A great flood', icon: CloudRain, tone: 'info' },
  quake: { label: 'An earthquake', icon: Activity, tone: 'warning' },
  divine: { label: 'A god', icon: Sun, tone: 'gold' },
  player: { label: 'Your hand', icon: Sparkles, tone: 'gold' },
  silting: { label: 'Its bed silted up', icon: Waves, tone: 'muted' },
  works: { label: 'The works of a people', icon: Hammer, tone: 'warning' },
  eruption: { label: 'An eruption', icon: Flame, tone: 'danger' },
  landslide: { label: 'A landslide', icon: Mountain, tone: 'warning' },
  ice: { label: 'River ice', icon: Snowflake, tone: 'info' },
  capture: {
    label: 'Another river cut into it',
    icon: Droplets,
    tone: 'muted',
  },
}

export const FIELD_LABEL: Record<string, string> = {
  phase: 'Phase',
  start_year: 'Start year',
  start_season: 'Start season',
  end_year: 'End year',
  end_season: 'End season',
  desertification: 'Desertification',
  desertified: 'Desert',
  volcanic: 'Volcanic',
  volcanic_pressure: 'Volcanic pressure',
  soil: 'Soil',
}

export function fieldLabel(key: string): string {
  return FIELD_LABEL[key] ?? key.replaceAll('_', ' ')
}
