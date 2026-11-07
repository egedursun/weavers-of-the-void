import {
  Baby,
  Castle,
  Dna,
  Eye,
  Flame,
  Gem,
  HandHeart,
  Home,
  House,
  Landmark,
  Mountain,
  Ship,
  Sparkles,
  Tent,
  TowerControl,
  User,
  UserCog,
  Users,
  Wallet,
  Warehouse,
} from 'lucide-react'
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

export const DWELLINGS: Record<string, Named> = {
  hut: { label: 'Hut', icon: House, tone: 'muted' },
  longhouse: { label: 'Longhouse', icon: House, tone: 'verdigris' },
  townhouse: { label: 'Townhouse', icon: Home, tone: 'info' },
  manor: { label: 'Manor', icon: Landmark, tone: 'gold' },
  palace: { label: 'Palace', icon: Castle, tone: 'gold' },
  tent: { label: 'Tent', icon: Tent, tone: 'muted' },
  cave: { label: 'Cave', icon: Mountain, tone: 'muted' },
  ship: { label: 'Ship', icon: Ship, tone: 'info' },
  tower: { label: 'Tower', icon: TowerControl, tone: 'verdigris' },
}

export const ROLES: Record<string, Named> = {
  head: { label: 'Head', icon: UserCog, tone: 'gold' },
  spouse: { label: 'Spouse', icon: HandHeart, tone: 'info' },
  heir: { label: 'Heir', icon: User, tone: 'verdigris' },
  dependent: { label: 'Dependent', icon: Baby, tone: 'muted' },
  carer: { label: 'Carer', icon: HandHeart, tone: 'success' },
  servant: { label: 'Servant', icon: User, tone: 'muted' },
  ward: { label: 'Ward', icon: Baby, tone: 'info' },
  lodger: { label: 'Lodger', icon: User, tone: 'muted' },
}

export const STANCE_TONE: Record<string, Named['tone']> = {
  honoured: 'success',
  feared: 'warning',
  persecuted: 'danger',
  taxed: 'info',
}

export const GROUP_ICON: Record<string, Named['icon']> = {
  looks: Eye,
  predisposition: Dna,
  gift: Flame,
}
