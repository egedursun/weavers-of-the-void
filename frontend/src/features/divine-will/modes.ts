import {
  BookOpenText,
  Gavel,
  ListChecks,
  type LucideIcon,
  PenLine,
  Telescope,
  Zap,
} from 'lucide-react'
import { divineWillModeValues } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type DivineWillMode, type Toolset, type WillModeView } from './types'

export type ModeImpact = 'acts' | 'after_approval' | 'copy' | 'reads'

export type ModeLook = {
  impact: ModeImpact
  label: string
  tab: string
  icon: LucideIcon
  tone: KpiTone
  caption: string
  placeholder: string
}

export const MODE_ORDER: readonly DivineWillMode[] = divineWillModeValues

export const MODE_LOOK: Record<DivineWillMode, ModeLook> = {
  command: {
    impact: 'acts',
    label: 'Command',
    tab: 'Command',
    icon: Zap,
    tone: 'gold',
    caption:
      'Acts on the world at once and asks first before a costly or destructive act.',
    placeholder: 'Say what should be done in the world',
  },
  plan: {
    impact: 'after_approval',
    label: 'Plan',
    tab: 'Plan',
    icon: ListChecks,
    tone: 'info',
    caption:
      'Drafts steps you can edit; nothing changes until you approve and execute.',
    placeholder: 'Describe what the plan should reach',
  },
  ask_lore: {
    impact: 'reads',
    label: 'Ask Lore',
    tab: 'Ask Lore',
    icon: BookOpenText,
    tone: 'verdigris',
    caption: 'Answers from the record of the world and names every source.',
    placeholder: 'Ask anything about the world and its past',
  },
  creative_work: {
    impact: 'reads',
    label: 'Creative Work',
    tab: 'Creative',
    icon: PenLine,
    tone: 'success',
    caption:
      'Writes and revises works into the Library from the canon of the world.',
    placeholder: 'Say what to write, in what form and language',
  },
  mechanics_guide: {
    impact: 'reads',
    label: 'Mechanics Guide',
    tab: 'Mechanics',
    icon: Gavel,
    tone: 'muted',
    caption: 'Explains the rules and mechanics of the game and how they meet.',
    placeholder: 'Ask how a rule or mechanic works',
  },
  foresight: {
    impact: 'copy',
    label: 'Foresight',
    tab: 'Foresight',
    icon: Telescope,
    tone: 'warning',
    caption:
      'Lives a copy of the world ahead and compares it with your intervention.',
    placeholder: 'Say what to try and how many epochs to look ahead',
  },
}

export function stepMode(
  current: DivineWillMode,
  step: 1 | -1
): DivineWillMode {
  const index = MODE_ORDER.indexOf(current)
  const next = (index + step + MODE_ORDER.length) % MODE_ORDER.length
  return MODE_ORDER[next]
}

export function isMode(value: unknown): value is DivineWillMode {
  return MODE_ORDER.some((mode) => mode === value)
}

export const TOOLSET_LABEL: Record<Toolset, string> = {
  read: 'Reads the world',
  act: 'Acts on the world',
  catalog_read: 'Reads the acts',
  mechanics: 'Explains the mechanics',
  rules_read: 'Reads the world rules',
  plan: 'Drafts plans',
  foresight: 'Foresees',
  artifacts: 'Writes works',
  artifacts_read: 'Reads works',
  attachments: 'Reads your files',
  notices: 'Suggests modes',
}

export function impactOf(
  look: ModeLook,
  served: WillModeView | undefined
): ModeImpact {
  if (!served) return look.impact
  if (served.changes_world)
    return look.impact === 'reads' ? 'acts' : look.impact
  return look.impact === 'acts' ? 'reads' : look.impact
}
