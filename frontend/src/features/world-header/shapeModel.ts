import {
  BookOpen,
  Brain,
  Crown,
  Dumbbell,
  Eye,
  Flame,
  Gem,
  HandHeart,
  Heart,
  Hourglass,
  type LucideIcon,
  Megaphone,
  Palette,
  Repeat,
  Ruler,
  Shield,
  Skull,
  Sparkles,
  Sprout,
  Sun,
  Telescope,
  Tornado,
  Users,
  Wind,
  Zap,
} from 'lucide-react'

export type Measure = {
  key: string
  label: string
  icon: LucideIcon
  min: number
  max: number
  start: number
  low: string
  high: string
  unit?: [string, string]
}

const PERCENT = 100
const EVEN = 50

function share(
  key: string,
  label: string,
  icon: LucideIcon,
  low: string,
  high: string
): Measure {
  return { key, label, icon, min: 0, max: PERCENT, start: EVEN, low, high }
}

export const ABILITIES: Measure[] = [
  share('strength', 'Strength', Dumbbell, 'Frail', 'Mighty'),
  share('agility', 'Agility', Wind, 'Clumsy', 'Swift'),
  share('intellect', 'Intellect', Brain, 'Dull', 'Brilliant'),
  share('charisma', 'Charisma', Sparkles, 'Plain', 'Magnetic'),
  share('endurance', 'Endurance', Shield, 'Fragile', 'Tireless'),
  share('willpower', 'Willpower', Flame, 'Yielding', 'Iron-willed'),
  share('perception', 'Perception', Eye, 'Unseeing', 'Keen'),
  share('wisdom', 'Wisdom', BookOpen, 'Rash', 'Sage'),
  share('creativity', 'Creativity', Palette, 'Rote', 'Inventive'),
  share('beauty', 'Beauty', Gem, 'Homely', 'Striking'),
]

export const YEARS: Measure[] = [
  {
    key: 'age',
    label: 'Age',
    icon: Hourglass,
    min: 0,
    max: 120,
    start: 25,
    low: 'Newborn',
    high: 'Ancient',
    unit: ['year', 'years'],
  },
  {
    key: 'lifespan',
    label: 'Lifespan',
    icon: Hourglass,
    min: 1,
    max: 200,
    start: 70,
    low: 'Brief',
    high: 'Long-lived',
    unit: ['year', 'years'],
  },
]

export const POWER: Measure = {
  key: 'power',
  label: 'Power',
  icon: Zap,
  min: 1,
  max: 10,
  start: 3,
  low: 'Faint',
  high: 'Overwhelming',
}

export const PASSIONS: Measure[] = [
  share('loyalty', 'Loyalty', Heart, 'Faithless', 'Devoted'),
  share('ambition', 'Ambition', Crown, 'Content', 'Grasping'),
  share('wrath', 'Wrath', Flame, 'Placid', 'Furious'),
  share('mercy', 'Mercy', HandHeart, 'Pitiless', 'Merciful'),
]

export const LAND: Measure[] = [
  share('breadth', 'Breadth', Ruler, 'Narrow', 'Vast'),
  share('danger', 'Danger', Skull, 'Safe', 'Deadly'),
  share('fertility', 'Fertility', Sprout, 'Barren', 'Lush'),
  share('magic', 'Magic', Sparkles, 'Mundane', 'Steeped'),
]

export const SETTLERS: Measure = {
  key: 'settlers',
  label: 'Settlers',
  icon: Users,
  min: 150,
  max: 5000,
  start: 300,
  low: 'A handful',
  high: 'A great exodus',
  unit: ['settler', 'settlers'],
}

export const RECORD_MEASURES: Record<string, Measure[]> = {
  celestial: [
    share('brightness', 'Brightness', Sun, 'Dim', 'Blazing'),
    share('influence', 'Influence', Megaphone, 'Ignored', 'Ruling'),
    share('visibility', 'Visibility', Telescope, 'Hidden', 'Ever seen'),
    {
      key: 'cycle',
      label: 'Cycle in years',
      icon: Repeat,
      min: 1,
      max: 1000,
      start: 12,
      low: 'Swift',
      high: 'Slow',
      unit: ['year', 'years'],
    },
  ],
  spirit: [
    share('strength', 'Strength', Zap, 'Faint', 'Overwhelming'),
    share('unrest', 'Unrest', Tornado, 'At peace', 'Raging'),
  ],
  natural_law: [],
  cult: [
    {
      key: 'followers',
      label: 'Followers',
      icon: Users,
      min: 1,
      max: 10000,
      start: 100,
      low: 'A few',
      high: 'Multitudes',
      unit: ['follower', 'followers'],
    },
    share('zeal', 'Zeal', Flame, 'Lukewarm', 'Fervent'),
    share('influence', 'Influence', Megaphone, 'Ignored', 'Ruling'),
  ],
}

const BANDS = [
  { below: 0.2, word: 'Very low' },
  { below: 0.4, word: 'Low' },
  { below: 0.6, word: 'Middling' },
  { below: 0.8, word: 'High' },
  { below: 1.01, word: 'Very high' },
]

export function bandOf(measure: Measure, value: number): string {
  if (measure.unit)
    return `${value} ${value === 1 ? measure.unit[0] : measure.unit[1]}`
  const span = Math.max(1, measure.max - measure.min)
  const place = (value - measure.min) / span
  return BANDS.find((band) => place < band.below)?.word ?? 'Very high'
}

export function startsOf(measures: Measure[]): Record<string, number> {
  return Object.fromEntries(
    measures.map((measure) => [measure.key, measure.start])
  )
}

export function rolled(measures: Measure[]): Record<string, number> {
  return Object.fromEntries(
    measures.map((measure) => {
      const span = measure.max - measure.min
      const low = measure.min + span * 0.15
      const high = measure.min + span * 0.85
      return [measure.key, Math.round(low + Math.random() * (high - low))]
    })
  )
}
