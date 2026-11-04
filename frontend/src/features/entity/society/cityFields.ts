import {
  Church,
  Coins,
  Droplets,
  Gavel,
  House,
  ScrollText,
  Ship,
  Siren,
  Users,
  Warehouse,
  Wheat,
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import type { KpiTone } from '@/components/domain'

type Effects = components['schemas']['DistrictEffectsView']
export type DesignKey = keyof Effects

export const DESIGN_FIELDS: {
  key: DesignKey
  icon: LucideIcon
  tone: KpiTone
  unit: string
  signed?: boolean
}[] = [
  { key: 'housing', icon: House, tone: 'info', unit: 'people' },
  { key: 'food_store', icon: Wheat, tone: 'success', unit: 'measures' },
  { key: 'goods_store', icon: Warehouse, tone: 'gold', unit: 'loads' },
  { key: 'harbour', icon: Ship, tone: 'info', unit: 'ships' },
  { key: 'order', icon: Gavel, tone: 'verdigris', unit: 'order' },
  {
    key: 'sanitation',
    icon: Droplets,
    tone: 'info',
    unit: 'sanitation',
    signed: true,
  },
  { key: 'piety_floor', icon: Church, tone: 'gold', unit: 'piety' },
  { key: 'admin_pct', icon: ScrollText, tone: 'verdigris', unit: '%' },
  { key: 'policing', icon: Siren, tone: 'danger', unit: 'crime' },
  { key: 'investment_pct', icon: Coins, tone: 'gold', unit: '%' },
  { key: 'tension_relief_pct', icon: Users, tone: 'success', unit: '%' },
]

export const DESIGN_LIMIT: Record<DesignKey, [number, number]> = {
  housing: [0, 1000000000],
  food_store: [0, 1000000000],
  goods_store: [0, 1000000000],
  harbour: [0, 1000000000],
  order: [0, 300],
  sanitation: [-100, 300],
  piety_floor: [0, 300],
  admin_pct: [0, 300],
  policing: [0, 300],
  investment_pct: [0, 300],
  tension_relief_pct: [0, 300],
}

export function signed(value: number): string {
  return `${value > 0 ? '+' : ''}${formatInteger(value)}`
}
