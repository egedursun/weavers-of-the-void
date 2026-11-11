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
export type ZoneSpec = Named & { token: string; fill: string; hint: string }

export const CITY_ICON: LucideIcon = Building2

export const ZONES: Record<Schema['ZoneKind'], ZoneSpec> = {
  governance: {
    label: 'Governance',
    icon: Landmark,
    tone: 'gold',
    token: '--brand-gold',
    fill: 'fill-brand-gold',
    hint: 'Palaces, citadels, courts, walls and public works',
  },
  residential: {
    label: 'Residential',
    icon: Home,
    tone: 'success',
    token: '--success',
    fill: 'fill-success',
    hint: 'Homes at their housing level, and the slums',
  },
  commercial: {
    label: 'Commercial',
    icon: Store,
    tone: 'info',
    token: '--info',
    fill: 'fill-info',
    hint: 'Markets, harbours, warehouses, banks and foreign quarters',
  },
  industrial: {
    label: 'Industrial',
    icon: Factory,
    tone: 'warning',
    token: '--warning',
    fill: 'fill-warning',
    hint: 'Forges, tanneries, mines, workshops and shipyards',
  },
  agricultural: {
    label: 'Agricultural',
    icon: Wheat,
    tone: 'gold',
    token: '--chart-4',
    fill: 'fill-chart-4',
    hint: 'Fields, granaries, mills, irrigation and dams',
  },
  civic: {
    label: 'Civic',
    icon: GraduationCap,
    tone: 'verdigris',
    token: '--brand-verdigris',
    fill: 'fill-brand-verdigris',
    hint: 'Education, health, sports, culture and social services',
  },
  green: {
    label: 'Green',
    icon: Trees,
    tone: 'success',
    token: '--chart-2',
    fill: 'fill-chart-2',
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
  water: 'fill-brand-azure',
  shore: 'fill-chart-4',
  lowland: 'fill-chart-2',
  wetland: 'fill-brand-verdigris',
  hills: 'fill-chart-3',
  mountains: 'fill-muted-foreground',
  peaks: 'fill-muted',
}

export const COVER_FILL: Record<Schema['LandCover'], string> = {
  open: 'fill-chart-2',
  forest: 'fill-success',
  fields: 'fill-brand-gold',
  pasture: 'fill-chart-4',
  marsh: 'fill-brand-verdigris',
  cleared: 'fill-warning',
  built: 'fill-chart-5',
  mined: 'fill-destructive',
}
