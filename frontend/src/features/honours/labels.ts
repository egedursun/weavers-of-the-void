import {
  Award,
  Castle,
  CircleSlash,
  Flag,
  Home,
  type LucideIcon,
  Medal,
  Coins,
  Shield,
  Skull,
  Swords,
  Users,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const HONOURS_ICON: LucideIcon = Medal

export const TAB_ICONS = {
  units: Flag,
  veterans: Users,
} as const

export const HONOURS: Record<Schema['UnitHonourKind'], Named> = {
  victory: { label: 'Victory', icon: Award, tone: 'gold' },
  stand: { label: 'A stand held', icon: Shield, tone: 'info' },
  siege: { label: 'A siege won', icon: Castle, tone: 'warning' },
  survival: { label: 'Survived', icon: Swords, tone: 'muted' },
  massacre: { label: 'Massacre suffered', icon: Skull, tone: 'danger' },
}

export const GRANTS: Record<Schema['VeteranGrant'], Named> = {
  land: { label: 'Land in a colony', icon: Home, tone: 'success' },
  pension: { label: 'Pensions', icon: Coins, tone: 'gold' },
  none: { label: 'Nothing', icon: CircleSlash, tone: 'muted' },
}
