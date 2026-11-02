import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type CreatorDetail = components['schemas']['CreatorDetail']
export type CreatorRecord = components['schemas']['CreatorRecord']
export type CreatorReputation = components['schemas']['CreatorReputation']
export type CreatorMood = components['schemas']['CreatorMood']
export type MoodAxis = components['schemas']['CreatorMoodAxis']
export type CreatorPassion = components['schemas']['CreatorPassion']

export const creatorKeys = {
  detail: [...queryKeys.world.all, 'creator'] as const,
  reputation: [...queryKeys.world.all, 'creator', 'reputation'] as const,
}

export function useCreator() {
  return useQuery({
    queryKey: creatorKeys.detail,
    queryFn: () => unwrap(api.GET('/api/creator')),
  })
}

export function useCreatorReputation() {
  return useQuery({
    queryKey: creatorKeys.reputation,
    queryFn: () => unwrap(api.GET('/api/creator/reputation')),
  })
}
