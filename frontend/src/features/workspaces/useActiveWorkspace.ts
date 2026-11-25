import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { libraryQueryClient } from '@/api/queryClients'
import { chooseUniverse } from '@/api/universeStore'
import { chooseWorkspace, useWorkspaceId } from '@/api/workspaceStore'
import { libraryKeys } from '@/features/universes/api'
import { useWorkspaces } from './api'
import { type Workspace } from './types'

export function pickWorkspace(
  workspaces: readonly Workspace[],
  chosen: string | null
): Workspace | null {
  return (
    workspaces.find((workspace) => String(workspace.id) === chosen) ??
    workspaces.find((workspace) => workspace.kind === 'personal') ??
    workspaces[0] ??
    null
  )
}

export function useActiveWorkspace() {
  const chosen = useWorkspaceId()
  const workspaces = useWorkspaces()
  const list = workspaces.data ?? []
  const active = workspaces.isSuccess ? pickWorkspace(list, chosen) : null
  const activeId = active === null ? null : String(active.id)
  useEffect(() => {
    if (activeId !== null && activeId !== chosen) chooseWorkspace(activeId)
  }, [activeId, chosen])
  return { workspaces, list, active }
}

export function useSwitchWorkspace() {
  const navigate = useNavigate()
  return (workspace: Workspace) => {
    chooseWorkspace(String(workspace.id))
    chooseUniverse(null)
    libraryQueryClient.removeQueries({ queryKey: libraryKeys.all })
    void navigate({ to: '/' })
  }
}
