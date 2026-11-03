import {
  Anchor,
  Axe,
  Beer,
  Bird,
  Box,
  Castle,
  Coins,
  Factory,
  FlaskConical,
  Flame,
  Gem,
  Hammer,
  HandCoins,
  Landmark,
  Mountain,
  Package,
  Pickaxe,
  Ship,
  Shirt,
  Shield,
  Sparkles,
  Store,
  Swords,
  Tent,
  Trees,
  Warehouse,
  Wheat,
  Wind,
  Fish,
  Beef,
  Croissant,
  Sprout,
  Wrench,
  Cross,
  PawPrint,
  Footprints,
  Waves,
  Route,
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'

type Schemas = components['schemas']
export type CommodityKind = Schemas['CommodityKind']
export type WorkshopKind = Schemas['WorkshopKind']
export type TradeMode = Schemas['TradeMode']
export type TradeRouteStatus = Schemas['TradeRouteStatus']
export type MaterialFamily = Schemas['MaterialFamily']

export const COMMODITY: Record<
  CommodityKind,
  { label: string; icon: LucideIcon }
> = {
  grain: { label: 'Grain', icon: Wheat },
  livestock: { label: 'Livestock', icon: Beef },
  fish: { label: 'Fish', icon: Fish },
  fodder: { label: 'Fodder', icon: Sprout },
  timber: { label: 'Timber', icon: Trees },
  fuel: { label: 'Fuel', icon: Flame },
  bread: { label: 'Bread', icon: Croissant },
  ore: { label: 'Ore', icon: Mountain },
  stone: { label: 'Stone', icon: Box },
  cloth: { label: 'Cloth', icon: Shirt },
  tools: { label: 'Tools', icon: Wrench },
  weapons: { label: 'Weapons', icon: Swords },
  armour: { label: 'Armour', icon: Shield },
  mounts: { label: 'Mounts', icon: PawPrint },
  siege_materiel: { label: 'Siege materiel', icon: Castle },
  medicine: { label: 'Medicine', icon: FlaskConical },
  luxuries: { label: 'Luxuries', icon: Gem },
  incense: { label: 'Incense', icon: Wind },
  sacred_goods: { label: 'Sacred goods', icon: Cross },
  magical_reagents: { label: 'Magical reagents', icon: Sparkles },
}

export const WORKSHOP: Record<
  WorkshopKind,
  { label: string; icon: LucideIcon }
> = {
  market: { label: 'Market', icon: Store },
  granary: { label: 'Granary', icon: Warehouse },
  warehouse: { label: 'Warehouse', icon: Warehouse },
  mine: { label: 'Mine', icon: Pickaxe },
  lumber_camp: { label: 'Lumber camp', icon: Axe },
  fishery: { label: 'Fishery', icon: Fish },
  charcoal_kiln: { label: 'Charcoal kiln', icon: Flame },
  forge: { label: 'Forge', icon: Hammer },
  tannery: { label: 'Tannery', icon: Shirt },
  mill: { label: 'Mill', icon: Wheat },
  brewery: { label: 'Brewery', icon: Beer },
  weavery: { label: 'Weavery', icon: Shirt },
  stable: { label: 'Stable', icon: PawPrint },
  mason_yard: { label: 'Mason yard', icon: Box },
  shipyard: { label: 'Shipyard', icon: Anchor },
  siege_yard: { label: 'Siege yard', icon: Castle },
  alchemist: { label: 'Alchemist', icon: FlaskConical },
  shrine_workshop: { label: 'Shrine workshop', icon: Cross },
  mint: { label: 'Mint', icon: Coins },
}

export const MODE: Record<TradeMode, { label: string; icon: LucideIcon }> = {
  road: { label: 'Road', icon: Footprints },
  river: { label: 'River way', icon: Waves },
  sea: { label: 'Sea lane', icon: Ship },
  caravan: { label: 'Caravan way', icon: Tent },
  sky: { label: 'Sky lane', icon: Bird },
}

export const ROUTE_STATUS: Record<
  TradeRouteStatus,
  {
    label: string
    variant: 'success' | 'info' | 'warning' | 'destructive' | 'outline'
  }
> = {
  forming: { label: 'Forming', variant: 'info' },
  open: { label: 'Open', variant: 'success' },
  blockaded: { label: 'Blockaded', variant: 'destructive' },
  closed: { label: 'Closed', variant: 'warning' },
  decayed: { label: 'Fallen out of use', variant: 'outline' },
}

export const FAMILY_TONE: Record<
  MaterialFamily,
  'muted' | 'info' | 'gold' | 'verdigris' | 'warning'
> = {
  organic: 'verdigris',
  stone: 'muted',
  metal: 'info',
  precious: 'gold',
  exotic: 'warning',
}

export const ECONOMY_ICONS = {
  route: Route,
  bank: Landmark,
  coin: HandCoins,
  factory: Factory,
  goods: Package,
}

export function commodityLabel(kind: CommodityKind): string {
  return COMMODITY[kind].label
}
