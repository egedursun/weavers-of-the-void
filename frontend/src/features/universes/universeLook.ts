import {
  Archive,
  ArchiveRestore,
  BookOpen,
  BookPlus,
  CalendarClock,
  CalendarPlus,
  Copy,
  Eraser,
  FileDown,
  FileUp,
  HardDrive,
  Hourglass,
  Landmark,
  type LucideIcon,
  NotebookPen,
  PenLine,
  SortAsc,
  Trash2,
  Undo2,
} from 'lucide-react'
import { fnv1a } from '@/lib/hash'
import { type KpiTone } from '@/components/domain'
import {
  type LibraryEventKind,
  type LibraryJobStage,
  type LibraryJobStatus,
  type UniverseOrigin,
  type UniverseSort,
  type UniverseStatus,
} from './types'

export type Look = { label: string; icon: LucideIcon; tone: KpiTone }

export const STATUS_LOOK: Record<UniverseStatus, Look> = {
  active: { label: 'On the shelf', icon: BookOpen, tone: 'gold' },
  archived: { label: 'Archived', icon: Archive, tone: 'muted' },
}

export const ORIGIN_LOOK: Record<UniverseOrigin, Look & { phrase: string }> = {
  created: {
    label: 'Created',
    phrase: 'Created in this library',
    icon: BookPlus,
    tone: 'gold',
  },
  imported: {
    label: 'Imported',
    phrase: 'Brought in from a universe file',
    icon: FileDown,
    tone: 'info',
  },
  duplicated: {
    label: 'Duplicated',
    phrase: 'Copied from another universe',
    icon: Copy,
    tone: 'verdigris',
  },
  adopted: {
    label: 'First universe',
    phrase: 'The universe this app held before the library',
    icon: Landmark,
    tone: 'success',
  },
}

export const SORT_LOOK: Record<
  UniverseSort,
  { label: string; icon: LucideIcon }
> = {
  opened: { label: 'Last opened first', icon: CalendarClock },
  created: { label: 'Newest first', icon: CalendarPlus },
  name: { label: 'By name', icon: SortAsc },
  epoch: { label: 'Furthest epoch first', icon: Hourglass },
  size: { label: 'Largest first', icon: HardDrive },
}

export const EVENT_LOOK: Record<LibraryEventKind, Look> = {
  created: { label: 'Created', icon: BookPlus, tone: 'gold' },
  adopted: { label: 'Adopted', icon: Landmark, tone: 'success' },
  opened: { label: 'Opened', icon: BookOpen, tone: 'info' },
  renamed: { label: 'Renamed', icon: PenLine, tone: 'muted' },
  edited: { label: 'Edited', icon: NotebookPen, tone: 'muted' },
  exported: { label: 'Exported', icon: FileUp, tone: 'info' },
  imported: { label: 'Imported', icon: FileDown, tone: 'info' },
  duplicated: { label: 'Duplicated', icon: Copy, tone: 'verdigris' },
  archived: { label: 'Archived', icon: Archive, tone: 'muted' },
  restored: { label: 'Restored', icon: ArchiveRestore, tone: 'success' },
  deleted: { label: 'Moved to the trash', icon: Trash2, tone: 'danger' },
  recovered: { label: 'Recovered', icon: Undo2, tone: 'success' },
  purged: { label: 'Purged', icon: Eraser, tone: 'danger' },
}

export const JOB_STATUS_LABEL: Record<LibraryJobStatus, string> = {
  running: 'Working',
  waiting: 'Checked, waiting for you',
  done: 'Finished',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export const JOB_STAGE_LABEL: Record<LibraryJobStage, string> = {
  snapshot: 'Taking a copy of the database',
  gather: 'Gathering the images and files',
  pack: 'Packing the file',
  check: 'Checking hashes, paths and the database',
  place: 'Placing the universe in its folder',
  register: 'Writing it into the catalogue',
}

const CREST_TONES: KpiTone[] = [
  'gold',
  'verdigris',
  'info',
  'success',
  'warning',
]

export function crestTone(seed: string): KpiTone {
  return CREST_TONES[fnv1a(seed) % CREST_TONES.length]
}
