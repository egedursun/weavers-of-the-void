import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import {
  type ProposalStatus,
  type QueuedActStatus,
  type QueuedActView,
} from './types'

export const TEAM_PAGE = 24

export function useTeam() {
  return useQuery({
    queryKey: queryKeys.team.view,
    queryFn: () => unwrap(api.GET('/api/team')),
    refetchOnWindowFocus: true,
  })
}

export function useQueue(status: QueuedActStatus | null, limit = TEAM_PAGE) {
  return useQuery({
    queryKey: [...queryKeys.team.queue(status ?? 'all'), limit],
    queryFn: () =>
      unwrap(
        api.GET('/api/team/queue', {
          params: { query: { status: status ?? undefined, limit } },
        })
      ),
    placeholderData: (previous) => previous,
  })
}

export function useProposals(status: ProposalStatus | null, limit = TEAM_PAGE) {
  return useQuery({
    queryKey: [...queryKeys.team.proposals(status ?? 'all'), limit],
    queryFn: () =>
      unwrap(
        api.GET('/api/team/proposals', {
          params: { query: { status: status ?? undefined, limit } },
        })
      ),
    placeholderData: (previous) => previous,
  })
}

function useTeamRefresh() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ queryKey: queryKeys.team.all })
}

export function useCancelQueued() {
  const refresh = useTeamRefresh()
  return useMutation({
    writes: [{ method: 'DELETE', path: '/api/team/queue/{act_id}' }],
    mutationFn: (act: QueuedActView) =>
      unwrap(
        api.DELETE('/api/team/queue/{act_id}', {
          params: { path: { act_id: act.id } },
        })
      ),
    onSuccess: refresh,
  })
}

export function useRetryQueued() {
  const refresh = useTeamRefresh()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/team/queue/{act_id}/retry' }],
    mutationFn: (act: QueuedActView) =>
      unwrap(
        api.POST('/api/team/queue/{act_id}/retry', {
          params: { path: { act_id: act.id } },
        })
      ),
    onSuccess: refresh,
  })
}

export function useApproveProposal() {
  const refresh = useTeamRefresh()
  return useMutation({
    writes: [
      { method: 'POST', path: '/api/team/proposals/{proposal_id}/approve' },
    ],
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      unwrap(
        api.POST('/api/team/proposals/{proposal_id}/approve', {
          params: { path: { proposal_id: id } },
          body: { note },
        })
      ),
    onSuccess: refresh,
  })
}

export function useRejectProposal() {
  const refresh = useTeamRefresh()
  return useMutation({
    writes: [
      { method: 'POST', path: '/api/team/proposals/{proposal_id}/reject' },
    ],
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      unwrap(
        api.POST('/api/team/proposals/{proposal_id}/reject', {
          params: { path: { proposal_id: id } },
          body: { note },
        })
      ),
    onSuccess: refresh,
  })
}

export function useWithdrawProposal() {
  const refresh = useTeamRefresh()
  return useMutation({
    writes: [
      { method: 'POST', path: '/api/team/proposals/{proposal_id}/withdraw' },
    ],
    mutationFn: (id: number) =>
      unwrap(
        api.POST('/api/team/proposals/{proposal_id}/withdraw', {
          params: { path: { proposal_id: id } },
        })
      ),
    onSuccess: refresh,
  })
}

export function useMarkPresence() {
  return useMutation({
    writes: [{ method: 'POST', path: '/api/presence' }],
    mutationFn: (body: {
      screen: string
      node_id: number | null
      editing: boolean
    }) => unwrap(api.POST('/api/presence', { body })),
  })
}

export function useLeavePresence() {
  return useMutation({
    writes: [{ method: 'DELETE', path: '/api/presence' }],
    mutationFn: () => unwrap(api.DELETE('/api/presence')),
  })
}

export function useNodeRevision(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.team.all, 'revision', nodeId],
    queryFn: () =>
      unwrap(
        api.GET('/api/team/revisions/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
