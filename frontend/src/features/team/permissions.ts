import {
  BookDown,
  BookOpen,
  Eye,
  Feather,
  Hammer,
  Hourglass,
  ImagePlus,
  Library,
  Lock,
  type LucideIcon,
  MessageCircleQuestion,
  PackageOpen,
  Scale,
  Split,
  Undo2,
  Users,
} from 'lucide-react'
import { type components, permissionValues } from '@/api/generated/schema'
import { type Permission } from '@/api/teamGate'

export type { Permission }

export type UniverseRole = Exclude<
  components['schemas']['UniverseRole'],
  'none'
>

export type TunedRole = Exclude<UniverseRole, 'admin'>

export type PermissionLook = {
  label: string
  allows: string
  verb: string
  icon: LucideIcon
}

export const PERMISSION_LOOK: Record<Permission, PermissionLook> = {
  view: {
    label: 'Read',
    allows: 'Every screen, the chronicle, the Atlas and the book on screen',
    verb: 'read it',
    icon: Eye,
  },
  edit_world: {
    label: 'Change the world',
    allows:
      'Every god lever that creates, edits, holds or deletes a thing, and every Divine Will act',
    verb: 'change it',
    icon: Hammer,
  },
  start_ages: {
    label: 'Start ages',
    allows: 'Run epochs, half epochs, prehistory and every job of the world',
    verb: 'start its ages',
    icon: Hourglass,
  },
  change_rules: {
    label: 'Change rules',
    allows: 'Rule and setting changes',
    verb: 'change its rules',
    icon: Scale,
  },
  lock_canon: {
    label: 'Lock canon',
    allows:
      'Hold and release things, strike and restore canon, edit canon facts',
    verb: 'lock or release its canon',
    icon: Lock,
  },
  alternative_histories: {
    label: 'Alternative histories',
    allows: 'Foresight and other forks of the universe',
    verb: 'explore its alternative histories',
    icon: Split,
  },
  undo_own: {
    label: 'Undo own acts',
    allows: 'Undo the acts they made themselves',
    verb: 'undo their own acts',
    icon: Undo2,
  },
  undo_any: {
    label: "Undo anyone's acts",
    allows:
      "Undo anyone's act; every undo names who undid it and can be undone",
    verb: "undo others' acts",
    icon: Users,
  },
  generate_images: {
    label: 'Make images',
    allows: 'Image generation and restyling',
    verb: 'make its images',
    icon: ImagePlus,
  },
  export: {
    label: 'Export and copy',
    allows: 'Export the universe, duplicate it, download backups',
    verb: 'export or copy it',
    icon: PackageOpen,
  },
  download_books: {
    label: 'Download the book',
    allows: 'Book PDF and Codex downloads',
    verb: 'download its book or Codex',
    icon: BookDown,
  },
  divine_will_read: {
    label: 'Ask the Divine Will',
    allows: 'Divine Will modes that only read, and Presence off the record',
    verb: 'ask the Divine Will',
    icon: MessageCircleQuestion,
  },
  presence_on_record: {
    label: 'Presence on the record',
    allows: 'Summon to Presence on the record',
    verb: 'summon on the record',
    icon: Feather,
  },
  manage_shelf: {
    label: 'Keep the shelf',
    allows: 'Rename, notes, tags, cover, pin and archive in the library',
    verb: 'change it on the shelf',
    icon: Library,
  },
}

export const PERMISSIONS: readonly Permission[] = permissionValues

export const ROLE_LOOK: Record<
  UniverseRole,
  { label: string; plural: string; icon: LucideIcon; summary: string }
> = {
  admin: {
    label: 'Administrator',
    plural: 'Administrators',
    icon: BookOpen,
    summary:
      'Everything, plus who has access, the permission table, canon approval and deleting the universe',
  },
  editor: {
    label: 'Editor',
    plural: 'Editors',
    icon: Hammer,
    summary:
      'Everything in the world itself: levers, ages, rules, canon, undo, images and exports',
  },
  viewer: {
    label: 'Viewer',
    plural: 'Viewers',
    icon: Eye,
    summary:
      'Reads everything, downloads the book and the Codex, asks the Divine Will; changes nothing',
  },
}

export function deniedReason(
  role: UniverseRole,
  universe: string,
  permission: Permission
): string {
  return `${ROLE_LOOK[role].plural} of ${universe} cannot ${PERMISSION_LOOK[permission].verb}.`
}

export const WILL_MODE_PERMISSION: Record<
  components['schemas']['DivineWillMode'],
  Permission
> = {
  command: 'edit_world',
  plan: 'edit_world',
  ask_lore: 'divine_will_read',
  creative_work: 'divine_will_read',
  mechanics_guide: 'divine_will_read',
  foresight: 'alternative_histories',
}

export const PRESENCE_RECORD_PERMISSION: Record<
  components['schemas']['PresenceRecord'],
  Permission
> = {
  on_record: 'presence_on_record',
  off_record: 'divine_will_read',
}
