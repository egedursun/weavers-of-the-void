import {
  Castle,
  Fish,
  Gavel,
  Landmark,
  Library,
  MoonStar,
  ShieldPlus,
  Ship,
  Sparkles,
  UserRound,
  Users,
  Wind,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type LoreNamed } from './model'

type Schemas = components['schemas']

export const BOOST_TRIGGERS: Record<Schemas['BoostTrigger'], LoreNamed> = {
  coastal_fishing: {
    label: 'Coastal fishing at scale',
    icon: Fish,
    tone: 'info',
    hint: 'A great catch from the sea in the last epoch',
  },
  survived_siege: {
    label: 'Survived a siege',
    icon: Castle,
    tone: 'warning',
    hint: 'A siege of this place was driven off',
  },
  survived_epidemic: {
    label: 'Survived an epidemic',
    icon: ShieldPlus,
    tone: 'success',
    hint: 'An outbreak in its land has ended',
  },
  eclipse_observed: {
    label: 'An eclipse observed',
    icon: MoonStar,
    tone: 'verdigris',
    hint: 'An eclipse was watched from a working observatory',
  },
  great_trial: {
    label: 'A great trial',
    icon: Gavel,
    tone: 'gold',
    hint: 'A case with weighty evidence was closed in its court',
  },
  great_debt: {
    label: 'A great debt',
    icon: Landmark,
    tone: 'gold',
    hint: 'A large loan was given or taken',
  },
  steppe_horses_at_war: {
    label: 'Mounted peoples of the open plains at war',
    icon: Wind,
    tone: 'danger',
    hint: 'Mounts on the steppe while at war',
  },
}

export const CHOOSERS: Record<Schemas['ResearchChooser'], LoreNamed> = {
  scholars: {
    label: 'Their scholars',
    icon: Users,
    tone: 'info',
    hint: 'The most skilled scholars pick from the drawn choices each epoch',
  },
  agent: {
    label: 'Their own choice',
    icon: UserRound,
    tone: 'success',
    hint: 'One of their own chose it with choose_research',
  },
  god: {
    label: 'Your will',
    icon: Sparkles,
    tone: 'gold',
    hint: 'You set it',
  },
}

export const CAPABILITY_LOOK: Record<Schemas['Capability'], LoreNamed> = {
  blue_water_navigation: {
    label: 'Blue-water navigation',
    icon: Ship,
    tone: 'info',
  },
  university: { label: 'Universities can rise', icon: Library, tone: 'gold' },
}
