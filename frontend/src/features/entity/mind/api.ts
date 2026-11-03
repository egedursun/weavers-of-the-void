import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Mind = components['schemas']['MindView']
export type MindValue = components['schemas']['ValueView']
export type MindTrait = components['schemas']['TraitView']
export type MindSkill = components['schemas']['SkillView']
export type MindMemory = components['schemas']['MemoryView']
export type MindOpinion = components['schemas']['OpinionView']
export type TraitKind = components['schemas']['TraitKind']
export type SkillKind = components['schemas']['SkillKind']
export type MemoryKind = components['schemas']['MemoryKind']
export type NeedKind = components['schemas']['NeedKind']
export type PressureKind = components['schemas']['PressureKind']
export type ValueAxis = components['schemas']['ValueAxis']
export type MortalRole = components['schemas']['MortalRole']

export function mindKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'mind'] as const
}

export function useMind(nodeId: number) {
  return useQuery({
    queryKey: mindKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/minds/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}

export function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}
