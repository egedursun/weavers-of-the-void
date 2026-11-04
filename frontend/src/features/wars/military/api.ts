import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '@/features/entity/api/keys'

export type WarRoom = components['schemas']['WarRoomView']
export type ArmyCard = components['schemas']['ArmyCard']
export type BattleReport = components['schemas']['BattleReportView']
export type SiegeTracker = components['schemas']['SiegeTracker']
export type MilitaryOverview = components['schemas']['MilitaryOverview']
export type Stack = components['schemas']['StackView']
export type UnitKindSpec = components['schemas']['UnitKindSpec']
export type Stance = components['schemas']['Stance']
export type WarAimKind = components['schemas']['WarAimKind']
export type CaptiveFate = components['schemas']['CaptiveFate']
export type CommanderTrait = components['schemas']['CommanderTrait']
export type SpyNetwork = components['schemas']['SpyNetworkView']
export type CaptiveCohort = components['schemas']['CaptiveCohortView']
export type Occupation = components['schemas']['OccupationView']

export const militaryKeys = {
  room: (id: number) => ['wars', id, 'room'] as const,
  battle: (id: number) => ['battles', id] as const,
  army: (id: number) => [...loreKeys.entity(id), 'army'] as const,
  overview: (id: number) => [...loreKeys.entity(id), 'military'] as const,
  kinds: ['units', 'kinds'] as const,
}

export function useWarRoom(id: number) {
  return useQuery({
    queryKey: militaryKeys.room(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/wars/{war_id}/room', {
          params: { path: { war_id: id } },
        })
      ),
  })
}

export function useBattleReport(id: number) {
  return useQuery({
    queryKey: militaryKeys.battle(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/battles/{battle_id}', {
          params: { path: { battle_id: id } },
        })
      ),
  })
}

export function useArmyCard(id: number, enabled = true) {
  return useQuery({
    queryKey: militaryKeys.army(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/army', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useMilitary(id: number, enabled = true) {
  return useQuery({
    queryKey: militaryKeys.overview(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/military', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useUnitKinds() {
  return useQuery({
    queryKey: militaryKeys.kinds,
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/units/kinds')),
  })
}

export function words(value: string): string {
  return value.replaceAll('_', ' ')
}

export function table(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}
