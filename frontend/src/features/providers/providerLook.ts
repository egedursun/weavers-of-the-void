import {
  BadgeCheck,
  Ban,
  CircleX,
  HardDrive,
  ImagePlus,
  KeyRound,
  LoaderCircle,
  type LucideIcon,
  MessagesSquare,
  PenLine,
  Swords,
} from 'lucide-react'
import { providerFamilyValues } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type LoginState, type ModelRole, type ProviderFamily } from './types'

export const FAMILIES: readonly ProviderFamily[] = providerFamilyValues

export const FAMILY_LOOK: Record<
  ProviderFamily,
  {
    label: string
    lead: string
    empty: string
    icon: LucideIcon
    tone: KpiTone
  }
> = {
  subscription: {
    label: 'Subscriptions',
    lead: 'A paid plan you log in to through its own official agent. Only in a personal workspace.',
    empty: 'No subscription is connected here yet.',
    icon: BadgeCheck,
    tone: 'gold',
  },
  api: {
    label: 'API keys',
    lead: 'A key of a cloud provider, sent through the gateway with each call.',
    empty: 'No API key is connected here yet.',
    icon: KeyRound,
    tone: 'info',
  },
  local: {
    label: 'Local',
    lead: 'A model server or image worker of your own, reached by its address.',
    empty: 'No local server or image worker is connected here yet.',
    icon: HardDrive,
    tone: 'verdigris',
  },
}

export const ROLE_LOOK: Record<
  ModelRole,
  { label: string; icon: LucideIcon; tone: KpiTone }
> = {
  world_agents: { label: 'World agents', icon: Swords, tone: 'danger' },
  writing: { label: 'Writing', icon: PenLine, tone: 'gold' },
  conversation: {
    label: 'Conversation',
    icon: MessagesSquare,
    tone: 'info',
  },
  images: { label: 'Images', icon: ImagePlus, tone: 'verdigris' },
}

export const LOGIN_LOOK: Record<
  LoginState,
  {
    label: string
    icon: LucideIcon
    variant: 'info' | 'success' | 'destructive' | 'outline'
  }
> = {
  running: { label: 'Waiting for you', icon: LoaderCircle, variant: 'info' },
  succeeded: { label: 'Logged in', icon: BadgeCheck, variant: 'success' },
  failed: { label: 'Not logged in', icon: CircleX, variant: 'destructive' },
  cancelled: { label: 'Stopped', icon: Ban, variant: 'outline' },
}
