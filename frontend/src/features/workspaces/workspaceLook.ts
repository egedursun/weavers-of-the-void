import {
  Archive,
  BookDown,
  BookOpenCheck,
  Crown,
  Eye,
  FileDown,
  GitFork,
  Hourglass,
  ImagePlus,
  type LucideIcon,
  MessageCircleQuestion,
  PenLine,
  Scale,
  ShieldCheck,
  Undo2,
  Users,
  UserRound,
  Undo,
  Lock,
} from 'lucide-react'
import { type KpiTone } from '@/components/domain'
import {
  type Permission,
  type UniverseRole,
  type WorkspaceKind,
  type WorkspaceRole,
} from './types'

type Look = { label: string; icon: LucideIcon; tone: KpiTone }

export const WORKSPACE_ROLE_LOOK: Record<
  WorkspaceRole,
  Look & { meaning: string }
> = {
  admin: {
    label: 'Administrator',
    icon: Crown,
    tone: 'gold',
    meaning:
      'Everything an Editor does, plus members, roles, access and deleting universes.',
  },
  editor: {
    label: 'Editor',
    icon: PenLine,
    tone: 'info',
    meaning:
      'Shapes every universe: edits, ages, rules, canon locks and undo. Cannot change who has access.',
  },
  viewer: {
    label: 'Viewer',
    icon: Eye,
    tone: 'muted',
    meaning:
      'Reads every universe, downloads the book and the Codex and asks the Divine Will; changes nothing.',
  },
}

export const UNIVERSE_ROLE_LOOK: Record<UniverseRole, Look> = {
  admin: { label: 'Administrator', icon: Crown, tone: 'gold' },
  editor: { label: 'Editor', icon: PenLine, tone: 'info' },
  viewer: { label: 'Viewer', icon: Eye, tone: 'muted' },
  none: { label: 'No access', icon: Lock, tone: 'danger' },
}

export const WORKSPACE_KIND_LOOK: Record<WorkspaceKind, Look> = {
  personal: { label: 'Personal', icon: UserRound, tone: 'verdigris' },
  team: { label: 'Team', icon: Users, tone: 'gold' },
}

export const PERMISSION_ICON: Record<Permission, LucideIcon> = {
  view: Eye,
  edit_world: PenLine,
  start_ages: Hourglass,
  change_rules: Scale,
  lock_canon: ShieldCheck,
  alternative_histories: GitFork,
  undo_own: Undo2,
  undo_any: Undo,
  generate_images: ImagePlus,
  export: FileDown,
  download_books: BookDown,
  divine_will_read: MessageCircleQuestion,
  presence_on_record: BookOpenCheck,
  manage_shelf: Archive,
}

export const WORKSPACE_ROLES: readonly WorkspaceRole[] = [
  'viewer',
  'editor',
  'admin',
]

export const OVERRIDE_ROLES: readonly UniverseRole[] = [
  'viewer',
  'editor',
  'admin',
  'none',
]
