import {
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
  Heart,
  Leaf,
  Mountain,
  MountainSnow,
  Rabbit,
  Ruler,
  Shield,
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
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
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
}

export const KEYSTONES: Record<Schema['KeystoneRole'], Named> = {
  pollinator: { label: 'Pollinator', icon: Flower2, tone: 'gold' },
  soil_maker: { label: 'Soil-maker', icon: Shovel, tone: 'verdigris' },
  dam_builder: { label: 'Dam-builder', icon: Waves, tone: 'info' },
  scavenger: { label: 'Scavenger', icon: Bird, tone: 'muted' },
}

export const LEVELS: Record<Schema['TrophicLevel'], Named> = {
  producer: { label: 'Plants and makers', icon: Sprout, tone: 'success' },
  herbivore: { label: 'Grazers', icon: Squirrel, tone: 'verdigris' },
  carnivore: { label: 'Hunters', icon: Footprints, tone: 'warning' },
  apex: { label: 'Apex', icon: Crown, tone: 'danger' },
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
}

export const STAGES: Record<Schema['SuccessionStage'], Named> = {
  bare: { label: 'Bare ground', icon: Mountain, tone: 'muted' },
  grassland: { label: 'Grassland', icon: Wheat, tone: 'gold' },
  shrubland: { label: 'Shrubland', icon: Leaf, tone: 'verdigris' },
  young_forest: { label: 'Young forest', icon: TreeDeciduous, tone: 'success' },
  old_forest: { label: 'Old forest', icon: Trees, tone: 'success' },
  marsh: { label: 'Marsh', icon: Droplets, tone: 'info' },
  swamp_forest: { label: 'Swamp forest', icon: TreePine, tone: 'info' },
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

export const CYCLES: Record<'carbon' | 'water' | 'nutrients', Named> = {
  carbon: { label: 'Carbon', icon: Cloud, tone: 'muted' },
  water: { label: 'Water', icon: Droplets, tone: 'info' },
  nutrients: { label: 'Nutrients', icon: Sprout, tone: 'success' },
}

export const MARK_ICONS = { blessing: Crown, taint: Bug }
