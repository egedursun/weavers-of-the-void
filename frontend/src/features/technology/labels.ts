import {
  Atom,
  Brain,
  Building2,
  Cpu,
  HeartPulse,
  Landmark,
  Pickaxe,
  RadioTower,
  Rocket,
  Sprout,
  Swords,
  TrainFront,
  Wheat,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

export const TECHNOLOGY_ICON = Atom

export const FAMILIES: Record<components['schemas']['TechFamily'], Named> = {
  agriculture: { label: 'Agriculture', icon: Wheat, tone: 'success' },
  materials: { label: 'Materials', icon: Pickaxe, tone: 'muted' },
  energy: { label: 'Energy', icon: Atom, tone: 'warning' },
  transport: { label: 'Transport', icon: TrainFront, tone: 'info' },
  communication: { label: 'Communication', icon: RadioTower, tone: 'info' },
  medicine: { label: 'Medicine', icon: HeartPulse, tone: 'success' },
  warfare: { label: 'Warfare', icon: Swords, tone: 'danger' },
  computation: { label: 'Computation', icon: Cpu, tone: 'verdigris' },
  life: { label: 'Living craft', icon: Sprout, tone: 'success' },
  construction: { label: 'Construction', icon: Building2, tone: 'muted' },
  administration: { label: 'Administration', icon: Landmark, tone: 'gold' },
  space: { label: 'Space', icon: Rocket, tone: 'gold' },
  mind: { label: 'Minds', icon: Brain, tone: 'verdigris' },
}
