import {
  BookOpen,
  Crown,
  Flame,
  Gem,
  HandCoins,
  HandHeart,
  Megaphone,
  Scale,
  ScrollText,
  Shield,
  Skull,
  Sparkles,
  Swords,
  Theater,
  Trophy,
  Zap,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const RENOWN_ICON = Megaphone
export const STANDING_ICON = Crown
export const DEED_ICON = Trophy
export const LORE_ICON = ScrollText

export const AXES: Record<string, Named> = {
  heroism: { label: 'Heroism', icon: Swords, tone: 'gold' },
  honour: { label: 'Honour', icon: Shield, tone: 'gold' },
  cruelty: { label: 'Cruelty', icon: Skull, tone: 'danger' },
  piety: { label: 'Piety', icon: Sparkles, tone: 'verdigris' },
  generosity: { label: 'Generosity', icon: HandHeart, tone: 'success' },
  wisdom: { label: 'Wisdom', icon: BookOpen, tone: 'info' },
  trickery: { label: 'Trickery', icon: Theater, tone: 'warning' },
  skill_renown: { label: 'Renown for a skill', icon: Gem, tone: 'gold' },
  troublemaker: { label: 'Troublemaking', icon: Zap, tone: 'danger' },
}

export const CURRENCIES: Record<string, Named> = {
  prestige: { label: 'Prestige', icon: Crown, tone: 'gold' },
  piety: { label: 'Piety', icon: Sparkles, tone: 'verdigris' },
  dread: { label: 'Dread', icon: Flame, tone: 'danger' },
  tyranny: { label: 'Tyranny', icon: Scale, tone: 'warning' },
}

export const PRICE_ICON = HandCoins
