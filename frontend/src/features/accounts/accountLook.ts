import {
  Crown,
  type LucideIcon,
  ShieldCheck,
  UserRound,
  UserRoundCheck,
  UserRoundX,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import { type AccountStatus, type AvatarTone, type ServerRole } from './types'

export type Look = { label: string; icon: LucideIcon; tone: KpiTone }

export const AVATAR_TONES: Record<AvatarTone, string> = {
  gold: 'Gold',
  verdigris: 'Verdigris',
  info: 'Sapphire',
  success: 'Emerald',
  warning: 'Amber',
  danger: 'Ruby',
  muted: 'Silver',
}

export const SERVER_ROLE_LOOK: Record<
  ServerRole,
  Look & { meaning: string; manages: boolean }
> = {
  owner: {
    label: 'Owner',
    icon: Crown,
    tone: 'gold',
    meaning: 'Owns the server: manages every account and hands ownership on.',
    manages: true,
  },
  admin: {
    label: 'Server admin',
    icon: ShieldCheck,
    tone: 'info',
    meaning: 'Creates, resets, deactivates and deletes accounts.',
    manages: true,
  },
  member: {
    label: 'Member',
    icon: UserRound,
    tone: 'muted',
    meaning: 'Works in the workspaces they belong to.',
    manages: false,
  },
}

export const STATUS_LOOK: Record<AccountStatus, Look> = {
  active: { label: 'Active', icon: UserRoundCheck, tone: 'success' },
  deactivated: { label: 'Deactivated', icon: UserRoundX, tone: 'muted' },
}

export function managesAccounts(role: ServerRole): boolean {
  return SERVER_ROLE_LOOK[role].manages
}
