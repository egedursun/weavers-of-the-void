import {
  type LucideIcon,
  LibraryBig,
  Settings2,
  UserCog,
  UsersRound,
} from 'lucide-react'

export type TeamPart = 'members' | 'universes' | 'general' | 'accounts'

export const TEAM_PARTS: readonly TeamPart[] = [
  'members',
  'universes',
  'general',
  'accounts',
]

export const TEAM_PART_LOOK: Record<
  TeamPart,
  { label: string; menu: string; icon: LucideIcon }
> = {
  members: { label: 'Members', menu: 'Members and roles', icon: UsersRound },
  universes: {
    label: 'Universes',
    menu: 'Who reaches each universe',
    icon: LibraryBig,
  },
  general: { label: 'Workspace', menu: 'Workspace settings', icon: Settings2 },
  accounts: {
    label: 'Server accounts',
    menu: 'Server accounts',
    icon: UserCog,
  },
}

export type TeamSearch = { part?: TeamPart; add?: boolean }

export function validateTeamSearch(
  search: Record<string, unknown>
): TeamSearch {
  const part = TEAM_PARTS.find((item) => item === search.part)
  return {
    ...(part ? { part } : {}),
    ...(search.add === true || search.add === 'true' ? { add: true } : {}),
  }
}
