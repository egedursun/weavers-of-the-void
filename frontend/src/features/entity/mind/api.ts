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

export type MindSplit = components['schemas']['MindSplitView']
export type MindAttribute = components['schemas']['AttributeView']
export type MindFacet = components['schemas']['FacetView']
export type MindIdea = components['schemas']['IdeaView']
export type MindIdeaSpec = components['schemas']['IdeaSpecView']
export type IdeaKind = components['schemas']['IdeaKind']
export type IdeaState = components['schemas']['IdeaState']
export type IdeaSource = components['schemas']['IdeaSource']

export function mindSplitKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'mind-split'] as const
}

export function useMindSplit(nodeId: number) {
  return useQuery({
    queryKey: mindSplitKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/minds/{node_id}/split', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}

export type Feelings = components['schemas']['FeelingsView']
export type FeelingThought = components['schemas']['ThoughtView']
export type FeelingGrief = components['schemas']['GriefView']
export type FeelingDream = components['schemas']['DreamLogView']
export type ThoughtKind = components['schemas']['ThoughtKind']
export type Emotion = components['schemas']['Emotion']
export type GriefStage = components['schemas']['GriefStage']
export type DreamKind = components['schemas']['DreamKind']
export type DreamReading = components['schemas']['DreamReading']

export function feelingsKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'feelings'] as const
}

export function useFeelings(nodeId: number) {
  return useQuery({
    queryKey: feelingsKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/minds/{node_id}/feelings', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}

export type CultureMind = components['schemas']['CultureMindView']
export type Preference = components['schemas']['PreferenceView']
export type PreferenceKind = components['schemas']['PreferenceKind']
export type Ethic = components['schemas']['EthicView']
export type ActKind = components['schemas']['ActKind']
export type EthicalStance = components['schemas']['EthicalStance']
export type HonourModel = components['schemas']['HonourModel']

export function cultureMindKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'culture-mind'] as const
}

export function useCultureMind(nodeId: number) {
  return useQuery({
    queryKey: cultureMindKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/minds/{node_id}/culture', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
