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
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import {
  MODE,
  ROUTE_STATUS,
  type TradeMode,
  type TradeRouteStatus,
} from './labels'

export type DangerKey = 'bandits' | 'beasts' | 'weather' | 'sea'

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
}

export const DANGER_KEYS: readonly DangerKey[] = [
  'bandits',
  'beasts',
  'weather',
  'sea',
]

export const DANGER_FIELD: Record<DangerKey, string> = {
  bandits: 'danger_bandits',
  beasts: 'danger_beasts',
  weather: 'danger_weather',
  sea: 'danger_sea',
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
