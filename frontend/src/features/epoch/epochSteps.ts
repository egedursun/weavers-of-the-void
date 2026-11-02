import {
  Cog,
  Crown,
  type LucideIcon,
  Scale,
  Sunrise,
  Users,
} from 'lucide-react'

export type PipelineStep = {
  no: number
  label: string
  icon: LucideIcon
}

export const EPOCH_STEPS: PipelineStep[] = [
  { no: 1, label: 'Sons act', icon: Crown },
  { no: 2, label: 'Mortals act', icon: Users },
  { no: 3, label: 'World engine', icon: Cog },
  { no: 4, label: 'Fate judges', icon: Scale },
  { no: 5, label: 'New epoch', icon: Sunrise },
]

export function stepLabel(no: number | string): string {
  const found = EPOCH_STEPS.find((step) => String(step.no) === String(no))
  return found ? found.label : `Phase ${no}`
}
