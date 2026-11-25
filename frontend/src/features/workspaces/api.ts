import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useMutation } from '@/api/mutation'
import { libraryQueryClient } from '@/api/queryClients'
import { libraryKeys } from '@/features/universes/api'
import {
  type MemberDraft,
  type Permission,
  type TunedRole,
  type UniverseRole,
  type WorkspaceRole,
} from './types'

const WORKSPACE_KEY = ['workspaces'] as const

export const workspaceKeys = {
  all: WORKSPACE_KEY,
  list: [...WORKSPACE_KEY, 'list'] as const,
  members: (id: number) => [...WORKSPACE_KEY, 'members', id] as const,
  candidates: (id: number, query: string) =>
    [...WORKSPACE_KEY, 'candidates', id, query] as const,
  access: (target: { id: number; universeId: string } | null) =>
    [...WORKSPACE_KEY, 'access', target] as const,
}

function refreshWorkspaces(): Promise<void> {
  return libraryQueryClient.invalidateQueries({ queryKey: workspaceKeys.all })
}

function workspaceMutation<A, R>(run: (args: A) => Promise<R>) {
  return {
    permission: null,
    mutationFn: run,
    onSuccess: () => refreshWorkspaces(),
  }
}

export function useWorkspaces() {
  return useQuery(
    {
      queryKey: workspaceKeys.list,
      queryFn: () => unwrap(api.GET('/api/workspaces')),
    },
    libraryQueryClient
  )
}

export function useCreateWorkspace() {
  return useMutation(
    workspaceMutation((name: string) =>
      unwrap(api.POST('/api/workspaces', { body: { name } }))
    ),
    libraryQueryClient
  )
}

export function useRenameWorkspace() {
  return useMutation(
    workspaceMutation(({ id, name }: { id: number; name: string }) =>
      unwrap(
        api.PATCH('/api/workspaces/{workspace_id}', {
          params: { path: { workspace_id: id } },
          body: { name },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useDeleteWorkspace() {
  return useMutation(
    workspaceMutation((id: number) =>
      unwrap(
        api.DELETE('/api/workspaces/{workspace_id}', {
          params: { path: { workspace_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useLeaveWorkspace() {
  return useMutation(
    workspaceMutation((id: number) =>
      unwrap(
        api.POST('/api/workspaces/{workspace_id}/leave', {
          params: { path: { workspace_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useCandidates(id: number, query: string) {
  const wanted = query.trim()
  return useQuery(
    {
      queryKey: workspaceKeys.candidates(id, wanted),
      queryFn: () =>
        unwrap(
          api.GET('/api/workspaces/{workspace_id}/candidates', {
            params: { path: { workspace_id: id }, query: { q: wanted } },
          })
        ),
      enabled: wanted.length > 0,
    },
    libraryQueryClient
  )
}

export function useMembers(id: number | null) {
  return useQuery(
    {
      queryKey: workspaceKeys.members(id ?? 0),
      queryFn: () =>
        unwrap(
          api.GET('/api/workspaces/{workspace_id}/members', {
            params: { path: { workspace_id: id ?? 0 } },
          })
        ),
      enabled: id !== null,
    },
    libraryQueryClient
  )
}

export function useAddMember() {
  return useMutation(
    workspaceMutation(({ id, draft }: { id: number; draft: MemberDraft }) =>
      unwrap(
        api.POST('/api/workspaces/{workspace_id}/members', {
          params: { path: { workspace_id: id } },
          body: draft,
        })
      )
    ),
    libraryQueryClient
  )
}

type MemberTarget = { id: number; accountId: number }

function memberPath({ id, accountId }: MemberTarget) {
  return { path: { workspace_id: id, account_id: accountId } }
}

export function useChangeMemberRole() {
  return useMutation(
    workspaceMutation(
      ({ role, ...target }: MemberTarget & { role: WorkspaceRole }) =>
        unwrap(
          api.PATCH('/api/workspaces/{workspace_id}/members/{account_id}', {
            params: memberPath(target),
            body: { role },
          })
        )
    ),
    libraryQueryClient
  )
}

export function useRemoveMember() {
  return useMutation(
    workspaceMutation((target: MemberTarget) =>
      unwrap(
        api.DELETE('/api/workspaces/{workspace_id}/members/{account_id}', {
          params: memberPath(target),
        })
      )
    ),
    libraryQueryClient
  )
}

export function useResetMemberPassword() {
  return useMutation(
    workspaceMutation((target: MemberTarget) =>
      unwrap(
        api.POST(
          '/api/workspaces/{workspace_id}/members/{account_id}/reset-password',
          { params: memberPath(target) }
        )
      )
    ),
    libraryQueryClient
  )
}

export function useSetMemberActive() {
  return useMutation(
    workspaceMutation(
      ({ active, ...target }: MemberTarget & { active: boolean }) =>
        unwrap(
          active
            ? api.POST(
                '/api/workspaces/{workspace_id}/members/{account_id}/reactivate',
                { params: memberPath(target) }
              )
            : api.POST(
                '/api/workspaces/{workspace_id}/members/{account_id}/deactivate',
                { params: memberPath(target) }
              )
        )
    ),
    libraryQueryClient
  )
}

type UniverseTarget = { id: number; universeId: string }

function accessPath({ id, universeId }: UniverseTarget) {
  return { path: { workspace_id: id, universe_id: universeId } }
}

export function useUniverseAccess(target: UniverseTarget | null) {
  return useQuery(
    {
      queryKey: workspaceKeys.access(target),
      queryFn: () =>
        unwrap(
          api.GET(
            '/api/workspaces/{workspace_id}/universes/{universe_id}/access',
            {
              params: accessPath(target ?? { id: 0, universeId: '' }),
            }
          )
        ),
      enabled: target !== null,
    },
    libraryQueryClient
  )
}

export function useSetOverride() {
  return useMutation(
    workspaceMutation(
      ({
        accountId,
        role,
        ...target
      }: UniverseTarget & { accountId: number; role: UniverseRole | null }) =>
        unwrap(
          role === null
            ? api.DELETE(
                '/api/workspaces/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}',
                {
                  params: {
                    path: { ...accessPath(target).path, account_id: accountId },
                  },
                }
              )
            : api.PUT(
                '/api/workspaces/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}',
                {
                  params: {
                    path: { ...accessPath(target).path, account_id: accountId },
                  },
                  body: { role },
                }
              )
        )
    ),
    libraryQueryClient
  )
}

export function useSetPermission() {
  return useMutation(
    workspaceMutation(
      ({
        changes,
        ...target
      }: UniverseTarget & {
        changes: Partial<
          Record<TunedRole, Partial<Record<Permission, boolean>>>
        >
      }) =>
        unwrap(
          api.PUT(
            '/api/workspaces/{workspace_id}/universes/{universe_id}/access/permissions',
            { params: accessPath(target), body: changes }
          )
        )
    ),
    libraryQueryClient
  )
}

export function useResetPermissions() {
  return useMutation(
    workspaceMutation((target: UniverseTarget) =>
      unwrap(
        api.DELETE(
          '/api/workspaces/{workspace_id}/universes/{universe_id}/access/permissions',
          { params: accessPath(target) }
        )
      )
    ),
    libraryQueryClient
  )
}

export function useSetCanonApproval() {
  return useMutation(
    workspaceMutation(({ on, ...target }: UniverseTarget & { on: boolean }) =>
      unwrap(
        api.PUT(
          '/api/workspaces/{workspace_id}/universes/{universe_id}/access/canon-approval',
          { params: accessPath(target), body: { on } }
        )
      )
    ),
    libraryQueryClient
  )
}

export function useMoveUniverse() {
  return useMutation(
    {
      writes: [
        { method: 'POST', path: '/api/library/universes/{universe_id}/move' },
      ],
      permission: null,
      mutationFn: ({
        universeId,
        workspaceId,
      }: {
        universeId: string
        workspaceId: number
      }) =>
        unwrap(
          api.POST('/api/library/universes/{universe_id}/move', {
            params: { path: { universe_id: universeId } },
            body: { workspace_id: workspaceId },
          })
        ),
      onSuccess: () =>
        Promise.all([
          refreshWorkspaces(),
          libraryQueryClient.invalidateQueries({ queryKey: libraryKeys.all }),
        ]),
    },
    libraryQueryClient
  )
}
