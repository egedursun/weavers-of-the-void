import {
  BookOpen,
  Brush,
  Feather,
  Layers,
  Link2,
  type LucideIcon,
  PenLine,
  Repeat,
  Sparkles,
  Tag,
  Unlink,
  UserRound,
  Wand2,
} from 'lucide-react'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'

export const ACTION_LABEL: Record<string, string> = {
  painted: 'Painted',
  deepened: 'Deepened',
  'image prompt written': 'Image prompt written',
  'epic written': 'Epic written',
  'likeness written': 'Likeness written',
  named: 'Named',
  'status changed': 'Status changed',
  created: 'Created',
  'powers written': 'Powers written',
  linked: 'Bond added',
  unlinked: 'Bond closed',
  'bond retyped': 'Bond retyped',
}

export const ACTION_ICON: Record<string, LucideIcon> = {
  painted: Brush,
  deepened: Layers,
  'image prompt written': PenLine,
  'epic written': BookOpen,
  'likeness written': UserRound,
  named: Tag,
  'status changed': Repeat,
  created: Sparkles,
  'powers written': Wand2,
  linked: Link2,
  unlinked: Unlink,
  'bond retyped': Link2,
}

export const FALLBACK_ACTION_ICON = Feather

export const ACTION_ORDER = Object.keys(ACTION_LABEL)

const DRAWER_OF_NODE: Record<string, DrawerKind> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  world: 'world',
  star: 'star',
  creator: 'creator',
  galaxy: 'galaxy',
  cluster: 'cluster',
  dimension: 'dimension',
}

export function drawerOfNode(kind: string): DrawerKind | null {
  return DRAWER_OF_NODE[kind] ?? null
}

export function actionLabel(action: string): string {
  return (
    ACTION_LABEL[action] ?? action.charAt(0).toUpperCase() + action.slice(1)
  )
}
