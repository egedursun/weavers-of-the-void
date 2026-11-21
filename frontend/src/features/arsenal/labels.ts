import {
  Biohazard,
  Bomb,
  Bot,
  Ghost,
  Orbit,
  Radiation,
  Skull,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const REMNANT_KIND: Record<Schema['RemnantKind'], Named> = {
  buried_charges: { label: 'Buried charges', icon: Bomb, tone: 'danger' },
  poisoned_ground: {
    label: 'Poisoned ground',
    icon: Biohazard,
    tone: 'danger',
  },
  fallout: { label: 'Fallout', icon: Radiation, tone: 'danger' },
  wreck_field: { label: 'Field of wrecks', icon: Orbit, tone: 'warning' },
  unquiet_dead: { label: 'Unquiet dead', icon: Ghost, tone: 'verdigris' },
  cursed_ground: { label: 'Cursed ground', icon: Skull, tone: 'verdigris' },
  abandoned_machines: {
    label: 'Abandoned machines',
    icon: Bot,
    tone: 'warning',
  },
}
