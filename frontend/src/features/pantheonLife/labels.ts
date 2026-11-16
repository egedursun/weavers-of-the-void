import {
  ArrowDown,
  ArrowUp,
  Castle,
  Crown,
  GitMerge,
  Handshake,
  Heart,
  Landmark,
  Network,
  Scale,
  Swords,
  Users,
  UsersRound,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const PANTHEON_ICON = Landmark
export const SYNCRETISM_ICON = GitMerge

export const STRUCTURES: Record<Schema['PantheonStructure'], Named> = {
  council: { label: 'A council of equals', icon: Users, tone: 'info' },
  family: { label: 'A family of gods', icon: UsersRound, tone: 'gold' },
  court: { label: 'A ruler and a court', icon: Castle, tone: 'gold' },
  rivals: { label: 'Rivals', icon: Swords, tone: 'danger' },
  single_high_god: { label: 'One high god', icon: Crown, tone: 'gold' },
  dual: { label: 'A pair', icon: Scale, tone: 'verdigris' },
  loose: { label: 'Loosely bound', icon: Network, tone: 'muted' },
}

export const TIES: Record<Schema['PantheonTie'], Named> = {
  elder: { label: 'Elder of', icon: ArrowUp, tone: 'gold' },
  younger: { label: 'Younger than', icon: ArrowDown, tone: 'info' },
  partner: { label: 'Partner of', icon: Heart, tone: 'success' },
  kin: { label: 'Kin of', icon: UsersRound, tone: 'info' },
  ruler_of: { label: 'Rules over', icon: Crown, tone: 'gold' },
  servant_of: { label: 'Serves', icon: ArrowDown, tone: 'muted' },
  rival: { label: 'Rival of', icon: Swords, tone: 'danger' },
  ally: { label: 'Ally of', icon: Handshake, tone: 'success' },
}
