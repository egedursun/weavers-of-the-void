import {
  Activity,
  Ban,
  CircleDashed,
  CircleDot,
  CloudFog,
  Compass,
  Eye,
  Flame,
  Ghost,
  Hourglass,
  Layers,
  Link2,
  type LucideIcon,
  Moon,
  Orbit,
  Repeat,
  Shield,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Waves,
  Workflow,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const ZONES: Record<Schema['GalacticZone'], Named> = {
  core: { label: 'Core', icon: CircleDot, tone: 'danger' },
  bulge: { label: 'Bulge', icon: Sun, tone: 'warning' },
  bar: { label: 'Bar', icon: Activity, tone: 'warning' },
  inner_disc: { label: 'Inner disc', icon: Orbit, tone: 'gold' },
  arm: { label: 'Arm', icon: Sparkles, tone: 'success' },
  interarm: { label: 'Between the arms', icon: CircleDashed, tone: 'info' },
  outer_disc: { label: 'Outer disc', icon: Orbit, tone: 'verdigris' },
  halo: { label: 'Halo', icon: CircleDashed, tone: 'muted' },
  rim: { label: 'Rim', icon: Compass, tone: 'muted' },
  intergalactic: { label: 'Between galaxies', icon: Star, tone: 'muted' },
}

export const NUCLEI: Record<Schema['GalacticNucleus'], Named> = {
  none: { label: 'No nucleus', icon: CircleDashed, tone: 'muted' },
  dormant: { label: 'Dormant nucleus', icon: CircleDot, tone: 'info' },
  active: { label: 'Active nucleus', icon: Flame, tone: 'warning' },
  quasar: { label: 'Quasar', icon: Zap, tone: 'danger' },
  devoured: { label: 'Devoured nucleus', icon: Ban, tone: 'muted' },
}

export const GALAXY_AGES: Record<Schema['GalaxyAge'], string> = {
  forming: 'Forming',
  young: 'Young',
  mature: 'Mature',
  old: 'Old',
  dying: 'Dying',
  dead: 'Dead',
}

export const STAR_AGES: Record<Schema['StarAge'], Named> = {
  young: { label: 'Young', icon: Sprout, tone: 'success' },
  main: { label: 'Main life', icon: Sun, tone: 'gold' },
  old: { label: 'Old', icon: Hourglass, tone: 'warning' },
  dying: { label: 'Dying', icon: Flame, tone: 'danger' },
  dead: { label: 'Dead', icon: Moon, tone: 'muted' },
  reborn: { label: 'Reborn', icon: Repeat, tone: 'info' },
}

export const WORLD_AGES: Record<Schema['WorldAge'], string> = {
  young: 'Young',
  mature: 'Mature',
  old: 'Old',
  dying: 'Dying',
}

export const CAUSALITIES: Record<Schema['Causality'], string> = {
  strict: 'Strict causality',
  loose: 'Loose causality',
  broken: 'Broken causality',
}

export const ELEMENTS: Record<Schema['DimensionElement'], string> = {
  fire: 'Fire',
  water: 'Water',
  earth: 'Earth',
  air: 'Air',
  void: 'Void',
  light: 'Light',
  shadow: 'Shadow',
  ice: 'Ice',
  lightning: 'Lightning',
  metal: 'Metal',
  wood: 'Wood',
}

export const RIFT_STATES: Record<Schema['RiftState'], Named> = {
  opening: { label: 'Opening', icon: CircleDashed, tone: 'warning' },
  open: { label: 'Open', icon: Eye, tone: 'danger' },
  closing: { label: 'Closing', icon: Hourglass, tone: 'info' },
  sealed: { label: 'Sealed', icon: Shield, tone: 'success' },
  collapsed: { label: 'Collapsed', icon: Ban, tone: 'muted' },
}

export const RIFT_CAUSES: Record<Schema['RiftCause'], string> = {
  rite_backlash: 'Rite backlash',
  leak_peak: 'Leak peak',
  convergence: 'Convergence',
  god: "A god's act",
  being: 'A cosmic being',
  phenomenon: 'A phenomenon',
  creator: 'The Creator',
}

export const SCOPES: Record<Schema['RouteScope'], Named> = {
  system: { label: 'Within one system', icon: Sun, tone: 'success' },
  stellar: { label: 'Between stars', icon: Star, tone: 'gold' },
  galactic: { label: 'To a near galaxy', icon: Orbit, tone: 'info' },
  intergalactic: { label: 'Between galaxies', icon: Orbit, tone: 'warning' },
  intercluster: { label: 'Between clusters', icon: Workflow, tone: 'danger' },
  interdimensional: {
    label: 'Between dimensions',
    icon: Layers,
    tone: 'danger',
  },
}

export const BEING_SCALES: Record<Schema['BeingScale'], string> = {
  world: 'World',
  system: 'Star system',
  galaxy: 'Galaxy',
  cluster: 'Cluster',
  dimension: 'Dimension',
}

export const BEING_PHASES: Record<Schema['BeingPhase'], Named> = {
  dormant: { label: 'Dormant', icon: Moon, tone: 'muted' },
  roaming: { label: 'Roaming', icon: Compass, tone: 'info' },
  manifest: { label: 'Manifest', icon: Eye, tone: 'warning' },
  incursion: { label: 'In incursion', icon: Swords, tone: 'danger' },
  bound: { label: 'Bound', icon: Link2, tone: 'success' },
  banished: { label: 'Banished', icon: Ban, tone: 'muted' },
}

export const BEING_AGENDAS: Record<Schema['BeingAgenda'], string> = {
  feed: 'Feed',
  explore: 'Explore',
  conquer: 'Conquer',
  guard: 'Guard',
  trade: 'Trade',
  flee: 'Flee',
  seek_worship: 'Seek worship',
  unmake: 'Unmake',
  mend: 'Mend',
}

export const PHENOMENON_CAUSES: Record<Schema['PhenomenonCause'], string> = {
  rite_backlash: 'Rite backlash',
  god_death: "A god's death",
  law_conflict: 'Clashing natural laws',
  sky_event: 'A sky event',
  leak_peak: 'A leak peak',
  battlefield: 'A great battlefield',
  rift: 'A rift',
  divine: 'A divine act',
}

export const OMENS: Record<Schema['OmenReading'], Named> = {
  good: { label: 'Good omen', icon: Sun, tone: 'success' },
  evil: { label: 'Evil omen', icon: Ghost, tone: 'danger' },
  neutral: { label: 'No omen', icon: CircleDashed, tone: 'muted' },
}

export const CURRENTS: Record<Schema['OceanCurrent'], Named> = {
  none: { label: 'No current', icon: CircleDashed, tone: 'muted' },
  warm: { label: 'Warm current', icon: Waves, tone: 'warning' },
  cold: { label: 'Cold current', icon: Waves, tone: 'info' },
}

export const CLIMATE_TURNS = {
  warmer: 'Warmer',
  colder: 'Colder',
  wetter: 'Wetter',
  drier: 'Drier',
} as const

export const STRUCTURES: Record<Schema['GalacticStructureKind'], Named> = {
  spiral_arm: { label: 'Spiral arm', icon: Waves, tone: 'info' },
  bar: { label: 'Bar', icon: Activity, tone: 'warning' },
  bulge: { label: 'Bulge', icon: Sun, tone: 'gold' },
  core: { label: 'Core', icon: CircleDot, tone: 'danger' },
  halo: { label: 'Halo', icon: CircleDashed, tone: 'muted' },
  emission_nebula: { label: 'Emission nebula', icon: CloudFog, tone: 'danger' },
  reflection_nebula: {
    label: 'Reflection nebula',
    icon: CloudFog,
    tone: 'info',
  },
  dark_nebula: { label: 'Dark nebula', icon: Moon, tone: 'muted' },
  planetary_nebula: {
    label: 'Planetary nebula',
    icon: CircleDot,
    tone: 'verdigris',
  },
  supernova_remnant: {
    label: 'Supernova remnant',
    icon: Flame,
    tone: 'warning',
  },
  stellar_nursery: { label: 'Stellar nursery', icon: Sprout, tone: 'success' },
  open_cluster: { label: 'Open cluster', icon: Sparkles, tone: 'info' },
  globular_cluster: { label: 'Globular cluster', icon: Sparkles, tone: 'gold' },
  stellar_stream: { label: 'Stellar stream', icon: Waves, tone: 'info' },
  dust_lane: { label: 'Dust lane', icon: CloudFog, tone: 'muted' },
  superbubble: { label: 'Superbubble', icon: CircleDashed, tone: 'danger' },
  star_graveyard: { label: 'Star graveyard', icon: Ghost, tone: 'muted' },
  ley_spiral: { label: 'Ley spiral', icon: Zap, tone: 'verdigris' },
  sealed_vault: { label: 'Sealed vault', icon: Shield, tone: 'gold' },
  gods_forge: { label: "Gods' forge", icon: Flame, tone: 'gold' },
  dead_light_drift: { label: 'Dead light drift', icon: Ghost, tone: 'muted' },
  singing_nebula: {
    label: 'Singing nebula',
    icon: Sparkles,
    tone: 'verdigris',
  },
  rift_scar: { label: 'Rift scar', icon: Eye, tone: 'danger' },
}

export const HELD_LABELS: Record<string, string> = {
  veil: 'Veil',
  stability: 'Stability',
  time_factor: 'Time',
  magic: 'Magic',
  hostility: 'Hostility',
  sanity_drain: 'Sanity drain',
  leak: 'Leak',
  causality: 'Causality',
  discovery: 'Discovery',
  ruler_node_id: 'Ruler',
  parent_dimension_id: 'Parent dimension',
  medium_heat: 'Heat of the medium',
  expansion: 'Drift',
  radius: 'Radius',
  x: 'Position',
  y: 'Position',
  star_formation: 'Star formation',
  metallicity: 'Metallicity',
  age_stage: 'Age',
  nucleus: 'Nucleus',
  arm_count: 'Arms',
  patron_son_id: 'Patron',
  merging_with_galaxy_id: 'Merging with',
  merge_progress: 'Merge progress',
  galaxy_type: 'Type',
  cluster_id: 'Cluster',
  dimension_id: 'Dimension',
  intensity: 'Intensity',
  size: 'Size',
  state: 'State',
  might: 'Might',
  phase: 'Phase',
  agenda: 'Aim',
  scale: 'Scale',
  growth: 'Growth',
  containment: 'Containment',
  galactic_zone: 'Zone',
  structure_id: 'Structure',
  galaxy_id: 'Galaxy',
  lifecycle_clock: 'Next age',
  radiation: 'Radiation',
  sacredness: 'Sacredness',
  magnetism: 'Magnetism',
  biosphere_health: 'Biosphere',
  mood: 'Mood',
  danger: 'Danger',
  capacity: 'Capacity',
  traffic: 'Traffic',
  toll_pct: 'Toll',
  toll_controller_entity_id: 'Toll keeper',
  piracy: 'Piracy',
  wear: 'Wear',
  window_every: 'Window',
  window_offset: 'Window offset',
  convoy: 'Convoy',
  escorts: 'Escorts',
  cargo: 'Cargo',
  passengers: 'Passengers',
  reading: 'Reading',
  brightness: 'Brightness',
  star_type: 'Type',
}

export function heldLabel(key: string): string {
  return HELD_LABELS[key] ?? key.replaceAll('_', ' ')
}
