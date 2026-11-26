import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useMutation } from '@/api/mutation'
import { libraryQueryClient, refreshEveryUniverse } from '@/api/queryClients'
import { overviewKeys, useWorldState } from '@/features/overview/api'
import {
  type ChainLink,
  type ConnectionChange,
  type ConnectionDraft,
  type LoginView,
  type ModelRole,
  type ProviderScope,
} from './types'

const PROVIDERS_KEY = ['providers'] as const
const LOGIN_POLL_MS = 1000

function scopeKey(scope: ProviderScope): string {
  return scope === 'server' ? 'server' : String(scope.workspaceId)
}

export const providerKeys = {
  all: PROVIDERS_KEY,
  view: (scope: ProviderScope) =>
    [...PROVIDERS_KEY, 'view', scopeKey(scope)] as const,
  models: (scope: ProviderScope, connectionId: number) =>
    [...PROVIDERS_KEY, 'models', scopeKey(scope), connectionId] as const,
  login: (workspaceId: number, connectionId: number) =>
    [...PROVIDERS_KEY, 'login', workspaceId, connectionId] as const,
}

function refreshProviders(): Promise<void> {
  refreshEveryUniverse(overviewKeys.state)
  return libraryQueryClient.invalidateQueries({ queryKey: providerKeys.all })
}

function providerMutation<A, R>(run: (args: A) => Promise<R>) {
  return {
    permission: null,
    mutationFn: run,
    onSuccess: () => refreshProviders(),
  }
}

export function useProviders(scope: ProviderScope | null) {
  return useQuery(
    {
      queryKey: providerKeys.view(scope ?? 'server'),
      queryFn: () =>
        scope === null || scope === 'server'
          ? unwrap(api.GET('/api/server/providers'))
          : unwrap(
              api.GET('/api/workspaces/{workspace_id}/providers', {
                params: { path: { workspace_id: scope.workspaceId } },
              })
            ),
      enabled: scope !== null,
    },
    libraryQueryClient
  )
}

export function useConnectionModels(
  scope: ProviderScope,
  connectionId: number | null,
  wanted: boolean
) {
  return useQuery(
    {
      queryKey: providerKeys.models(scope, connectionId ?? -1),
      queryFn: () => {
        const id = connectionId ?? -1
        return scope === 'server'
          ? unwrap(
              api.GET(
                '/api/server/providers/connections/{connection_id}/models',
                {
                  params: { path: { connection_id: id } },
                }
              )
            )
          : unwrap(
              api.GET(
                '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/models',
                {
                  params: {
                    path: {
                      workspace_id: scope.workspaceId,
                      connection_id: id,
                    },
                  },
                }
              )
            )
      },
      enabled: wanted && connectionId !== null,
      retry: false,
      staleTime: Number.POSITIVE_INFINITY,
    },
    libraryQueryClient
  )
}

export function useAddConnection(scope: ProviderScope) {
  return useMutation(
    providerMutation((body: ConnectionDraft) =>
      scope === 'server'
        ? unwrap(api.POST('/api/server/providers/connections', { body }))
        : unwrap(
            api.POST('/api/workspaces/{workspace_id}/providers/connections', {
              params: { path: { workspace_id: scope.workspaceId } },
              body,
            })
          )
    ),
    libraryQueryClient
  )
}

export function useEditConnection(scope: ProviderScope) {
  return useMutation(
    providerMutation(({ id, body }: { id: number; body: ConnectionChange }) =>
      scope === 'server'
        ? unwrap(
            api.PATCH('/api/server/providers/connections/{connection_id}', {
              params: { path: { connection_id: id } },
              body,
            })
          )
        : unwrap(
            api.PATCH(
              '/api/workspaces/{workspace_id}/providers/connections/{connection_id}',
              {
                params: {
                  path: { workspace_id: scope.workspaceId, connection_id: id },
                },
                body,
              }
            )
          )
    ),
    libraryQueryClient
  )
}

export function useRemoveConnection(scope: ProviderScope) {
  return useMutation(
    providerMutation((id: number) =>
      scope === 'server'
        ? unwrap(
            api.DELETE('/api/server/providers/connections/{connection_id}', {
              params: { path: { connection_id: id } },
            })
          )
        : unwrap(
            api.DELETE(
              '/api/workspaces/{workspace_id}/providers/connections/{connection_id}',
              {
                params: {
                  path: { workspace_id: scope.workspaceId, connection_id: id },
                },
              }
            )
          )
    ),
    libraryQueryClient
  )
}

export function useSetChain(scope: ProviderScope) {
  return useMutation(
    providerMutation(
      ({ role, entries }: { role: ModelRole; entries: ChainLink[] }) =>
        scope === 'server'
          ? unwrap(
              api.PUT('/api/server/providers/roles/{role}', {
                params: { path: { role } },
                body: { entries },
              })
            )
          : unwrap(
              api.PUT('/api/workspaces/{workspace_id}/providers/roles/{role}', {
                params: { path: { workspace_id: scope.workspaceId, role } },
                body: { entries },
              })
            )
    ),
    libraryQueryClient
  )
}

export function useCheckChain(scope: ProviderScope) {
  return useMutation(
    providerMutation((role: ModelRole) =>
      scope === 'server'
        ? unwrap(
            api.POST('/api/server/providers/roles/{role}/check', {
              params: { path: { role } },
            })
          )
        : unwrap(
            api.POST(
              '/api/workspaces/{workspace_id}/providers/roles/{role}/check',
              { params: { path: { workspace_id: scope.workspaceId, role } } }
            )
          )
    ),
    libraryQueryClient
  )
}

function loginPath(workspaceId: number, connectionId: number) {
  return {
    params: {
      path: { workspace_id: workspaceId, connection_id: connectionId },
    },
  }
}

function keepLogin(workspaceId: number, connectionId: number) {
  return (view: LoginView) => {
    libraryQueryClient.setQueryData(
      providerKeys.login(workspaceId, connectionId),
      view
    )
    return refreshProviders()
  }
}

export function useLogin(
  workspaceId: number,
  connectionId: number,
  open: boolean
) {
  const login = useQuery(
    {
      queryKey: providerKeys.login(workspaceId, connectionId),
      queryFn: () =>
        unwrap(
          api.GET(
            '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/login',
            loginPath(workspaceId, connectionId)
          )
        ),
      enabled: open,
      retry: false,
      refetchInterval: (query) =>
        query.state.data?.state === 'running' ? LOGIN_POLL_MS : false,
    },
    libraryQueryClient
  )
  const ended = login.data?.ended_at ?? null
  useEffect(() => {
    if (ended !== null) void refreshProviders()
  }, [ended])
  return login
}

export function forgetLogin(workspaceId: number, connectionId: number): void {
  libraryQueryClient.removeQueries({
    queryKey: providerKeys.login(workspaceId, connectionId),
  })
}

export function useStartLogin(workspaceId: number, connectionId: number) {
  return useMutation(
    {
      permission: null,
      mutationFn: () =>
        unwrap(
          api.POST(
            '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/login',
            loginPath(workspaceId, connectionId)
          )
        ),
      onSuccess: keepLogin(workspaceId, connectionId),
    },
    libraryQueryClient
  )
}

export function useAnswerLogin(workspaceId: number, connectionId: number) {
  return useMutation(
    {
      permission: null,
      mutationFn: (text: string) =>
        unwrap(
          api.POST(
            '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/login/input',
            { ...loginPath(workspaceId, connectionId), body: { text } }
          )
        ),
      onSuccess: keepLogin(workspaceId, connectionId),
    },
    libraryQueryClient
  )
}

export function useStopLogin(workspaceId: number, connectionId: number) {
  return useMutation(
    providerMutation(() =>
      unwrap(
        api.DELETE(
          '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/login',
          loginPath(workspaceId, connectionId)
        )
      )
    ),
    libraryQueryClient
  )
}

export function useLogOut(workspaceId: number) {
  return useMutation(
    providerMutation((connectionId: number) =>
      unwrap(
        api.POST(
          '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/logout',
          loginPath(workspaceId, connectionId)
        )
      )
    ),
    libraryQueryClient
  )
}

export function useRoleModel(role: ModelRole): string | undefined {
  const state = useWorldState()
  return state.data?.role_models.find((entry) => entry.role === role)?.model
}
