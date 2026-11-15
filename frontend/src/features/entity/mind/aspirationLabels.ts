import {
  Award,
  BookOpen,
  Brush,
  Coins,
  Compass,
  Crown,
  Flame,
  Gem,
  Ghost,
  Hammer,
  Heart,
  HeartHandshake,
  Home,
  Mountain,
  PartyPopper,
  Scale,
  Shield,
  Sparkles,
  Star,
  Swords,
  Target,
  Telescope,
  Users,
  Wand2,
  CircleX,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'
import { type InspirationState } from './api'

export const ASPIRATION_ICON = Star
export const WANT_ICON = Target
export const FEAR_ICON = Ghost
export const FOCUS_ICON = Award
export const INSPIRATION_ICON = Flame

export const DREAM_STATES: Record<components['schemas']['DreamState'], Named> =
  {
    pursuing: { label: 'Pursuing', icon: Compass, tone: 'info' },
    fulfilled: { label: 'Fulfilled', icon: Award, tone: 'success' },
    failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
  }

export const INSPIRATION_STATES: Record<InspirationState, Named> = {
  burning: { label: 'Burning', icon: Flame, tone: 'warning' },
  fulfilled: { label: 'Fulfilled', icon: Award, tone: 'success' },
  failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
}

export const GOAL_ICONS: Record<string, Named> = {
  rule_a_realm: { label: 'Rule a realm', icon: Crown, tone: 'gold' },
  found_a_house: { label: 'Found a house', icon: Home, tone: 'gold' },
  master_a_craft: { label: 'Master a craft', icon: Hammer, tone: 'warning' },
  create_a_masterwork: {
    label: 'Create a masterwork',
    icon: Gem,
    tone: 'gold',
  },
  become_a_legend: { label: 'Become a legend', icon: Star, tone: 'gold' },
  raise_a_family: {
    label: 'Raise a large family',
    icon: Users,
    tone: 'success',
  },
  see_the_world: { label: 'See the world', icon: Compass, tone: 'info' },
  achieve_holiness: { label: 'Achieve holiness', icon: Sparkles, tone: 'gold' },
  gain_wealth: { label: 'Gain wealth', icon: Coins, tone: 'gold' },
  avenge_kin: { label: 'Avenge kin', icon: Swords, tone: 'danger' },
  know_a_truth: { label: 'Know a truth', icon: Telescope, tone: 'info' },
  defeat_a_beast: {
    label: 'Defeat a great beast',
    icon: Shield,
    tone: 'danger',
  },
  serve_a_god: { label: 'Serve a god', icon: Wand2, tone: 'verdigris' },
  live_in_peace: { label: 'Live in peace', icon: Mountain, tone: 'success' },
  find_love: { label: 'Find love', icon: Heart, tone: 'danger' },
}

export const FOCUS_ICONS: Record<string, Named> = {
  diplomacy: { label: 'Diplomacy', icon: HeartHandshake, tone: 'success' },
  martial: { label: 'Martial', icon: Swords, tone: 'danger' },
  stewardship: { label: 'Stewardship', icon: Scale, tone: 'gold' },
  intrigue: { label: 'Intrigue', icon: Ghost, tone: 'verdigris' },
  learning: { label: 'Learning', icon: BookOpen, tone: 'info' },
  piety: { label: 'Piety', icon: Sparkles, tone: 'gold' },
  craft: { label: 'Craft', icon: Brush, tone: 'warning' },
  leisure: { label: 'Leisure', icon: PartyPopper, tone: 'success' },
}
