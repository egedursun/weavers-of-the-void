import { createContext, useContext } from 'react'
import { type Permission, type UniverseRole } from './permissions'
import { type TeamView } from './types'

export type TeamContextValue = {
  team: TeamView | null
  universe: string
  role: UniverseRole | null
  me: number | null
  can: (permission: Permission) => boolean
}

export const TeamContext = createContext<TeamContextValue | null>(null)

export function useTeamContext(): TeamContextValue | null {
  return useContext(TeamContext)
}
