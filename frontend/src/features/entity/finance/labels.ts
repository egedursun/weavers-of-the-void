import {
  Ban,
  Coins,
  HandCoins,
  Landmark,
  ChartLine,
  Route,
  Scale,
  Warehouse,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const FINANCE_ICON = Landmark
export const CREDIT_ICON = Scale
export const HOARD_ICON = Warehouse
export const INDICATOR_ICON = ChartLine
export const ACCESS_ICON = Route
export const COIN_ICON = Coins

export const POLICIES: Record<string, Named> = {
  tariff: { label: 'Tariff', icon: HandCoins, tone: 'warning' },
  subsidy: { label: 'Subsidy', icon: Coins, tone: 'success' },
  embargo: { label: 'Embargo', icon: Ban, tone: 'danger' },
}

export const CREDIT_TONE: Record<string, Named['tone']> = {
  normal: 'success',
  strained: 'warning',
  default: 'danger',
  restructuring: 'info',
}

export const HOARD_TONE: Record<string, Named['tone']> = {
  hoarding: 'warning',
  sold: 'success',
  bust: 'danger',
}
