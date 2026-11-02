import { Eye, Flame, type LucideIcon, Moon, Smile } from 'lucide-react'
import { type MoodAxis } from './api'

export type GaugeSpec = {
  axis: MoodAxis
  label: string
  icon: LucideIcon
  rule: string
  downward: boolean
  tone: 'destructive' | 'legendary' | 'default' | 'epic'
  effect: string
}

export const GAUGES: GaugeSpec[] = [
  {
    axis: 'anger',
    label: 'Anger',
    icon: Flame,
    rule: 'creator.wrath_threshold',
    downward: false,
    tone: 'destructive',
    effect: 'Wrath falls on godless and cursed lands.',
  },
  {
    axis: 'contentment',
    label: 'Contentment',
    icon: Smile,
    rule: 'creator.content_threshold',
    downward: false,
    tone: 'legendary',
    effect: 'Blessing descends on those who worship.',
  },
  {
    axis: 'interest',
    label: 'Attention',
    icon: Eye,
    rule: 'creator.label_silent',
    downward: true,
    tone: 'default',
    effect: 'Sons feel abandoned and their loyalty melts.',
  },
  {
    axis: 'loneliness',
    label: 'Loneliness',
    icon: Moon,
    rule: 'creator.label_lonely',
    downward: false,
    tone: 'epic',
    effect: "The Creator's light falls into the dreams of seers.",
  },
]

export const MOOD_AXES: MoodAxis[] = GAUGES.map((gauge) => gauge.axis)
