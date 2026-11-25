import { type ReactNode, useEffect, useMemo } from 'react'
import { noteRevision, watchEditing } from '@/api/editSession'
import { setHoldFields, setTeamGate } from '@/api/teamGate'
import { useUniverseId } from '@/api/universeStore'
import { useUniverse } from '@/features/universes/api'
import { useTeam } from './api'
import {
  PERMISSIONS,
  type Permission,
  type UniverseRole,
  deniedReason,
} from './permissions'
import { TeamContext, type TeamContextValue } from './teamContext'
import { type TeamView } from './types'
import { useHoldFields } from './writeGate'

const UNNAMED = 'this universe'

function roleOf(team: TeamView | undefined): UniverseRole | null {
  const role = team?.role
  return role === undefined || role === null || role === 'none' ? null : role
}

export function TeamProvider({ children }: { children: ReactNode }) {
  const team = useTeam()
  const universeId = useUniverseId()
  const detail = useUniverse(universeId)
  const universe = detail.data?.name ?? UNNAMED
  const data = team.data
  const role = roleOf(data)
  const value = useMemo<TeamContextValue>(() => {
    const allowed = new Set<Permission>(data?.permissions ?? [])
    return {
      team: data ?? null,
      universe,
      role,
      me: data?.me?.account_id ?? null,
      can: (permission) => role === 'admin' || allowed.has(permission),
    }
  }, [data, role, universe])

  useEffect(() => {
    if (!data) return
    const refused = role ?? 'viewer'
    const refusals: Partial<Record<Permission, string>> = {}
    if (role !== 'admin')
      for (const permission of PERMISSIONS)
        if (!value.can(permission))
          refusals[permission] = deniedReason(refused, universe, permission)
    setTeamGate({
      universe,
      refusals,
      adminRefusal:
        role === 'admin'
          ? null
          : `Only administrators of ${universe} can do this.`,
    })
    noteRevision(data.revision)
  }, [data, role, universe, value])

  const holds = useHoldFields(data !== undefined)
  useEffect(() => {
    if (holds.data) setHoldFields(holds.data)
  }, [holds.data])

  useEffect(() => () => setTeamGate(null), [])
  useEffect(() => watchEditing(), [])

  return <TeamContext value={value}>{children}</TeamContext>
}
