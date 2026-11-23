import {
  Bone,
  Box,
  CircleDot,
  Droplets,
  Flame,
  Gem,
  Globe,
  HeartPulse,
  Layers,
  Mountain,
  MountainSnow,
  Pickaxe,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Waves,
  Wind,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import type { Named } from './labels'

type Schema = components['schemas']

export const ROCK: Record<Schema['RockKind'], Named> = {
  soil: { label: 'Soil', icon: Sprout, tone: 'success' },
  clay: { label: 'Clay', icon: CircleDot, tone: 'gold' },
  sand: { label: 'Sand', icon: Wind, tone: 'warning' },
  limestone: { label: 'Limestone', icon: Layers, tone: 'muted' },
  sandstone: { label: 'Sandstone', icon: Layers, tone: 'gold' },
  shale: { label: 'Shale', icon: Layers, tone: 'muted' },
  granite: { label: 'Granite', icon: Mountain, tone: 'muted' },
  basalt: { label: 'Basalt', icon: Mountain, tone: 'info' },
  marble: { label: 'Marble', icon: Gem, tone: 'gold' },
  obsidian: { label: 'Obsidian', icon: Gem, tone: 'verdigris' },
  slate: { label: 'Slate', icon: Layers, tone: 'info' },
  crystal_bedrock: { label: 'Crystal bedrock', icon: Sparkles, tone: 'info' },
  frozen_methane: { label: 'Frozen methane', icon: Snowflake, tone: 'info' },
  bone: { label: 'Bone', icon: Bone, tone: 'muted' },
  glass: { label: 'Glass', icon: Gem, tone: 'info' },
  halite: { label: 'Halite', icon: Box, tone: 'muted' },
  coal: { label: 'Coal', icon: Flame, tone: 'warning' },
  chalk: { label: 'Chalk', icon: CircleDot, tone: 'muted' },
  tuff: { label: 'Tuff', icon: Mountain, tone: 'gold' },
  gneiss: { label: 'Gneiss', icon: MountainSnow, tone: 'gold' },
  quartzite: { label: 'Quartzite', icon: Gem, tone: 'muted' },
  water_ice: { label: 'Water ice', icon: Snowflake, tone: 'info' },
  iron: { label: 'Iron crust', icon: Pickaxe, tone: 'warning' },
  carbon: { label: 'Carbon crust', icon: Gem, tone: 'muted' },
  living_tissue: { label: 'Living tissue', icon: HeartPulse, tone: 'danger' },
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
    icon: Layers,
    tone: 'verdigris',
    hint: 'Deeper hollows under rough country',
  },
  cavern_deep: {
    label: 'Deep caverns',
    icon: Layers,
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
    icon: Droplets,
    tone: 'warning',
    hint: 'A trap of fuel or brine under a sealing layer',
  },
}

export const GRADE: Record<Schema['BuildingGrade'], Named> = {
  plain: { label: 'Plain stone', icon: Box, tone: 'muted' },
  fine: { label: 'Fine stone', icon: Gem, tone: 'info' },
  splendid: { label: 'Splendid stone', icon: Sparkles, tone: 'gold' },
}
