import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type WorldState = components['schemas']['StateResponse']
export type EpochStatistics = components['schemas']['EpochStatistics']
export type EpochStatsData = components['schemas']['EpochStatsData']
export type EpochBreakdown = components['schemas']['EpochBreakdown']
export type ChangesResponse = components['schemas']['ChangesResponse']
export type LedgerItem = components['schemas']['LedgerItem']
export type LoreTotals = components['schemas']['LoreTotals']

export const overviewKeys = {
  state: [...queryKeys.world.all, 'state'] as const,
  lore: [...queryKeys.world.all, 'lore'] as const,
  stats: [...queryKeys.epochs.all, 'stats'] as const,
  breakdown: (epoch: number) =>
    [...queryKeys.epochs.all, 'breakdown', epoch] as const,
}

export function fetchWorldState(): Promise<WorldState> {
  return unwrap(api.GET('/api/state'))
}

export function useWorldState() {
  return useQuery({ queryKey: overviewKeys.state, queryFn: fetchWorldState })
}

export function useLoreTotals() {
  return useQuery({
    queryKey: overviewKeys.lore,
    queryFn: (): Promise<LoreTotals> => unwrap(api.GET('/api/stats/lore')),
  })
}

export function useEpochStatistics(enabled: boolean) {
  return useQuery({
    queryKey: overviewKeys.stats,
    queryFn: () => unwrap(api.GET('/api/stats/epochs')),
    enabled,
  })
}

export function useEpochBreakdown(epoch: number | null) {
  return useQuery({
    queryKey: overviewKeys.breakdown(epoch ?? 0),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/epochs/{epoch}/breakdown', {
          params: { path: { epoch: epoch ?? 0 } },
        })
      ),
    enabled: epoch !== null && epoch > 0,
    retry: false,
  })
}

export type ChangeTally = {
  entities: number
  removedEntities: number
  sons: number
  chronicleLines: number
  bonds: boolean
  cosmos: boolean
  worlds: boolean
  relations: boolean
  foreignGods: number
  rebuilt: boolean
}

export const EMPTY_TALLY: ChangeTally = {
  entities: 0,
  removedEntities: 0,
  sons: 0,
  chronicleLines: 0,
  bonds: false,
  cosmos: false,
  worlds: false,
  relations: false,
  foreignGods: 0,
  rebuilt: false,
}

export function addChanges(
  tally: ChangeTally,
  changes: ChangesResponse
): ChangeTally {
  return {
    entities: tally.entities + changes.entities.length,
    removedEntities: tally.removedEntities + changes.removed_entity_ids.length,
    sons: tally.sons + changes.sons.length + changes.removed_son_ids.length,
    chronicleLines: tally.chronicleLines + changes.new_chronicle_lines,
    bonds: tally.bonds || changes.bonds_changed,
    cosmos: tally.cosmos || changes.cosmos_changed,
    worlds: tally.worlds || changes.worlds_changed,
    relations: tally.relations || changes.relations_changed,
    foreignGods: tally.foreignGods + changes.foreign_god_ids.length,
    rebuilt: tally.rebuilt || changes.full,
  }
}

type DigestState = {
  since: string | null
  tally: ChangeTally
}

export function useChangeDigest() {
  const [digest, setDigest] = useState<DigestState>({
    since: null,
    tally: EMPTY_TALLY,
  })
  const query = useQuery({
    queryKey: [...queryKeys.world.all, 'changes', digest.since] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/changes', {
          params: { query: { since: digest.since ?? undefined } },
        })
      ),
  })
  const changes = query.data
  if (changes && changes.version !== digest.since) {
    setDigest({
      since: changes.version,
      tally:
        digest.since === null
          ? digest.tally
          : addChanges(digest.tally, changes),
    })
  }
  const reset = () =>
    setDigest((current) => ({ ...current, tally: EMPTY_TALLY }))
  return { query, tally: digest.tally, reset }
}
