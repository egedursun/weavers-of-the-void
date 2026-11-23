import {
  type LucideIcon,
  ArrowDown,
  ArrowUp,
  Beaker,
  Bird,
  Bomb,
  Brain,
  Bug,
  Cloud,
  Crown,
  Dna,
  Droplet,
  Droplets,
  Ear,
  Eye,
  EyeOff,
  Fence,
  Flame,
  FlaskConical,
  Flower2,
  Footprints,
  Hand,
  HandHeart,
  Heart,
  Hourglass,
  Layers,
  Leaf,
  Mountain,
  MountainSnow,
  Rabbit,
  Recycle,
  Ruler,
  Scale,
  Shell,
  Shield,
  ShieldPlus,
  ShieldX,
  Shovel,
  Snowflake,
  Sprout,
  Squirrel,
  Sun,
  TreeDeciduous,
  TreePine,
  Trees,
  Waves,
  Wheat,
  Wind,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import type { ProgressTone } from '@/components/ui/progress'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const EVOLUTION_ICON: LucideIcon = Dna

export const TRAITS: Record<Schema['EvolvedTrait'], Named> = {
  size: { label: 'Size', icon: Ruler, tone: 'info' },
  speed: { label: 'Speed', icon: Rabbit, tone: 'success' },
  armour: { label: 'Armour', icon: Shield, tone: 'muted' },
  venom: { label: 'Venom', icon: Beaker, tone: 'danger' },
  camouflage: { label: 'Camouflage', icon: EyeOff, tone: 'verdigris' },
  cold_tolerance: { label: 'Cold tolerance', icon: Snowflake, tone: 'info' },
  intelligence: { label: 'Wits', icon: Brain, tone: 'gold' },
  fecundity: { label: 'Fecundity', icon: Heart, tone: 'success' },
  wariness: { label: 'Wariness', icon: Eye, tone: 'warning' },
  heat_tolerance: { label: 'Heat tolerance', icon: Sun, tone: 'warning' },
  drought_tolerance: {
    label: 'Drought tolerance',
    icon: Droplet,
    tone: 'warning',
  },
  keen_senses: { label: 'Keen senses', icon: Ear, tone: 'info' },
  disease_resistance: {
    label: 'Disease resistance',
    icon: ShieldPlus,
    tone: 'success',
  },
  docility: { label: 'Docility', icon: HandHeart, tone: 'gold' },
  longevity: { label: 'Longevity', icon: Hourglass, tone: 'info' },
}

export const KEYSTONES: Record<Schema['KeystoneRole'], Named> = {
  pollinator: { label: 'Pollinator', icon: Flower2, tone: 'gold' },
  soil_maker: { label: 'Soil-maker', icon: Shovel, tone: 'verdigris' },
  dam_builder: { label: 'Dam-builder', icon: Waves, tone: 'info' },
  scavenger: { label: 'Scavenger', icon: Bird, tone: 'muted' },
  seed_disperser: { label: 'Seed carrier', icon: Sprout, tone: 'success' },
  regulator: { label: 'Regulator', icon: Scale, tone: 'warning' },
  reef_builder: { label: 'Reef builder', icon: Shell, tone: 'info' },
}

export const LEVELS: Record<Schema['TrophicLevel'], Named> = {
  producer: { label: 'Plants and makers', icon: Sprout, tone: 'success' },
  herbivore: { label: 'Grazers', icon: Squirrel, tone: 'verdigris' },
  carnivore: { label: 'Hunters', icon: Footprints, tone: 'warning' },
  apex: { label: 'Apex', icon: Crown, tone: 'danger' },
  decomposer: { label: 'Decomposers', icon: Recycle, tone: 'muted' },
}

export const RESPONSES: Record<Schema['PlagueResponse'], Named> = {
  close_borders: { label: 'Closed borders', icon: Fence, tone: 'warning' },
  quarantine: { label: 'Quarantine', icon: ShieldX, tone: 'info' },
  burn_dead: { label: 'Burning the dead', icon: Flame, tone: 'danger' },
  expel_sick: {
    label: 'Driving out the sick',
    icon: Footprints,
    tone: 'danger',
  },
  prayer: { label: 'Prayer', icon: Hand, tone: 'gold' },
  seek_cure: { label: 'Seeking a cure', icon: FlaskConical, tone: 'success' },
  sanitation: {
    label: 'Cleaning water and refuse',
    icon: Droplets,
    tone: 'info',
  },
}

export const STAGES: Record<Schema['SuccessionStage'], Named> = {
  bare: { label: 'Bare ground', icon: Mountain, tone: 'muted' },
  grassland: { label: 'Grassland', icon: Wheat, tone: 'gold' },
  shrubland: { label: 'Shrubland', icon: Leaf, tone: 'verdigris' },
  young_forest: { label: 'Young forest', icon: TreeDeciduous, tone: 'success' },
  old_forest: { label: 'Old forest', icon: Trees, tone: 'success' },
  marsh: { label: 'Marsh', icon: Droplets, tone: 'info' },
  swamp_forest: { label: 'Swamp forest', icon: TreePine, tone: 'info' },
  pioneer: { label: 'Pioneer life', icon: Sprout, tone: 'verdigris' },
  open_water: { label: 'Open water', icon: Waves, tone: 'info' },
  bog: { label: 'Bog', icon: Layers, tone: 'info' },
  heath: { label: 'Heath', icon: Flower2, tone: 'gold' },
  coastal_dune: { label: 'Coastal dune', icon: Wind, tone: 'gold' },
}

export const LAND_ACTS: Record<Schema['LandAct'], Named> = {
  shift_river: { label: 'Move its river', icon: Waves, tone: 'info' },
  parch: { label: 'Parch it', icon: Flame, tone: 'warning' },
  green: { label: 'Bring the grass back', icon: Sprout, tone: 'success' },
  make_saline: {
    label: 'Make the soil saline',
    icon: Droplets,
    tone: 'danger',
  },
  enrich_soil: { label: 'Enrich the soil', icon: Leaf, tone: 'success' },
  raise_land: { label: 'Raise the land', icon: ArrowUp, tone: 'gold' },
  lower_land: { label: 'Lower the land', icon: ArrowDown, tone: 'muted' },
  carve_valley: { label: 'Carve a valley', icon: MountainSnow, tone: 'info' },
  fill_valley: { label: 'Fill its valleys', icon: Mountain, tone: 'muted' },
  open_spring: { label: 'Open a spring', icon: Droplets, tone: 'success' },
  call_lava: { label: 'Call up lava', icon: Bomb, tone: 'danger' },
  sink_coast: { label: 'Sink its coast', icon: Waves, tone: 'danger' },
}

export const CYCLES: Record<
  Schema['PlanetaryCycle'],
  Named & { meter: ProgressTone }
> = {
  carbon: { label: 'Carbon', icon: Cloud, tone: 'muted', meter: 'warning' },
  water: { label: 'Water', icon: Droplets, tone: 'info', meter: 'info' },
  nutrients: {
    label: 'Nutrients',
    icon: Sprout,
    tone: 'success',
    meter: 'success',
  },
  oxygen: { label: 'Breathable air', icon: Wind, tone: 'info', meter: 'info' },
  rock: { label: 'Rock', icon: Mountain, tone: 'muted', meter: 'warning' },
}

export const MARK_ICONS = { blessing: Crown, taint: Bug }
