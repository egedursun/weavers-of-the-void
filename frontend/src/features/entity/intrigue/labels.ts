import {
  Anchor,
  Crosshair,
  Drama,
  Eye,
  HandCoins,
  KeyRound,
  ScrollText,
  Telescope,
  VenetianMask,
  Swords,
  Target,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const INTRIGUE_ICON = Drama
export const SECRET_ICON = KeyRound
export const HOOK_ICON = Anchor
export const FAVOUR_ICON = HandCoins
export const IDENTITY_ICON = VenetianMask
export const SCHEME_ICON = Crosshair
export const NAME_ICON = ScrollText
export const BELIEF_ICON = Telescope
export const WITNESS_ICON = Eye

export const PHASES: Record<string, Named> = {
  recruit: { label: 'Recruiting agents', icon: Crosshair, tone: 'info' },
  prepare: { label: 'Preparing', icon: Crosshair, tone: 'warning' },
  execute: { label: 'Carrying out', icon: Crosshair, tone: 'danger' },
  succeeded: { label: 'Succeeded', icon: Crosshair, tone: 'success' },
  failed: { label: 'Failed', icon: Target, tone: 'muted' },
  exposed: { label: 'Exposed', icon: Eye, tone: 'danger' },
  abandoned: { label: 'Abandoned', icon: Swords, tone: 'muted' },
}

export const OPEN_PHASES = new Set(['recruit', 'prepare', 'execute'])

export function severityTone(severity: number): Named['tone'] {
  if (severity >= 70) return 'danger'
  if (severity >= 40) return 'warning'
  return 'muted'
}
