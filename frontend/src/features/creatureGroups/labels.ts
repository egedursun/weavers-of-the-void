import { Bird, Bug, Cat, Hexagon, PawPrint, Rabbit, Users } from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const GROUP_FORM: Record<Schema['GroupForm'], Named> = {
  pack: { label: 'Pack', icon: PawPrint, tone: 'danger' },
  herd: { label: 'Herd', icon: Rabbit, tone: 'success' },
  colony: { label: 'Colony', icon: Bug, tone: 'warning' },
  hive: { label: 'Hive', icon: Hexagon, tone: 'danger' },
  troop: { label: 'Troop', icon: Users, tone: 'warning' },
  flock: { label: 'Flock', icon: Bird, tone: 'info' },
  solitary_range: { label: 'Lone range', icon: Cat, tone: 'muted' },
}
