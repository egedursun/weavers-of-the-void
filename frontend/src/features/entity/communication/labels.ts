import {
  Bird,
  Brain,
  Cable,
  Drum,
  Eye,
  Flame,
  KeySquare,
  Mail,
  Megaphone,
  MessagesSquare,
  Moon,
  Network,
  RadioTower,
  ScrollText,
  Sparkles,
  Sprout,
  ThumbsUp,
  UserRoundCheck,
  Rabbit,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'

export const CORRESPONDENCE_ICON = MessagesSquare
export const OPINION_ICON = ThumbsUp
export const CIPHER_ICON = KeySquare
export const SIGNAL_ICON = RadioTower
export const LETTER_ICON = Mail

export const MEDIUMS: Record<string, Named> = {
  courier_animal: { label: 'Courier animal', icon: Rabbit, tone: 'info' },
  drum_and_whistle: { label: 'Drum and whistle', icon: Drum, tone: 'warning' },
  envoy: { label: 'Envoy', icon: UserRoundCheck, tone: 'gold' },
  letter: { label: 'Letter', icon: Mail, tone: 'info' },
  herald: { label: 'Herald', icon: Megaphone, tone: 'warning' },
  signal_fire: { label: 'Signal fire', icon: Flame, tone: 'danger' },
  dream: { label: 'Dream', icon: Moon, tone: 'verdigris' },
  bird: { label: 'Messenger bird', icon: Bird, tone: 'info' },
  magic_sending: { label: 'Magic sending', icon: Sparkles, tone: 'verdigris' },
  network: { label: 'By network', icon: Network, tone: 'info' },
  mind_link: {
    label: 'By a link between minds',
    icon: Brain,
    tone: 'verdigris',
  },
  broadcast: { label: 'By broadcast', icon: RadioTower, tone: 'warning' },
}

export const STATE_TONE: Record<string, Named['tone']> = {
  under_way: 'info',
  delivered: 'success',
  intercepted: 'danger',
  lost: 'muted',
}

export const SIGNAL_ICONS: Record<components['schemas']['SignalKind'], Named> =
  {
    beacon_chain: { label: 'Beacon chains', icon: Flame, tone: 'danger' },
    optical_relay: { label: 'Optical relays', icon: Eye, tone: 'info' },
    courier_post: { label: 'Courier posts', icon: ScrollText, tone: 'gold' },
    bound_pair: { label: 'Bound pairs', icon: Sparkles, tone: 'verdigris' },
    wire_station: { label: 'Wire stations', icon: Cable, tone: 'muted' },
    radio_station: { label: 'Radio stations', icon: RadioTower, tone: 'info' },
    mind_link_station: {
      label: 'Mind-link stations',
      icon: Brain,
      tone: 'verdigris',
    },
    grown_node: { label: 'Grown nodes', icon: Sprout, tone: 'success' },
    drum_relay: { label: 'Drum relays', icon: Drum, tone: 'danger' },
  }

export function approvalTone(approval: number): Named['tone'] {
  if (approval >= 30) return 'success'
  if (approval <= -30) return 'danger'
  return 'muted'
}
