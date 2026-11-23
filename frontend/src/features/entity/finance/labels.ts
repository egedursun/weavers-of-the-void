import {
  ShieldBan,
  PackageX,
  Handshake,
  ScrollText,
  Gauge,
  Ban,
  Coins,
  HandCoins,
  Landmark,
  ChartLine,
  Route,
  Scale,
  Warehouse,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'

export const FINANCE_ICON = Landmark
export const CREDIT_ICON = Scale
export const HOARD_ICON = Warehouse
export const INDICATOR_ICON = ChartLine
export const ACCESS_ICON = Route
export const COIN_ICON = Coins

export const POLICIES: Record<components['schemas']['TradePolicyKind'], Named> =
  {
    tariff: { label: 'Tariff', icon: HandCoins, tone: 'warning' },
    subsidy: { label: 'Subsidy', icon: Coins, tone: 'success' },
    embargo: { label: 'Embargo', icon: Ban, tone: 'danger' },
    quota: { label: 'Quota on imports', icon: Gauge, tone: 'warning' },
    licence: {
      label: 'Licence fee on imports',
      icon: ScrollText,
      tone: 'warning',
    },
    price_control: { label: 'Price ceiling', icon: Scale, tone: 'info' },
    free_trade: {
      label: 'Free trade, no tariffs both ways',
      icon: Handshake,
      tone: 'success',
    },
    export_ban: { label: 'Ban on exports', icon: PackageX, tone: 'danger' },
    sanction: {
      label: 'Sanction against a realm',
      icon: ShieldBan,
      tone: 'danger',
    },
  }

export const CREDIT_TONE: Record<string, Named['tone']> = {
  normal: 'success',
  strained: 'warning',
  default: 'danger',
  restructuring: 'info',
  rescued: 'verdigris',
  repudiated: 'danger',
}

export const HOARD_TONE: Record<string, Named['tone']> = {
  hoarding: 'warning',
  sold: 'success',
  bust: 'danger',
  seized: 'info',
}
