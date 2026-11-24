import {
  Anchor,
  Castle,
  Church,
  Crown,
  Gem,
  Hammer,
  Landmark,
  Network,
  Scroll,
  Shield,
  Swords,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const TITLE_ICON = Crown
export const LANDS_ICON = Scroll
export const HISTORY_ICON = Landmark

export const RANKS: Record<string, Named> = {
  local: { label: 'Local', icon: Shield, tone: 'muted' },
  district: { label: 'District', icon: Shield, tone: 'info' },
  regional: { label: 'Regional', icon: Castle, tone: 'verdigris' },
  realm: { label: 'Realm', icon: Crown, tone: 'gold' },
  imperial: { label: 'Imperial', icon: Gem, tone: 'gold' },
  faith_local: { label: 'Local seat of a faith', icon: Church, tone: 'info' },
  faith_high: {
    label: 'High seat of a faith',
    icon: Church,
    tone: 'verdigris',
  },
  faith_supreme: {
    label: 'Foremost seat of a faith',
    icon: Church,
    tone: 'gold',
  },
  military: { label: 'Military command', icon: Swords, tone: 'danger' },
  guild: { label: 'Head of an association', icon: Hammer, tone: 'warning' },
  league: { label: 'League', icon: Network, tone: 'gold' },
}

export const TENURE_ICON = Anchor
