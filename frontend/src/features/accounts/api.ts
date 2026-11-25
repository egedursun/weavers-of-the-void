import { useQuery } from '@tanstack/react-query'
import { setAccountScope } from '@/api/accountScope'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useMutation } from '@/api/mutation'
import { libraryQueryClient } from '@/api/queryClients'
import { adoptViewerStorage } from '@/lib/universeStorage'
import { PASSWORD_MIN } from './passwordRules'
import {
  type AccountDraft,
  type ProfileDraft,
  type ServerRole,
  type SetupDraft,
} from './types'

const AUTH_KEY = ['auth'] as const

export const authKeys = {
  all: AUTH_KEY,
  state: [...AUTH_KEY, 'state'] as const,
  sessions: [...AUTH_KEY, 'sessions'] as const,
  accounts: [...AUTH_KEY, 'accounts'] as const,
}

export function refreshAuth(): Promise<void> {
  return libraryQueryClient.invalidateQueries({ queryKey: authKeys.all })
}

function authMutation<A, R>(run: (args: A) => Promise<R>) {
  return {
    permission: null,
    mutationFn: run,
    onSuccess: () => refreshAuth(),
  }
}

export function useAuthState() {
  return useQuery(
    {
      queryKey: authKeys.state,
      queryFn: async () => {
        const state = await unwrap(api.GET('/api/auth/state'))
        const id = state.account?.id ?? null
        if (id !== null) adoptViewerStorage(id)
        setAccountScope(id)
        return state
      },
      staleTime: Number.POSITIVE_INFINITY,
      retry: 1,
    },
    libraryQueryClient
  )
}

export function useSignedInAccount() {
  return useAuthState().data?.account ?? null
}

export function usePasswordMin(): number {
  return useAuthState().data?.password_min_length ?? PASSWORD_MIN
}

export function useSetup() {
  return useMutation(
    authMutation((draft: SetupDraft) =>
      unwrap(api.POST('/api/auth/setup', { body: draft }))
    ),
    libraryQueryClient
  )
}

export function useSignIn() {
  return useMutation(
    authMutation((body: { login: string; password: string }) =>
      unwrap(api.POST('/api/auth/sign-in', { body }))
    ),
    libraryQueryClient
  )
}

export function useSignOut() {
  return useMutation(
    {
      writes: [{ method: 'POST', path: '/api/auth/sign-out' }],
      permission: null,
      mutationFn: () => unwrap(api.POST('/api/auth/sign-out')),
      onSettled: () => refreshAuth(),
    },
    libraryQueryClient
  )
}

export function useChangePassword() {
  return useMutation(
    authMutation((body: { current: string; new: string }) =>
      unwrap(api.POST('/api/auth/password', { body }))
    ),
    libraryQueryClient
  )
}

export function useEditProfile() {
  return useMutation(
    authMutation((body: ProfileDraft) =>
      unwrap(api.PATCH('/api/auth/profile', { body }))
    ),
    libraryQueryClient
  )
}

export function useSessions(enabled: boolean) {
  return useQuery(
    {
      queryKey: authKeys.sessions,
      queryFn: () => unwrap(api.GET('/api/auth/sessions')),
      enabled,
    },
    libraryQueryClient
  )
}

export function useEndSession() {
  return useMutation(
    authMutation((id: number) =>
      unwrap(
        api.DELETE('/api/auth/sessions/{session_id}', {
          params: { path: { session_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useEndOtherSessions() {
  return useMutation(
    authMutation(() => unwrap(api.DELETE('/api/auth/sessions'))),
    libraryQueryClient
  )
}

export function useAccounts(enabled: boolean) {
  return useQuery(
    {
      queryKey: authKeys.accounts,
      queryFn: () => unwrap(api.GET('/api/accounts')),
      enabled,
    },
    libraryQueryClient
  )
}

export function useCreateAccount() {
  return useMutation(
    authMutation((body: AccountDraft) =>
      unwrap(api.POST('/api/accounts', { body }))
    ),
    libraryQueryClient
  )
}

export function useEditAccount() {
  return useMutation(
    authMutation(
      ({
        id,
        ...body
      }: {
        id: number
        server_role?: ServerRole
        status?: 'active' | 'deactivated'
      }) =>
        unwrap(
          api.PATCH('/api/accounts/{account_id}', {
            params: { path: { account_id: id } },
            body,
          })
        )
    ),
    libraryQueryClient
  )
}

export function useResetAccountPassword() {
  return useMutation(
    authMutation((id: number) =>
      unwrap(
        api.POST('/api/accounts/{account_id}/reset-password', {
          params: { path: { account_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useDeleteAccount() {
  return useMutation(
    authMutation((id: number) =>
      unwrap(
        api.DELETE('/api/accounts/{account_id}', {
          params: { path: { account_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}

export function useTransferOwnership() {
  return useMutation(
    authMutation((id: number) =>
      unwrap(
        api.POST('/api/accounts/{account_id}/ownership', {
          params: { path: { account_id: id } },
        })
      )
    ),
    libraryQueryClient
  )
}
