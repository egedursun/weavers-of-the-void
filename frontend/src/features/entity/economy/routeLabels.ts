import {
  CalendarRange,
  CloudLightning,
  Flag,
  Footprints,
  Gauge,
  Map as MapIcon,
  Mountain,
  Package,
  PawPrint,
  Route,
  ShieldAlert,
  Skull,
  Sparkles,
  Swords,
  Waves,
  type LucideIcon,
  Landmark,
  Apple,
  HandCoins,
  CalendarX,
  Truck,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import { TRANSPORTS } from '@/features/operations/labels'
import {
  MODE,
  ROUTE_STATUS,
  type TradeMode,
  type TradeRouteStatus,
} from './labels'

export type DangerKey =
  | 'bandits'
  | 'beasts'
  | 'weather'
  | 'sea'
  | 'officials'
  | 'spoilage'
  | 'pilferage'

export const DANGERS: Record<
  DangerKey,
  { label: string; icon: LucideIcon; tone: KpiTone; hint: string }
> = {
  bandits: {
    label: 'Bandits',
    icon: Skull,
    tone: 'danger',
    hint: 'The wild lands and any robber band camped on the way',
  },
  beasts: {
    label: 'Beasts',
    icon: PawPrint,
    tone: 'warning',
    hint: 'Hungry, territorial or enraged beasts near the road',
  },
  weather: {
    label: 'Weather',
    icon: CloudLightning,
    tone: 'info',
    hint: "This age's mud, snow, heat, floods and storms in the lands crossed",
  },
  sea: {
    label: 'The sea',
    icon: Waves,
    tone: 'verdigris',
    hint: 'Open water and storms at sea; losses here sink ships',
  },
  officials: {
    label: 'Officials',
    icon: Landmark,
    tone: 'gold',
    hint: 'Tolls, bribes and extortion by the realms at either end, by their corruption',
  },
  spoilage: {
    label: 'Spoilage',
    icon: Apple,
    tone: 'warning',
    hint: 'Goods that spoil on a long way where nothing keeps them',
  },
  pilferage: {
    label: 'Pilferage',
    icon: HandCoins,
    tone: 'danger',
    hint: 'Guards and crews helping themselves where no patrol watches the way',
  },
}

export const DANGER_KEYS: readonly DangerKey[] = [
  'bandits',
  'beasts',
  'weather',
  'sea',
  'officials',
  'spoilage',
  'pilferage',
]

export const DANGER_FIELD: Record<DangerKey, string> = {
  bandits: 'danger_bandits',
  beasts: 'danger_beasts',
  weather: 'danger_weather',
  sea: 'danger_sea',
  officials: 'danger_officials',
  spoilage: 'danger_spoilage',
  pilferage: 'danger_pilferage',
}

export const ROUTE_FIELD: Record<string, { label: string; icon: LucideIcon }> =
  {
    mode: { label: 'Way of travel', icon: Footprints },
    status: { label: 'State', icon: Route },
    controller_entity_id: { label: 'Master of the road', icon: Flag },
    blockaded_by_entity_id: { label: 'Blockade', icon: ShieldAlert },
    capacity: { label: 'Capacity', icon: Package },
    danger: { label: 'Danger', icon: Swords },
    danger_bandits: { label: 'Bandit danger', icon: Skull },
    danger_beasts: { label: 'Beast danger', icon: PawPrint },
    danger_weather: { label: 'Weather danger', icon: CloudLightning },
    danger_sea: { label: 'Sea danger', icon: Waves },
    danger_officials: { label: 'Officials danger', icon: Landmark },
    danger_spoilage: { label: 'Spoilage danger', icon: Apple },
    danger_pilferage: { label: 'Pilferage danger', icon: HandCoins },
    closed_season: { label: 'Closed season', icon: CalendarX },
    carrier: { label: 'Carried by', icon: Truck },
    season_pct: { label: 'Worst season', icon: CalendarRange },
    length: { label: 'Length', icon: MapIcon },
    renown: { label: 'Renown', icon: Sparkles },
    culture: { label: 'Carried culture', icon: Gauge },
    chokepoint: { label: 'Chokepoint', icon: Mountain },
    path: { label: 'Path', icon: MapIcon },
  }

export function fieldLabel(key: string): string {
  return ROUTE_FIELD[key]?.label ?? key.replaceAll('_', ' ')
}

export const MODE_CHOICES: Record<string, string> = Object.fromEntries(
  (Object.keys(MODE) as TradeMode[]).map((key) => [key, MODE[key].label])
)

export const STATUS_CHOICES: Record<string, string> = Object.fromEntries(
  (Object.keys(ROUTE_STATUS) as TradeRouteStatus[]).map((key) => [
    key,
    ROUTE_STATUS[key].label,
  ])
)

export const LAND_DECIDES = 'land'

export function seasonTone(pct: number): KpiTone {
  if (pct >= 90) return 'success'
  if (pct >= 70) return 'gold'
  if (pct >= 50) return 'warning'
  return 'danger'
}

export function seasonWord(pct: number): string {
  if (pct >= 90) return 'Open all year'
  if (pct >= 70) return 'A hard season slows it'
  if (pct >= 50) return 'Half shut in its worst season'
  return 'Nearly shut in its worst season'
}

export const NO_CARRIER = 'none'
export const OPEN_ALL_YEAR = 'open'

export const CARRIER_CHOICES: Record<string, string> = {
  [NO_CARRIER]: 'The way of travel decides',
  ...Object.fromEntries(
    Object.entries(TRANSPORTS).map(([key, spec]) => [key, spec.label])
  ),
}

export function seasonChoices(
  seasons: Record<string, string>
): Record<string, string> {
  return { [OPEN_ALL_YEAR]: 'Open all year', ...seasons }
}
