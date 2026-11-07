import {
  Anchor,
  Castle,
  Church,
  Crown,
  Gem,
  Hammer,
  Landmark,
  Scroll,
  Shield,
  Swords,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const TITLE_ICON = Crown
export const LANDS_ICON = Scroll
export const HISTORY_ICON = Landmark

export const RANKS: Record<string, Named> = {
  lordship: { label: 'Lordship', icon: Shield, tone: 'muted' },
  county: { label: 'County', icon: Shield, tone: 'info' },
  duchy: { label: 'Duchy', icon: Castle, tone: 'verdigris' },
  kingdom: { label: 'Kingdom', icon: Crown, tone: 'gold' },
  empire: { label: 'Empire', icon: Gem, tone: 'gold' },
  see: { label: 'See', icon: Church, tone: 'info' },
  archsee: { label: 'Archsee', icon: Church, tone: 'verdigris' },
  high_seat: { label: 'High Seat', icon: Church, tone: 'gold' },
  captaincy: { label: 'Captaincy', icon: Swords, tone: 'danger' },
  guildmastership: { label: 'Guildmastership', icon: Hammer, tone: 'warning' },
}

export const TENURE_ICON = Anchor
