import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

type Schema = components['schemas']
export type PowersNodeView = Schema['PowersNodeView']
export type PowerView = Schema['PowerView']
export type SourcesNodeView = Schema['SourcesNodeView']
export type PowerSourceView = Schema['PowerSourceView']
export type MagicSystemsNodeView = Schema['MagicSystemsNodeView']
export type MagicSystemView = Schema['MagicSystemView']
export type TruthsNodeView = Schema['TruthsNodeView']
export type HiddenTruthView = Schema['HiddenTruthView']
export type PublicKnowledgeView = Schema['PublicKnowledgeView']

const keys = {
  powers: (nodeId: number) =>
    [...queryKeys.world.all, 'powers-of', nodeId] as const,
  sources: (nodeId: number) =>
    [...queryKeys.world.all, 'sources-of', nodeId] as const,
  systems: (nodeId: number) =>
    [...queryKeys.world.all, 'magic-systems-of', nodeId] as const,
  truths: (nodeId: number) =>
    [...queryKeys.world.all, 'truths-of', nodeId] as const,
}

export function useNodePowers(nodeId: number) {
  return useQuery({
    queryKey: keys.powers(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/powers/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeSources(nodeId: number) {
  return useQuery({
    queryKey: keys.sources(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sources/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeSystems(nodeId: number) {
  return useQuery({
    queryKey: keys.systems(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/magic-systems/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeTruths(nodeId: number) {
  return useQuery({
    queryKey: keys.truths(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/truths/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
