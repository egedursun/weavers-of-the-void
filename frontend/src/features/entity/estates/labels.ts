import {
  Building2,
  Church,
  Coins,
  Flag,
  Hammer,
  Landmark,
  MapPinned,
  Megaphone,
  Shield,
  Users,
  Vote,
  ShieldOff,
  Shirt,
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
  dress: { label: 'Dress of their rank', icon: Shirt, tone: 'gold' },
  service_exemption: {
    label: 'Freedom from service',
    icon: ShieldOff,
    tone: 'info',
  },
  tax_exemption: { label: 'Freedom from taxes', icon: Coins, tone: 'gold' },
  monopoly: { label: 'A monopoly', icon: Building2, tone: 'warning' },
  council_seat: { label: 'A seat in council', icon: Users, tone: 'info' },
  arms: { label: 'The right to bear arms', icon: Shield, tone: 'danger' },
  judicial_immunity: {
    label: 'Immunity from the courts',
    icon: Flag,
    tone: 'verdigris',
  },
  reserved_offices: {
    label: 'Offices kept for it',
    icon: Landmark,
    tone: 'gold',
  },
  land_holding: {
    label: 'Sole right to hold land',
    icon: MapPinned,
    tone: 'warning',
  },
}

export function loyaltyTone(loyalty: number): Named['tone'] {
  if (loyalty >= 60) return 'success'
  if (loyalty <= 30) return 'danger'
  return 'warning'
}
