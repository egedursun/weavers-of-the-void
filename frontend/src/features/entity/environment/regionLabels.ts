import {
  Biohazard,
  Bug,
  Building2,
  Castle,
  CircleDashed,
  CloudRain,
  Compass,
  Crown,
  DoorOpen,
  Flag,
  Flame,
  Footprints,
  Ghost,
  HandHeart,
  Handshake,
  Landmark,
  Link2,
  Mountain,
  MountainSnow,
  PawPrint,
  Pickaxe,
  Ship,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Swords,
  Thermometer,
  Waves,
  Wheat,
  Wind,
  Zap,
  Droplets,
  Gem,
  ThermometerSnowflake,
  WavesLadder,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import type { KpiTone } from '@/components/domain'
import type { Named } from './labels'

type Schema = components['schemas']

export const DANGER_SOURCE: Record<
  Schema['DangerSource'],
  Named & { hint: string }
> = {
  beasts: {
    label: 'Beasts',
    icon: PawPrint,
    tone: 'warning',
    hint: 'Fierce wild kinds and named beasts with their lairs here',
  },
  bandits: {
    label: 'Bandits',
    icon: Swords,
    tone: 'danger',
    hint: 'Outlaws, deserters and lawless land no realm controls',
  },
  monsters: {
    label: 'Monsters',
    icon: Skull,
    tone: 'danger',
    hint: 'The most dangerous kinds of the world stalk this land',
  },
  phenomena: {
    label: 'Phenomena',
    icon: Ghost,
    tone: 'verdigris',
    hint: 'Hauntings, leak wounds, blight, wild magic and dark memories',
  },
  disease: {
    label: 'Disease',
    icon: Biohazard,
    tone: 'warning',
    hint: 'Fevers from a sick land and old plague ground',
  },
  avalanche: {
    label: 'Avalanches',
    icon: MountainSnow,
    tone: 'info',
    hint: 'Snow slopes in cold, rough country',
  },
  quicksand: {
    label: 'Quicksand',
    icon: Waves,
    tone: 'muted',
    hint: 'Sucking ground in marsh, wetland and desert sand',
  },
  volcanic: {
    label: 'Volcanic ground',
    icon: Flame,
    tone: 'danger',
    hint: 'Fumes, fire and craters of volcanic land',
  },
  landslide: {
    label: 'Landslides',
    icon: Mountain,
    tone: 'warning',
    hint: 'Rough wet slopes, eroded or stripped of their woods',
  },
  exposure: {
    label: 'Exposure',
    icon: Thermometer,
    tone: 'info',
    hint: 'Warmth beyond what the unsheltered can bear',
  },
  currents: {
    label: 'Currents',
    icon: Droplets,
    tone: 'info',
    hint: 'Strong rivers and coasts that drag people down',
  },
  toxic_ground: {
    label: 'Toxic ground',
    icon: Biohazard,
    tone: 'danger',
    hint: 'Fumes, poisoned ground and marsh gases',
  },
  lightning: {
    label: 'Lightning',
    icon: Zap,
    tone: 'warning',
    hint: 'Open ground under heavy storms',
  },
  sinkhole: {
    label: 'Sinkholes',
    icon: CircleDashed,
    tone: 'warning',
    hint: 'Hollow karst ground that gives way',
  },
  rockfall: {
    label: 'Rockfall',
    icon: MountainSnow,
    tone: 'warning',
    hint: 'Loose stone on high rough ground',
  },
}

export const HARM: Record<Schema['DangerHarm'], Named> = {
  settlers: { label: 'Settlers', icon: Castle, tone: 'danger' },
  livestock: { label: 'Livestock', icon: Wheat, tone: 'warning' },
  travellers: { label: 'Travellers', icon: Mountain, tone: 'info' },
  armies: { label: 'Armies', icon: Swords, tone: 'danger' },
  ambush: { label: 'Ambush', icon: Zap, tone: 'warning' },
  merchants: { label: 'Merchants', icon: Crown, tone: 'gold' },
  crops: { label: 'Crops', icon: Sprout, tone: 'warning' },
  vessels: { label: 'Vessels', icon: Ship, tone: 'info' },
  structures: { label: 'Buildings', icon: Building2, tone: 'warning' },
  pilgrims: { label: 'Pilgrims', icon: Footprints, tone: 'gold' },
  workers: { label: 'Workers at their work', icon: Pickaxe, tone: 'warning' },
}

export const ORIGIN: Record<string, { label: string; tone: BadgeTone }> = {
  derived: { label: 'Bred by the land', tone: 'secondary' },
  player: { label: 'Set by your hand', tone: 'info' },
  divine: { label: 'A god’s curse', tone: 'warning' },
}

export type BadgeTone =
  'secondary' | 'info' | 'success' | 'warning' | 'destructive' | 'default'

export const MEMORY: Record<Schema['RegionMemoryKind'], Named> = {
  battle: { label: 'Battle', icon: Swords, tone: 'warning' },
  massacre: { label: 'Massacre', icon: Skull, tone: 'danger' },
  sack: { label: 'Sack', icon: Flame, tone: 'danger' },
  disaster: { label: 'Disaster', icon: CloudRain, tone: 'warning' },
  plague: { label: 'Plague', icon: Bug, tone: 'danger' },
  famine: { label: 'Famine', icon: Wheat, tone: 'warning' },
  god_death: { label: 'A god fell here', icon: Crown, tone: 'gold' },
  saint_burial: { label: 'Saint’s grave', icon: HandHeart, tone: 'success' },
  miracle: { label: 'Miracle', icon: Sparkles, tone: 'gold' },
  founding: { label: 'Founding', icon: Landmark, tone: 'gold' },
  treaty: { label: 'Treaty', icon: Handshake, tone: 'success' },
  expulsion: { label: 'Expulsion', icon: DoorOpen, tone: 'danger' },
  discovery: { label: 'Discovery', icon: Compass, tone: 'info' },
  uprising: { label: 'Uprising', icon: Flag, tone: 'warning' },
  union: { label: 'Union', icon: Link2, tone: 'success' },
  accession: { label: 'Accession to rule', icon: Gem, tone: 'gold' },
}

export const HAZARD: Record<
  Schema['TerrainHazard'],
  Named & { season: string }
> = {
  avalanche: {
    label: 'Avalanche',
    icon: MountainSnow,
    tone: 'info',
    season: 'in the coldest season',
  },
  spring_flood: {
    label: 'Spring flood',
    icon: Waves,
    tone: 'info',
    season: 'in the wettest season',
  },
  wildfire: {
    label: 'Wildfire',
    icon: Flame,
    tone: 'danger',
    season: 'in the hottest season',
  },
  whiteout: {
    label: 'Whiteout',
    icon: Snowflake,
    tone: 'info',
    season: 'in the coldest season',
  },
  mudslide: {
    label: 'Mudslide',
    icon: Mountain,
    tone: 'warning',
    season: 'in the wettest season',
  },
  flash_flood: {
    label: 'Flash flood',
    icon: WavesLadder,
    tone: 'danger',
    season: 'in the wettest season',
  },
  thin_ice: {
    label: 'Thin ice',
    icon: ThermometerSnowflake,
    tone: 'info',
    season: 'in the warming season',
  },
  ice_jam: {
    label: 'Ice jam',
    icon: Thermometer,
    tone: 'warning',
    season: 'in the warming season',
  },
  storm_surge: {
    label: 'Storm surge',
    icon: Zap,
    tone: 'danger',
    season: 'in the stormiest season',
  },
  dust_storm: {
    label: 'Dust storm',
    icon: Wind,
    tone: 'warning',
    season: 'in the driest season',
  },
}

const DANGER_HIGH = 60
const DANGER_MID = 30

export function dangerTone(value: number): KpiTone {
  if (value >= DANGER_HIGH) return 'danger'
  if (value >= DANGER_MID) return 'warning'
  return value > 0 ? 'gold' : 'success'
}

export function sacredTone(value: number, threshold: number): KpiTone {
  if (value >= threshold) return 'gold'
  return value > 0 ? 'verdigris' : 'muted'
}
