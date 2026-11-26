import {
  type DefaultError,
  type QueryClient,
  type UseMutationOptions,
  type UseMutationResult,
  useMutation as useQueryMutation,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { type WriteTarget, useWriteRefusal } from '@/features/team/writeGate'
import { settleRefetches } from './refetchSettle'
import { type Permission } from './teamGate'

export type ActGate = { blockedReason: string | null }

export type ActProp = ActGate | readonly ActGate[] | null

export function refusalOf(act: ActProp | undefined): string | null {
  if (!act) return null
  const gates: readonly ActGate[] = 'blockedReason' in act ? [act] : act
  for (const gate of gates)
    if (gate.blockedReason !== null) return gate.blockedReason
  return null
}

export function everyRefused(gates: readonly ActGate[]): ActGate {
  const reasons = gates.map((gate) => gate.blockedReason)
  return {
    blockedReason:
      reasons.length > 0 && reasons.every((reason) => reason !== null)
        ? reasons[0]
        : null,
  }
}

export type GatedMutationOptions<TData, TError, TVariables, TContext> =
  UseMutationOptions<TData, TError, TVariables, TContext> & {
    writes?: readonly WriteTarget[]
    permission?: Permission | null
  }

export type GatedMutation<TData, TError, TVariables, TContext> =
  UseMutationResult<TData, TError, TVariables, TContext> & ActGate

export function useMutation<
  TData = unknown,
  TError = DefaultError,
  TVariables = void,
  TContext = unknown,
>(
  {
    writes = [],
    permission,
    ...options
  }: GatedMutationOptions<TData, TError, TVariables, TContext>,
  client?: QueryClient
): GatedMutation<TData, TError, TVariables, TContext> {
  const blockedReason = useWriteRefusal(writes, permission)
  const queryClient = useQueryClient(client)
  const { onSuccess, onSettled } = options
  const settling: UseMutationOptions<TData, TError, TVariables, TContext> = {
    ...options,
    onSuccess:
      onSuccess &&
      ((...args) => settleRefetches(queryClient, () => onSuccess(...args))),
    onSettled:
      onSettled &&
      ((...args) => settleRefetches(queryClient, () => onSettled(...args))),
  }
  const mutation = useQueryMutation(settling, client)
  if (blockedReason === null) return { ...mutation, blockedReason }
  return {
    ...mutation,
    blockedReason,
    mutate: () => {
      toast.error(blockedReason)
    },
    mutateAsync: () => Promise.reject(new Error(blockedReason)),
  }
}
