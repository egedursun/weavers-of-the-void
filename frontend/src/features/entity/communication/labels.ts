import {
  Network,
  Bird,
  Flame,
  KeySquare,
  Mail,
  Megaphone,
  MessagesSquare,
  Moon,
  RadioTower,
  ScrollText,
  Sparkles,
  ThumbsUp,
  UserRoundCheck,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const CORRESPONDENCE_ICON = MessagesSquare
export const OPINION_ICON = ThumbsUp
export const CIPHER_ICON = KeySquare
export const SIGNAL_ICON = RadioTower
export const LETTER_ICON = Mail

export const MEDIUMS: Record<string, Named> = {
  envoy: { label: 'Envoy', icon: UserRoundCheck, tone: 'gold' },
  letter: { label: 'Letter', icon: Mail, tone: 'info' },
  herald: { label: 'Herald', icon: Megaphone, tone: 'warning' },
  signal_fire: { label: 'Signal fire', icon: Flame, tone: 'danger' },
  dream: { label: 'Dream', icon: Moon, tone: 'verdigris' },
  bird: { label: 'Messenger bird', icon: Bird, tone: 'info' },
  magic_sending: { label: 'Magic sending', icon: Sparkles, tone: 'verdigris' },
  network: { label: 'By network', icon: Network, tone: 'info' },
}

export const STATE_TONE: Record<string, Named['tone']> = {
  under_way: 'info',
  delivered: 'success',
  intercepted: 'danger',
  lost: 'muted',
}

export const SIGNAL_ICONS: Record<string, Named> = {
  fire_beacon: { label: 'Fire beacons', icon: Flame, tone: 'danger' },
  mirror_tower: { label: 'Mirror towers', icon: RadioTower, tone: 'info' },
  post_station: { label: 'Post stations', icon: ScrollText, tone: 'gold' },
  sending_stone: { label: 'Sending stones', icon: Sparkles, tone: 'verdigris' },
}

export function approvalTone(approval: number): Named['tone'] {
  if (approval >= 30) return 'success'
  if (approval <= -30) return 'danger'
  return 'muted'
}
