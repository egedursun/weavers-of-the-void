import {
  Building2,
  Factory,
  GraduationCap,
  HandHeart,
  HeartPulse,
  Home,
  Landmark,
  type LucideIcon,
  Store,
  Theater,
  Trees,
  Trophy,
  Wheat,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }
export type ZoneSpec = Named & {
  token: string
  fill: string
  hint: string
}

export const CITY_ICON: LucideIcon = Building2

export const ZONES: Record<Schema['ZoneKind'], ZoneSpec> = {
  governance: {
    label: 'Governance',
    icon: Landmark,
    tone: 'gold',
    token: '--zone-governance',
    fill: 'fill-zone-governance',
    hint: 'Palaces, citadels, courts, walls and public works',
  },
  residential: {
    label: 'Residential',
    icon: Home,
    tone: 'success',
    token: '--zone-residential',
    fill: 'fill-zone-residential',
    hint: 'Homes at their housing level, and the slums',
  },
  commercial: {
    label: 'Commercial',
    icon: Store,
    tone: 'info',
    token: '--zone-commercial',
    fill: 'fill-zone-commercial',
    hint: 'Markets, harbours, warehouses, banks and foreign quarters',
  },
  industrial: {
    label: 'Industrial',
    icon: Factory,
    tone: 'warning',
    token: '--zone-industrial',
    fill: 'fill-zone-industrial',
    hint: 'Forges, tanneries, mines, workshops and shipyards',
  },
  agricultural: {
    label: 'Agricultural',
    icon: Wheat,
    tone: 'gold',
    token: '--zone-agricultural',
    fill: 'fill-zone-agricultural',
    hint: 'Fields, granaries, mills, irrigation and dams',
  },
  civic: {
    label: 'Civic',
    icon: GraduationCap,
    tone: 'verdigris',
    token: '--zone-civic',
    fill: 'fill-zone-civic',
    hint: 'Education, health, sports, culture and social services',
  },
  green: {
    label: 'Green',
    icon: Trees,
    tone: 'success',
    token: '--zone-green',
    fill: 'fill-zone-green',
    hint: 'Gardens, parks and fountains',
  },
}

export const CIVIC: Record<Schema['CivicService'], Named> = {
  education: { label: 'Education', icon: GraduationCap, tone: 'info' },
  health: { label: 'Health', icon: HeartPulse, tone: 'success' },
  sports: { label: 'Sports', icon: Trophy, tone: 'warning' },
  culture: { label: 'Culture', icon: Theater, tone: 'gold' },
  social: { label: 'Social services', icon: HandHeart, tone: 'verdigris' },
}

export const GROUNDS: Record<Schema['LandGround'], string> = {
  water: 'Water',
  shore: 'Shore',
  lowland: 'Lowland',
  wetland: 'Wet lowland',
  hills: 'Hills',
  mountains: 'Mountains',
  peaks: 'Peaks',
}

export const COVERS: Record<Schema['LandCover'], string> = {
  open: 'Open ground',
  forest: 'Forest',
  fields: 'Fields',
  pasture: 'Pasture',
  marsh: 'Marsh',
  cleared: 'Cleared ground',
  built: 'Built ground',
  mined: 'Diggings',
}

export const STATES: Record<Schema['ConstructionState'], string> = {
  planned: 'Planned',
  building: 'Being built',
  complete: 'Standing',
  damaged: 'Damaged',
  ruined: 'In ruins',
}

export const GROUND_FILL: Record<Schema['LandGround'], string> = {
  water: 'fill-land-water',
  shore: 'fill-land-shore',
  lowland: 'fill-land-lowland',
  wetland: 'fill-land-wetland',
  hills: 'fill-land-hills',
  mountains: 'fill-land-mountains',
  peaks: 'fill-land-peaks',
}

export type LandTexture =
  | 'trees'
  | 'furrows'
  | 'grass'
  | 'reeds'
  | 'stubble'
  | 'blocks'
  | 'spoil'
  | 'ridges'
  | 'snow'
  | 'swell'

export const GROUND_RELIEF: Record<Schema['LandGround'], LandTexture | null> = {
  water: 'swell',
  shore: null,
  lowland: null,
  wetland: 'reeds',
  hills: 'ridges',
  mountains: 'ridges',
  peaks: 'snow',
}

export const COVER_TEXTURE: Record<Schema['LandCover'], LandTexture | null> = {
  open: null,
  forest: 'trees',
  fields: 'furrows',
  pasture: 'grass',
  marsh: 'reeds',
  cleared: 'stubble',
  built: 'blocks',
  mined: 'spoil',
}

export const COVER_FILL: Record<Schema['LandCover'], string> = {
  open: 'fill-land-lowland',
  forest: 'fill-land-forest',
  fields: 'fill-land-fields',
  pasture: 'fill-land-pasture',
  marsh: 'fill-land-marsh',
  cleared: 'fill-land-cleared',
  built: 'fill-land-built',
  mined: 'fill-land-mined',
}
