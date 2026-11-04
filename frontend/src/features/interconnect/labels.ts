import {
  ArrowDownLeft,
  ArrowUpRight,
  Atom,
  BookOpen,
  Brain,
  Church,
  Cloud,
  Coins,
  Cog,
  Crown,
  Drama,
  Eye,
  Gavel,
  HeartPulse,
  House,
  Languages,
  Leaf,
  MessagesSquare,
  Orbit,
  Sparkles,
  Swords,
  Users,
  Wand2,
  Waypoints,
  Zap,
} from 'lucide-react'
import { type Named } from '@/features/entity/environment/labels'

export const SUBSYSTEM: Record<string, Named> = {
  core: { label: 'Core', icon: Cog },
  body: { label: 'Body', icon: HeartPulse, tone: 'danger' },
  mind: { label: 'Mind', icon: Brain, tone: 'info' },
  social: { label: 'Society', icon: Users },
  household: { label: 'Household', icon: House },
  demography: { label: 'Demography', icon: Users, tone: 'verdigris' },
  economy: { label: 'Economy', icon: Coins, tone: 'gold' },
  polity: { label: 'Polity', icon: Crown, tone: 'gold' },
  law: { label: 'Law', icon: Gavel },
  intrigue: { label: 'Intrigue', icon: Eye, tone: 'warning' },
  communication: { label: 'Communication', icon: MessagesSquare },
  war: { label: 'War', icon: Swords, tone: 'danger' },
  faith: { label: 'Faith', icon: Church, tone: 'info' },
  magic: { label: 'Magic', icon: Wand2, tone: 'verdigris' },
  knowledge: { label: 'Knowledge', icon: BookOpen },
  culture: { label: 'Culture', icon: Drama, tone: 'verdigris' },
  language: { label: 'Language', icon: Languages },
  ecology: { label: 'Ecology', icon: Leaf, tone: 'success' },
  environment: { label: 'Environment', icon: Cloud, tone: 'info' },
  gods: { label: 'Gods', icon: Sparkles, tone: 'gold' },
  cosmos: { label: 'Cosmos', icon: Orbit, tone: 'info' },
}

export const EDGE_KIND: Record<string, Named> = {
  flow: { label: 'Value flow', icon: Waypoints },
  modifier: { label: 'Modifier', icon: Atom, tone: 'gold' },
  trigger: { label: 'Trigger', icon: Zap, tone: 'warning' },
  rule_switch: { label: 'Rule switch', icon: Cog },
}

export const DIRECTION: Record<string, Named> = {
  out: { label: 'Feeds', icon: ArrowUpRight, tone: 'success' },
  in: { label: 'Reads from', icon: ArrowDownLeft, tone: 'info' },
}

export function heat(edges: number, most: number): 0 | 1 | 2 | 3 {
  if (edges <= 0 || most <= 0) return 0
  const share = Math.log1p(edges) / Math.log1p(most)
  if (share > 0.75) return 3
  if (share > 0.45) return 2
  return 1
}
