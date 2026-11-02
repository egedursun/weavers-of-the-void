import {
  Baby,
  Bomb,
  CloudLightning,
  Crown,
  Flame,
  Ghost,
  HandHeart,
  Hourglass,
  type LucideIcon,
  Megaphone,
  Orbit,
  Scroll,
  Skull,
  StickyNote,
  Swords,
  TriangleAlert,
  Trophy,
  Users,
  Hammer,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import { type NotificationCategory, type NotificationRecord } from './api'

export const CATEGORY_ICON: Record<NotificationCategory, LucideIcon> = {
  rebellion: Flame,
  death: Skull,
  birth: Baby,
  prophecy: Scroll,
  apocalypse: Bomb,
  horror: Ghost,
  war: Swords,
  prayer: HandHeart,
  cosmos: Orbit,
  ascension: Crown,
  disaster: CloudLightning,
  epoch: Hourglass,
  achievement: Trophy,
  society: Users,
  reputation: Megaphone,
  error: TriangleAlert,
  note: StickyNote,
  work: Hammer,
}

export const CATEGORY_TONE: Record<NotificationCategory, KpiTone> = {
  rebellion: 'danger',
  death: 'muted',
  birth: 'success',
  prophecy: 'info',
  apocalypse: 'danger',
  horror: 'danger',
  war: 'danger',
  prayer: 'gold',
  cosmos: 'info',
  ascension: 'gold',
  disaster: 'warning',
  epoch: 'verdigris',
  achievement: 'gold',
  society: 'verdigris',
  reputation: 'info',
  error: 'warning',
  note: 'gold',
  work: 'verdigris',
}

export type NotificationGroup = {
  key: string
  items: NotificationRecord[]
}

const REASON_SEPARATOR = ': '

export function reasonOf(item: NotificationRecord): string | null {
  if (item.category !== 'error') return null
  const text = item.body ?? item.title
  const cut = text.indexOf(REASON_SEPARATOR)
  return cut === -1 ? text : text.slice(cut + REASON_SEPARATOR.length)
}

export function subjectOf(item: NotificationRecord): string {
  const text = item.body ?? item.title
  const cut = text.indexOf(REASON_SEPARATOR)
  return cut === -1 ? item.title : text.slice(0, cut)
}

export function groupNotifications(
  items: NotificationRecord[]
): NotificationGroup[] {
  const groups: NotificationGroup[] = []
  const byReason = new Map<string, NotificationGroup>()
  for (const item of items) {
    const reason = reasonOf(item)
    const existing = reason === null ? undefined : byReason.get(reason)
    if (existing) {
      existing.items.push(item)
      continue
    }
    const group = { key: `n-${item.id}`, items: [item] }
    groups.push(group)
    if (reason !== null) byReason.set(reason, group)
  }
  return groups
}
