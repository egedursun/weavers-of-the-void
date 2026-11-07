import {
  Building2,
  Church,
  Coins,
  Flag,
  Hammer,
  Landmark,
  Megaphone,
  Shield,
  Users,
  Vote,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const ESTATES_ICON = Landmark
export const MOVEMENT_ICON = Megaphone
export const PARTY_ICON = Vote
export const COMPANY_ICON = Building2
export const ORDER_ICON = Church
export const GUILD_ICON = Hammer
export const SHARE_ICON = Coins

export const PRIVILEGE_ICONS: Record<string, Named> = {
  tax_exemption: { label: 'Freedom from taxes', icon: Coins, tone: 'gold' },
  monopoly: { label: 'A monopoly', icon: Building2, tone: 'warning' },
  council_seat: { label: 'A seat in council', icon: Users, tone: 'info' },
  arms: { label: 'The right to bear arms', icon: Shield, tone: 'danger' },
  judicial_immunity: {
    label: 'Immunity from the courts',
    icon: Flag,
    tone: 'verdigris',
  },
}

export function loyaltyTone(loyalty: number): Named['tone'] {
  if (loyalty >= 60) return 'success'
  if (loyalty <= 30) return 'danger'
  return 'warning'
}
