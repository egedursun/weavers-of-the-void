import {
  BookOpen,
  Crown,
  Flame,
  Gem,
  GraduationCap,
  HandCoins,
  HandHeart,
  Handshake,
  HeartHandshake,
  House,
  Megaphone,
  Scale,
  ScrollText,
  Shield,
  ShieldCheck,
  Skull,
  Sparkles,
  Swords,
  Theater,
  Trophy,
  Zap,
} from 'lucide-react'
import { type Named } from '../environment/labels'
import { type ReputationAxis } from './api'

export const RENOWN_ICON = Megaphone
export const STANDING_ICON = Crown
export const DEED_ICON = Trophy
export const LORE_ICON = ScrollText

export const AXES: Record<ReputationAxis, Named> = {
  heroism: { label: 'Heroism', icon: Swords, tone: 'gold' },
  honour: { label: 'Honour', icon: Shield, tone: 'gold' },
  cruelty: { label: 'Cruelty', icon: Skull, tone: 'danger' },
  piety: { label: 'Piety', icon: Sparkles, tone: 'verdigris' },
  generosity: { label: 'Generosity', icon: HandHeart, tone: 'success' },
  wisdom: { label: 'Wisdom', icon: BookOpen, tone: 'info' },
  trickery: { label: 'Trickery', icon: Theater, tone: 'warning' },
  skill_renown: { label: 'Renown for a skill', icon: Gem, tone: 'gold' },
  troublemaker: { label: 'Troublemaking', icon: Zap, tone: 'danger' },
  mercy: { label: 'Mercy', icon: HeartHandshake, tone: 'success' },
  justice: { label: 'Justice', icon: Scale, tone: 'gold' },
  hospitality: { label: 'Hospitality', icon: House, tone: 'success' },
  reliability: { label: 'Reliability', icon: ShieldCheck, tone: 'success' },
}

export const CURRENCIES: Record<string, Named> = {
  prestige: { label: 'Prestige', icon: Crown, tone: 'gold' },
  piety: { label: 'Piety', icon: Sparkles, tone: 'verdigris' },
  dread: { label: 'Dread', icon: Flame, tone: 'danger' },
  tyranny: { label: 'Tyranny', icon: Scale, tone: 'warning' },
  trust: { label: 'Trust', icon: Handshake, tone: 'success' },
  learning: { label: 'Learning', icon: GraduationCap, tone: 'info' },
}

export const PRICE_ICON = HandCoins
