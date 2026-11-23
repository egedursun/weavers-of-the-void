import {
  ArrowDownRight,
  ArrowUpRight,
  CircleSlash,
  Clock,
  CloudDrizzle,
  CloudRain,
  Droplet,
  Minus,
  Snowflake,
  Sun,
  SunDim,
  Thermometer,
  ThermometerSnowflake,
  ThermometerSun,
  Timer,
  TimerOff,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import type { Named } from '@/features/entity/environment/labels'

type SeasonView = components['schemas']['SeasonView']
type OnsetView = components['schemas']['SeasonOnsetView']

export const SEASON_WARMTH: Record<SeasonView['warmth'], Named> = {
  coldest: { label: 'Coldest', icon: Snowflake, tone: 'info' },
  cold: { label: 'Cold', icon: ThermometerSnowflake, tone: 'info' },
  cooling: { label: 'Cooling', icon: ArrowDownRight, tone: 'verdigris' },
  even: { label: 'Even', icon: Thermometer, tone: 'muted' },
  warming: { label: 'Warming', icon: ArrowUpRight, tone: 'success' },
  warm: { label: 'Warm', icon: ThermometerSun, tone: 'warning' },
  warmest: { label: 'Warmest', icon: Sun, tone: 'gold' },
}

export const SEASON_WATER: Record<SeasonView['water'], Named> = {
  arid: { label: 'Arid', icon: SunDim, tone: 'warning' },
  dry: { label: 'Dry', icon: Droplet, tone: 'muted' },
  even: { label: 'Even', icon: Minus, tone: 'muted' },
  wet: { label: 'Wet', icon: CloudDrizzle, tone: 'info' },
  deluge: { label: 'Deluge', icon: CloudRain, tone: 'verdigris' },
}

export const SEASON_ONSET: Record<OnsetView['onset'], Named> = {
  early: { label: 'Early', icon: Timer, tone: 'success' },
  on_time: { label: 'On time', icon: Clock, tone: 'muted' },
  late: { label: 'Late', icon: TimerOff, tone: 'warning' },
  failed: { label: 'Failed', icon: CircleSlash, tone: 'danger' },
}
