import {
  Church,
  Coins,
  Crown,
  FlaskConical,
  Footprints,
  Handshake,
  Landmark,
  Scale,
  Shield,
  Users,
  Vote,
  Wallet,
  HeartHandshake,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const LEAGUE_AIMS: Record<Schema['LeagueAim'], Named> = {
  defence: { label: 'Defence', icon: Shield, tone: 'danger' },
  trade: { label: 'Trade', icon: Handshake, tone: 'gold' },
  customs_union: { label: 'Customs union', icon: Landmark, tone: 'gold' },
  currency_union: { label: 'Currency union', icon: Coins, tone: 'gold' },
  law: { label: 'Law', icon: Scale, tone: 'info' },
  faith: { label: 'Faith', icon: Church, tone: 'verdigris' },
  peace: { label: 'Peace', icon: HeartHandshake, tone: 'success' },
  research: { label: 'Research', icon: FlaskConical, tone: 'info' },
  migration: { label: 'Migration', icon: Footprints, tone: 'warning' },
}

export const LEAGUE_VOTE_BASES: Record<Schema['LeagueVoteBasis'], Named> = {
  one_member_one_vote: {
    label: 'One realm, one vote',
    icon: Vote,
    tone: 'info',
  },
  by_population: { label: 'By population', icon: Users, tone: 'info' },
  by_dues: { label: 'By dues paid', icon: Wallet, tone: 'gold' },
  by_veto_holders: {
    label: 'By the veto holders',
    icon: Crown,
    tone: 'warning',
  },
}

export const LEAGUE_ICON = Handshake
