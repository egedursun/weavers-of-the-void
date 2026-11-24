import {
  Bone,
  Box,
  CircleDot,
  DoorOpen,
  Droplets,
  Flame,
  Gem,
  Globe,
  HeartPulse,
  Layers,
  Lock,
  Mountain,
  MountainSnow,
  MoveHorizontal,
  MoveVertical,
  Pickaxe,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Waves,
  Wind,
  Zap,
  Crown,
  Diamond,
  Droplet,
  GlassWater,
  Hexagon,
  Layers2,
  Layers3,
  Pyramid,
  Sparkle,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import type { Named } from './labels'

type Schema = components['schemas']

export const ROCK: Record<Schema['RockKind'], Named> = {
  soil: { label: 'Soil', icon: Sprout, tone: 'success' },
  clay: { label: 'Clay', icon: CircleDot, tone: 'gold' },
  sand: { label: 'Sand', icon: Wind, tone: 'warning' },
  limestone: { label: 'Limestone', icon: Layers, tone: 'muted' },
  sandstone: { label: 'Sandstone', icon: Layers2, tone: 'gold' },
  shale: { label: 'Shale', icon: Layers3, tone: 'muted' },
  granite: { label: 'Granite', icon: Mountain, tone: 'muted' },
  basalt: { label: 'Basalt', icon: Pyramid, tone: 'info' },
  marble: { label: 'Marble', icon: Gem, tone: 'gold' },
  obsidian: { label: 'Obsidian', icon: Diamond, tone: 'verdigris' },
  slate: { label: 'Slate', icon: Layers, tone: 'info' },
  crystal_bedrock: { label: 'Crystal bedrock', icon: Sparkles, tone: 'info' },
  frozen_methane: { label: 'Frozen methane', icon: Snowflake, tone: 'info' },
  bone: { label: 'Bone', icon: Bone, tone: 'muted' },
  glass: { label: 'Glass', icon: GlassWater, tone: 'info' },
  halite: { label: 'Halite', icon: Box, tone: 'muted' },
  coal: { label: 'Coal', icon: Flame, tone: 'warning' },
  chalk: { label: 'Chalk', icon: CircleDot, tone: 'muted' },
  tuff: { label: 'Tuff', icon: Mountain, tone: 'gold' },
  gneiss: { label: 'Gneiss', icon: MountainSnow, tone: 'gold' },
  quartzite: { label: 'Quartzite', icon: Crown, tone: 'muted' },
  water_ice: { label: 'Water ice', icon: Droplet, tone: 'info' },
  iron: { label: 'Iron crust', icon: Pickaxe, tone: 'warning' },
  carbon: { label: 'Carbon crust', icon: Sparkle, tone: 'muted' },
  living_tissue: { label: 'Living tissue', icon: HeartPulse, tone: 'danger' },
  pumice: { label: 'Pumice', icon: Waves, tone: 'muted' },
  serpentinite: { label: 'Serpentinite', icon: Hexagon, tone: 'success' },
  travertine: { label: 'Travertine', icon: Layers, tone: 'gold' },
}

export const STRATUM: Record<
  Schema['UndergroundStratum'],
  Named & { hint: string }
> = {
  aquifer: {
    label: 'Aquifer',
    icon: Droplets,
    tone: 'info',
    hint: 'Water held in porous rock; wells draw it and deep mines flood',
  },
  cavern_upper: {
    label: 'Upper caverns',
    icon: Layers,
    tone: 'muted',
    hint: 'Hollows dissolved in soluble rock',
  },
  cavern_middle: {
    label: 'Middle caverns',
    icon: Layers2,
    tone: 'verdigris',
    hint: 'Deeper hollows under rough country',
  },
  cavern_lower: {
    label: 'Lower caverns',
    icon: Pickaxe,
    tone: 'warning',
    hint: 'The deepest hollows, opened by moving crust',
  },
  magma_sea: {
    label: 'Magma sea',
    icon: Flame,
    tone: 'danger',
    hint: 'Molten rock; it warms forges and burns when breached',
  },
  deep_underworld: {
    label: 'Deep underworld',
    icon: Skull,
    tone: 'danger',
    hint: 'Where the deep meets the realm below',
  },
  under_ocean: {
    label: 'Ocean under the ice',
    icon: Waves,
    tone: 'info',
    hint: 'A sea kept liquid beneath an ice crust',
  },
  hollow_interior: {
    label: 'Hollow interior',
    icon: Globe,
    tone: 'gold',
    hint: 'The inner surface of a hollow world',
  },
  reservoir: {
    label: 'Reservoir',
    icon: Droplet,
    tone: 'warning',
    hint: 'A trap of fuel or brine under a sealing layer',
  },
  permafrost_layer: {
    label: 'Frozen ground',
    icon: Snowflake,
    tone: 'info',
    hint: 'Ground frozen through the year beneath cold land',
  },
  fault_zone: {
    label: 'Fault zone',
    icon: Mountain,
    tone: 'danger',
    hint: 'Where stress gathers until the ground shakes',
  },
}

export const GRADE: Record<Schema['BuildingGrade'], Named> = {
  plain: { label: 'Plain stone', icon: Box, tone: 'muted' },
  fine: { label: 'Fine stone', icon: Gem, tone: 'info' },
  splendid: { label: 'Splendid stone', icon: Sparkles, tone: 'gold' },
}

export const PASSAGE_KIND: Record<Schema['DeepPassageKind'], Named> = {
  level: { label: 'Level passage', icon: MoveHorizontal, tone: 'info' },
  vertical: {
    label: 'Vertical passage',
    icon: MoveVertical,
    tone: 'verdigris',
  },
  opening: { label: 'Opening to the surface', icon: DoorOpen, tone: 'gold' },
}

export const PASSAGE_STATE: Record<Schema['DeepPassageState'], Named> = {
  digging: { label: 'Being dug', icon: Pickaxe, tone: 'warning' },
  open: { label: 'Open', icon: DoorOpen, tone: 'success' },
  flooded: { label: 'Flooded', icon: Waves, tone: 'info' },
  collapsed: { label: 'Collapsed', icon: Mountain, tone: 'danger' },
  sealed: { label: 'Sealed', icon: Lock, tone: 'muted' },
}

export const PASSAGE_ORIGIN: Record<Schema['DeepPassageOrigin'], Named> = {
  natural: { label: 'Formed with the world', icon: Globe, tone: 'muted' },
  dug: { label: 'Dug by a people', icon: Pickaxe, tone: 'gold' },
  breach: { label: 'Broken open', icon: Zap, tone: 'danger' },
  divine: { label: 'Made by a god', icon: Sparkles, tone: 'gold' },
}
