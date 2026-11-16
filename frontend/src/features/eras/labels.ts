import {
  Ban,
  Castle,
  Church,
  CircleCheck,
  CircleX,
  CloudFog,
  Crosshair,
  Factory,
  FlaskConical,
  Footprints,
  Gauge,
  Hammer,
  HeartPulse,
  type LucideIcon,
  Megaphone,
  Package,
  PencilRuler,
  Pickaxe,
  RadioTower,
  Rocket,
  Ship,
  Skull,
  Sparkles,
  Wheat,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'
import {
  TECHNOLOGY_HINT,
  TECHNOLOGY_ICON,
} from '@/features/onboarding/wizardVisuals'

type Schema = components['schemas']

export const TECH_ERAS_ICON: LucideIcon = Gauge

export const TAB_ICONS = {
  era: Gauge,
  ladder: FlaskConical,
  programmes: PencilRuler,
} as const

const ERA_NAMES: Record<Schema['TechnologyEra'], [string, Named['tone']]> = {
  stone: ['Stone', 'muted'],
  bronze: ['Bronze', 'warning'],
  iron: ['Iron', 'muted'],
  medieval: ['Medieval', 'verdigris'],
  gunpowder: ['Gunpowder', 'danger'],
  renaissance: ['Renaissance', 'gold'],
  steam: ['Steam', 'warning'],
  electrical: ['Electrical', 'info'],
  information: ['Information', 'info'],
  advanced: ['Advanced', 'danger'],
  interstellar: ['Interstellar', 'gold'],
  beyond: ['Beyond', 'verdigris'],
}

export const ERAS = Object.fromEntries(
  Object.entries(ERA_NAMES).map(([key, [label, tone]]) => [
    key,
    {
      label,
      tone,
      icon: TECHNOLOGY_ICON[key as Schema['TechnologyEra']],
      hint: TECHNOLOGY_HINT[key as Schema['TechnologyEra']],
    },
  ])
) as Record<Schema['TechnologyEra'], Named & { hint: string }>

export const CHANNELS: Record<Schema['EraChannel'], Named & { unit: string }> =
  {
    farming: { label: 'Harvests', icon: Wheat, tone: 'success', unit: '%' },
    mining: { label: 'Mining', icon: Pickaxe, tone: 'muted', unit: '%' },
    industry: { label: 'Industry', icon: Factory, tone: 'gold', unit: '%' },
    disease: {
      label: 'Deaths from sickness spared',
      icon: HeartPulse,
      tone: 'success',
      unit: '%',
    },
    messages: {
      label: 'Message reach',
      icon: RadioTower,
      tone: 'info',
      unit: ' regions',
    },
    march: {
      label: 'Army march',
      icon: Footprints,
      tone: 'warning',
      unit: ' regions',
    },
    sea_routes: { label: 'Sea routes', icon: Ship, tone: 'info', unit: '%' },
    world_routes: {
      label: 'Routes between worlds',
      icon: Rocket,
      tone: 'verdigris',
      unit: '%',
    },
    fortification: { label: 'Walls', icon: Castle, tone: 'muted', unit: '%' },
    pollution: {
      label: 'Pollution',
      icon: CloudFog,
      tone: 'danger',
      unit: '%',
    },
    opinion: {
      label: 'Speed of opinion',
      icon: Megaphone,
      tone: 'info',
      unit: '%',
    },
    research: {
      label: 'Research',
      icon: FlaskConical,
      tone: 'gold',
      unit: '%',
    },
    secularisation: {
      label: 'Secularisation',
      icon: Church,
      tone: 'warning',
      unit: '%',
    },
    firepower: {
      label: 'Missile strength',
      icon: Crosshair,
      tone: 'danger',
      unit: '%',
    },
    rites: {
      label: 'Power rites lose',
      icon: Sparkles,
      tone: 'warning',
      unit: '%',
    },
    spoilage: {
      label: 'Spoilage spared',
      icon: Package,
      tone: 'success',
      unit: '%',
    },
    doom: { label: 'Doom each epoch', icon: Skull, tone: 'danger', unit: '' },
  }

export const STAGES: Record<Schema['ProgrammeStage'], Named> = {
  planning: { label: 'Planning', icon: PencilRuler, tone: 'info' },
  building: { label: 'Building', icon: Hammer, tone: 'gold' },
  testing: { label: 'Testing', icon: FlaskConical, tone: 'warning' },
  complete: { label: 'Complete', icon: CircleCheck, tone: 'success' },
  abandoned: { label: 'Abandoned', icon: CircleX, tone: 'muted' },
}

export const BARRED_ICON: LucideIcon = Ban
