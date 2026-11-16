import {
  Ban,
  Brain,
  Copy,
  Cpu,
  Wrench,
  CheckCircle2,
  Eye,
  EyeOff,
  Flame,
  Footprints,
  Gavel,
  Ghost,
  Hand,
  HandCoins,
  Handshake,
  Landmark,
  Megaphone,
  MessageSquare,
  Scale,
  ScrollText,
  Search,
  ShieldCheck,
  ShieldX,
  Skull,
  Swords,
  Users,
  Vote,
  Wind,
  XCircle,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const JUSTICE_ICON = Scale
export const PROPOSAL_ICON = Vote
export const CASE_ICON = Gavel
export const WITNESS_ICON = Eye

export const PROPOSAL_STATES: Record<string, Named> = {
  debating: { label: 'Under debate', icon: MessageSquare, tone: 'info' },
  passed: { label: 'Passed into law', icon: CheckCircle2, tone: 'success' },
  failed: { label: 'Failed', icon: XCircle, tone: 'danger' },
  withdrawn: { label: 'Withdrawn', icon: Ban, tone: 'muted' },
}

export const PROPOSAL_EVENTS: Record<string, Named> = {
  debate: { label: 'Debated in assembly', icon: Users, tone: 'info' },
  riot: { label: 'Riots in the streets', icon: Flame, tone: 'danger' },
  compromise: {
    label: 'Softened by compromise',
    icon: Handshake,
    tone: 'gold',
  },
  obstruction: {
    label: 'Obstructed by estates',
    icon: ShieldX,
    tone: 'warning',
  },
}

export const STANCES: Record<string, Named> = {
  support: { label: 'For it', icon: CheckCircle2, tone: 'success' },
  oppose: { label: 'Against it', icon: XCircle, tone: 'danger' },
  obstruct: { label: 'Obstructing', icon: ShieldX, tone: 'warning' },
}

export const BASES: Record<string, Named> = {
  custom: { label: 'By custom', icon: ScrollText, tone: 'muted' },
  decree: { label: 'By decree', icon: Landmark, tone: 'gold' },
  divine: { label: 'By divine will', icon: Megaphone, tone: 'verdigris' },
  council: { label: 'By council', icon: Users, tone: 'info' },
}

export const STAGES: Record<string, Named> = {
  investigation: { label: 'Under investigation', icon: Search, tone: 'info' },
  trial: { label: 'Awaiting trial', icon: Gavel, tone: 'warning' },
  closed: { label: 'Closed', icon: CheckCircle2, tone: 'muted' },
}

export const TRIALS: Record<string, Named> = {
  judge: { label: 'Before a judge', icon: Gavel, tone: 'info' },
  jury: { label: 'Before a jury', icon: Users, tone: 'verdigris' },
  combat: { label: 'By combat', icon: Swords, tone: 'danger' },
  ordeal: { label: 'By ordeal', icon: Flame, tone: 'warning' },
}

export const VERDICTS: Record<string, Named> = {
  guilty: { label: 'Guilty', icon: Gavel, tone: 'danger' },
  acquitted: { label: 'Acquitted', icon: ShieldCheck, tone: 'success' },
  fled: { label: 'Fled the court', icon: Footprints, tone: 'warning' },
  dropped: { label: 'Dropped', icon: Wind, tone: 'muted' },
}

export const TESTIMONIES: Record<string, Named> = {
  accuses: { label: 'Accuses', icon: Hand, tone: 'danger' },
  shields: { label: 'Shields', icon: ShieldCheck, tone: 'success' },
  silent: { label: 'Silent', icon: EyeOff, tone: 'muted' },
}

export const CRIMES: Record<string, Named> = {
  theft: { label: 'Theft', icon: HandCoins, tone: 'warning' },
  murder: { label: 'Murder', icon: Skull, tone: 'danger' },
  treason: { label: 'Treason', icon: Landmark, tone: 'danger' },
  blasphemy: { label: 'Blasphemy', icon: Flame, tone: 'warning' },
  desertion: { label: 'Desertion', icon: Wind, tone: 'warning' },
  witchcraft: { label: 'Witchcraft', icon: Ghost, tone: 'danger' },
  mind_theft: { label: 'Theft of a mind', icon: Brain, tone: 'danger' },
  unlicensed_copying: {
    label: 'Copying a mind without leave',
    icon: Copy,
    tone: 'warning',
  },
  forced_edit: {
    label: 'Editing a mind by force',
    icon: Wrench,
    tone: 'danger',
  },
  erasure: { label: 'Ending a mind', icon: Skull, tone: 'danger' },
  machine_seizure: {
    label: 'Seizing a made thing',
    icon: Cpu,
    tone: 'warning',
  },
  impersonation: {
    label: 'Passing as another by a copy',
    icon: Users,
    tone: 'warning',
  },
  mind_compulsion: {
    label: 'Bending a mind by a power',
    icon: Brain,
    tone: 'danger',
  },
}

export function labelTable(
  specs: Record<string, Named>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(specs).map(([key, spec]) => [key, spec.label])
  )
}

export function spec(
  table: Record<string, Named>,
  key: string | null | undefined
): Named {
  return (
    (key ? table[key] : undefined) ?? {
      label: key ?? 'Unknown',
      icon: Scale,
      tone: 'muted',
    }
  )
}
