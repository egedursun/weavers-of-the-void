import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { fetchJobs } from '@/api/system'
import { type WriteTarget } from '@/features/team/writeGate'

export type GraphNodeRecord = components['schemas']['GraphNode']
export type GraphLinkRecord = components['schemas']['GraphLink']
export type LinkGroup = components['schemas']['LinkGroup']
export type LinkGroupInfo = components['schemas']['LinkGroupInfo']
export type GraphWindow = components['schemas']['GraphWindow']
export type PathResult = components['schemas']['PathResult']
export type NetworkHealth = components['schemas']['NetworkHealth']
export type RepairResult = components['schemas']['RepairResult']
export type FateLinkRequest = components['schemas']['FateLinkRequest']

export const GRAPH_WINDOW = 2000
export const JOB_SCAN_LIMIT = 50

export const graphKeys = {
  all: [...queryKeys.world.all, 'graph'] as const,
  window: [...queryKeys.world.all, 'graph', 'window'] as const,
  health: [...queryKeys.world.all, 'graph', 'health'] as const,
  path: (first: number, second: number) =>
    [...queryKeys.world.all, 'graph', 'path', first, second] as const,
}

export type FullGraph = {
  nodes: GraphNodeRecord[]
  links: GraphLinkRecord[]
  nodeTotal: number
  linkTotal: number
}

function graphWindow(nodeOffset: number, linkOffset: number) {
  return unwrap(
    api.GET('/api/graph', {
      params: {
        query: {
          node_offset: nodeOffset,
          node_limit: GRAPH_WINDOW,
          link_offset: linkOffset,
          link_limit: GRAPH_WINDOW,
        },
      },
    })
  )
}

export async function fetchFullGraph(): Promise<FullGraph> {
  const first = await graphWindow(0, 0)
  const nodes = [...first.nodes]
  const links = [...first.links]
  let nodeOffset = nodes.length
  let linkOffset = links.length
  while (
    (nodeOffset < first.node_total || linkOffset < first.link_total) &&
    (first.nodes.length > 0 || first.links.length > 0)
  ) {
    const next = await graphWindow(
      Math.min(nodeOffset, first.node_total),
      Math.min(linkOffset, first.link_total)
    )
    if (next.nodes.length === 0 && next.links.length === 0) break
    if (nodeOffset < first.node_total) nodes.push(...next.nodes)
    if (linkOffset < first.link_total) links.push(...next.links)
    nodeOffset += next.nodes.length
    linkOffset += next.links.length
  }
  return {
    nodes,
    links,
    nodeTotal: first.node_total,
    linkTotal: first.link_total,
  }
}

export function useGraph() {
  return useQuery({ queryKey: graphKeys.window, queryFn: fetchFullGraph })
}

export function useNetworkHealth(enabled = true) {
  return useQuery({
    queryKey: graphKeys.health,
    queryFn: () => unwrap(api.GET('/api/graph/health')),
    enabled,
  })
}

export function usePath(first: number | null, second: number | null) {
  return useQuery({
    queryKey: graphKeys.path(first ?? 0, second ?? 0),
    queryFn: () =>
      unwrap(
        api.GET('/api/graph/path', {
          params: { query: { a: first ?? 0, b: second ?? 0 } },
        })
      ),
    enabled: first !== null && second !== null,
  })
}

function useGraphMutation<TInput, TOutput>(
  writes: readonly WriteTarget[],
  run: (input: TInput) => Promise<TOutput>
) {
  const client = useQueryClient()
  return useMutation({
    writes,
    mutationFn: run,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: graphKeys.all })
      void client.invalidateQueries({ queryKey: queryKeys.jobs.all })
    },
  })
}

export function useRepairNetwork() {
  return useGraphMutation([{ method: 'POST', path: '/api/graph/repair' }], () =>
    unwrap(api.POST('/api/graph/repair'))
  )
}

export function useFateLink() {
  return useGraphMutation(
    [{ method: 'POST', path: '/api/graph/fate-link' }],
    (request: FateLinkRequest) =>
      unwrap(api.POST('/api/graph/fate-link', { body: request }))
  )
}

export function useStopFateLink() {
  return useGraphMutation(
    [{ method: 'POST', path: '/api/graph/fate-link/stop' }],
    () => unwrap(api.POST('/api/graph/fate-link/stop'))
  )
}

export function isFateLinkJob(job: components['schemas']['JobResponse']) {
  return (
    job.kind === 'content' &&
    'related' in job.params &&
    'full' in job.params &&
    (job.status === 'running' || job.status === 'queued')
  )
}

export function useFateLinkJob() {
  return useQuery({
    queryKey: queryKeys.jobs.list(JOB_SCAN_LIMIT),
    queryFn: () => fetchJobs(JOB_SCAN_LIMIT),
    select: (jobs) => jobs.find(isFateLinkJob) ?? null,
  })
}
