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
  ShieldCheck,
  Waves,
  Crown,
  Receipt,
  BadgeCheck,
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
  relief: { label: 'A siege relieved', icon: ShieldCheck, tone: 'success' },
  crossing: { label: 'A crossing under arms', icon: Waves, tone: 'info' },
}

export const GRANTS: Record<Schema['VeteranGrant'], Named> = {
  land: { label: 'Land in a colony', icon: Home, tone: 'success' },
  pension: { label: 'Pensions', icon: Coins, tone: 'gold' },
  none: { label: 'Nothing', icon: CircleSlash, tone: 'muted' },
  membership: { label: 'Full membership', icon: BadgeCheck, tone: 'info' },
  title: { label: 'A lesser title', icon: Crown, tone: 'gold' },
  tax_exemption: {
    label: 'Freedom from taxes',
    icon: Receipt,
    tone: 'verdigris',
  },
}
