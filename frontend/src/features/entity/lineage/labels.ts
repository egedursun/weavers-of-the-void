import {
  Activity,
  Baby,
  Biohazard,
  Brain,
  Dumbbell,
  Ear,
  HeartPulse,
  Hourglass,
  Snowflake,
  Sun,
  Dna,
  Eye,
  Flame,
  Gem,
  HandHeart,
  Home,
  Sparkles,
  User,
  UserCog,
  Users,
  Wallet,
  Warehouse,
  User2,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '../environment/labels'

export const LINEAGE_ICON = Dna
export const GIFT_ICON = Sparkles
export const LOOKS_ICON = Eye
export const POOL_ICON = Users
export const LIKENESS_ICON = Gem
export const HOME_ICON = Home
export const PURSE_ICON = Wallet
export const FURNISHING_ICON = Warehouse
export const CARE_ICON = HandHeart

export const ROLES: Record<string, Named> = {
  head: { label: 'Head', icon: UserCog, tone: 'gold' },
  spouse: { label: 'Spouse', icon: HandHeart, tone: 'info' },
  heir: { label: 'Heir', icon: User, tone: 'verdigris' },
  dependent: { label: 'Dependent', icon: Baby, tone: 'muted' },
  carer: { label: 'Carer', icon: HandHeart, tone: 'success' },
  servant: { label: 'Servant', icon: User2, tone: 'muted' },
  ward: { label: 'Ward', icon: Baby, tone: 'info' },
  lodger: { label: 'Lodger', icon: User, tone: 'muted' },
}

export const STANCE_TONE: Record<string, Named['tone']> = {
  honoured: 'success',
  feared: 'warning',
  persecuted: 'danger',
  taxed: 'info',
}

export const GROUP_ICON: Record<
  components['schemas']['LocusGroup'],
  Named['icon']
> = {
  looks: Eye,
  body: Dumbbell,
  sense: Ear,
  temperament: Activity,
  aptitude: Brain,
  predisposition: Dna,
  gift: Flame,
}

export const BLOOD_EFFECTS: Record<
  components['schemas']['GeneticEffect'],
  Named
> = {
  disease: { label: 'Sickness', icon: Biohazard, tone: 'danger' },
  fertility: { label: 'Children', icon: Baby, tone: 'verdigris' },
  madness: { label: 'Strain on the mind', icon: Brain, tone: 'warning' },
  lifespan: { label: 'Lifespan', icon: Hourglass, tone: 'gold' },
  healing: { label: 'Healing', icon: HeartPulse, tone: 'success' },
  stress: { label: 'Stress', icon: Activity, tone: 'warning' },
  cold: { label: 'Cold lands', icon: Snowflake, tone: 'info' },
  heat: { label: 'Hot lands', icon: Sun, tone: 'gold' },
}

export const HARMFUL_EFFECTS: ReadonlySet<
  components['schemas']['GeneticEffect']
> = new Set(['disease', 'madness', 'stress'])
