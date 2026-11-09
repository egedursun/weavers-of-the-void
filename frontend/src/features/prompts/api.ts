import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type ContextBlockInfo = components['schemas']['ContextBlockInfo']
export type ContextBlockKind = components['schemas']['ContextBlockKind']
export type ContextBlock = components['schemas']['ContextBlock']
export type SummarySection = components['schemas']['SummarySection']
export type SonPromptPreview = components['schemas']['SonPromptPreview']
export type PromptArea = components['schemas']['PromptArea']
export type PromptId = components['schemas']['PromptId']
export type PromptEntry = components['schemas']['PromptEntry']
export type PromptDetail = components['schemas']['PromptDetail']
export type ToolEntry = components['schemas']['ToolEntry']
export type TiredMotifReport = components['schemas']['TiredMotifReport']
export type MotifOverrideMode = components['schemas']['MotifOverrideMode']

export type BlockQuery = {
  kind: ContextBlockKind
  sonId: number | null
  worldId: number | null
  entityId: number | null
  section: SummarySection | null
  short: boolean
  full: boolean
}

const promptRoot = [...queryKeys.world.all, 'prompt-context'] as const

export const promptKeys = {
  blocks: [...queryKeys.catalogue.all, 'prompt-blocks'] as const,
  block: (query: BlockQuery) => [...promptRoot, 'block', query] as const,
  sonPrompt: (sonId: number) => [...promptRoot, 'son', sonId] as const,
  catalogue: (area: PromptArea | null) =>
    [...queryKeys.rules.all, 'prompt-catalogue', area] as const,
  detail: (promptId: PromptId) =>
    [...queryKeys.rules.all, 'prompt-catalogue', 'detail', promptId] as const,
  motifs: (worldId: number | null) =>
    [...promptRoot, 'tired-motifs', worldId] as const,
}

export function useContextBlockList() {
  return useQuery({
    queryKey: promptKeys.blocks,
    queryFn: () => unwrap(api.GET('/api/prompt-context/blocks')),
    staleTime: Infinity,
  })
}

export function useContextBlock(query: BlockQuery, enabled: boolean) {
  return useQuery({
    queryKey: promptKeys.block(query),
    enabled,
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/prompt-context/{kind}', {
          params: {
            path: { kind: query.kind },
            query: {
              son_id: query.sonId ?? undefined,
              world_id: query.worldId ?? undefined,
              entity_id: query.entityId ?? undefined,
              section: query.section ?? undefined,
              short: query.short || undefined,
              full: query.full || undefined,
            },
          },
        })
      ),
  })
}

export function useSonPrompt(sonId: number | null) {
  return useQuery({
    queryKey: promptKeys.sonPrompt(sonId ?? 0),
    enabled: sonId !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/prompt-context/son-prompt/{son_id}', {
          params: { path: { son_id: sonId ?? 0 } },
        })
      ),
  })
}

export function usePromptCatalogue(area: PromptArea | null) {
  return useQuery({
    queryKey: promptKeys.catalogue(area),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/prompt-context/catalogue', {
          params: { query: { area: area ?? undefined } },
        })
      ),
  })
}

export function usePromptDetail(promptId: PromptId | null) {
  return useQuery({
    queryKey: promptKeys.detail(promptId ?? 'fate_judgment_system'),
    enabled: promptId !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/prompt-context/catalogue/{prompt_id}', {
          params: { path: { prompt_id: promptId ?? 'fate_judgment_system' } },
        })
      ),
  })
}

export function useTiredMotifs(worldId: number | null) {
  return useQuery({
    queryKey: promptKeys.motifs(worldId),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/prompt-context/tired-motifs', {
          params: { query: { world_id: worldId ?? undefined } },
        })
      ),
  })
}

export type MotifChange = {
  motif: string
  worldId: number | null
  mode: MotifOverrideMode | null
}

export function useSetMotifOverride() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (change: MotifChange) =>
      change.mode === null
        ? unwrap(
            api.POST('/api/prompt-context/tired-motifs/overrides/clear', {
              body: { motif: change.motif, world_id: change.worldId },
            })
          )
        : unwrap(
            api.PUT('/api/prompt-context/tired-motifs/overrides', {
              body: {
                motif: change.motif,
                mode: change.mode,
                world_id: change.worldId,
              },
            })
          ),
    onSuccess: (report, change) => {
      queryClient.setQueryData(promptKeys.motifs(change.worldId), report)
      void queryClient.invalidateQueries({ queryKey: promptRoot })
    },
  })
}
