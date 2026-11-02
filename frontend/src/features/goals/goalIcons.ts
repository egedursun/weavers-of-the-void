import {
  Bird,
  BookOpen,
  Church,
  Compass,
  Crown,
  Eye,
  Flag,
  Globe,
  Hand,
  HandHeart,
  Hourglass,
  Landmark,
  Languages,
  type LucideIcon,
  Radar,
  Rocket,
  RotateCcw,
  Shapes,
  Shield,
  Sparkles,
  Star,
  Sun,
  Trophy,
  Users,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type ScenarioKey } from './api'

type AchievementKey = components['schemas']['AchievementKey']

export const SCENARIO_ICON: Record<ScenarioKey, LucideIcon> = {
  doom_far: Hourglass,
  one_faith: Church,
  lost_star: Star,
  many_worlds: Globe,
  long_peace: Bird,
  cosmic_power: Rocket,
  loyal_pantheon: Crown,
  new_horizons: Compass,
}

export const ACHIEVEMENT_ICON: Record<AchievementKey, LucideIcon> = {
  second_sky: Sun,
  constellation: Sparkles,
  prophecy_fulfilled: Eye,
  return_from_death: RotateCcw,
  fathers_hand: Hand,
  babel: Languages,
  crowded_world: Users,
  first_prayer: HandHeart,
  creators_cult: Church,
  interstellar_traveller: Rocket,
  saga_completed: BookOpen,
  god_of_epochs: Hourglass,
  ancient: Landmark,
  crowded_pantheon: Crown,
  first_explorers: Compass,
  sensed_world: Radar,
  weapons_silent: Shield,
}

export const SCORE_PART_ICON: Record<string, LucideIcon> = {
  population: Users,
  diversity: Shapes,
  languages: Languages,
  worlds: Globe,
  civilization: Landmark,
  doomsday: Hourglass,
  achievements: Trophy,
  scenarios: Flag,
}

export const SCORE_PART_TONE: Record<string, KpiTone> = {
  population: 'info',
  diversity: 'verdigris',
  languages: 'verdigris',
  worlds: 'info',
  civilization: 'gold',
  doomsday: 'danger',
  achievements: 'gold',
  scenarios: 'success',
}
