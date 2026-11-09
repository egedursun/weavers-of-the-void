import { type QueryKey, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type Cosmography = Schema['CosmographyView']
export type CosmographyCatalog = Schema['CosmographyCatalog']
export type KindRecord = Schema['KindRecord']
export type DimensionRecord = Schema['DimensionRecord']
export type ClusterRecord = Schema['ClusterRecord']
export type GalaxyRecord = Schema['GalaxyRecord']
export type StructureRecord = Schema['StructureRecord']
export type GalacticEventRecord = Schema['GalacticEventRecord']
export type DimensionalEventRecord = Schema['DimensionalEventRecord']
export type RiftRecord = Schema['RiftRecord']
export type CosmicBeingRecord = Schema['CosmicBeingRecord']
export type PhenomenonRecord = Schema['PhenomenonRecord']
export type ReadingRecord = Schema['CelestialReadingRecord']
export type PlacementRecord = Schema['PlacementRecord']
export type StarRecord = Schema['StarRecord']
export type WorldRecord = Schema['WorldRecord']
export type RouteRecord = Schema['RouteRecord']
export type JourneyRecord = Schema['JourneyRecord']

export type ScaleWiki = Schema['ScaleWiki']
export type HeldLawRecord = Schema['HeldLawRecord']
export type HostedStratumRecord = Schema['HostedStratumRecord']
export type SkyWorshipView = Schema['SkyWorshipView']
export type SkyWorshipperRecord = Schema['SkyWorshipperRecord']

export const cosmographyKeys = {
  view: [...queryKeys.world.all, 'cosmography'] as const,
  catalog: [...queryKeys.world.all, 'cosmography-catalog'] as const,
  wiki: (nodeId: number) =>
    [...queryKeys.world.all, 'cosmography-wiki', nodeId] as const,
  worship: (nodeId: number) =>
    [...queryKeys.world.all, 'cosmography-worship', nodeId] as const,
}

export function useSkyWorship(nodeId: number) {
  return useQuery({
    queryKey: cosmographyKeys.worship(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/cosmography/nodes/{node_id}/worship', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useScaleWiki(nodeId: number) {
  return useQuery({
    queryKey: cosmographyKeys.wiki(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/cosmography/nodes/{node_id}/wiki', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useCosmography() {
  return useQuery({
    queryKey: cosmographyKeys.view,
    queryFn: () => unwrap(api.GET('/api/cosmography')),
  })
}

export function useCosmographyCatalog() {
  return useQuery({
    queryKey: cosmographyKeys.catalog,
    staleTime: Infinity,
    queryFn: () => unwrap(api.GET('/api/cosmography/catalog')),
  })
}

export type CosmographyAction =
  | 'dimension:create'
  | 'dimension:edit'
  | 'dimension:delete'
  | 'dimension:bind_law'
  | 'dimension:release_law'
  | 'heavens:worship'
  | 'cluster:create'
  | 'cluster:edit'
  | 'cluster:delete'
  | 'galaxy:create'
  | 'galaxy:edit'
  | 'galaxy:delete'
  | 'galactic_structure:create'
  | 'galactic_structure:edit'
  | 'galactic_structure:delete'
  | 'galactic_event:trigger'
  | 'galactic_event:edit'
  | 'galactic_event:delete'
  | 'dimensional_event:trigger'
  | 'dimensional_event:edit'
  | 'dimensional_event:delete'
  | 'rift:open'
  | 'rift:edit'
  | 'rift:seal'
  | 'rift:delete'
  | 'cosmic_being:call'
  | 'cosmic_being:edit'
  | 'cosmic_being:bind'
  | 'cosmic_being:banish'
  | 'phenomenon:create'
  | 'phenomenon:edit'
  | 'phenomenon:footprint'
  | 'phenomenon:contain'
  | 'star_life:edit'
  | 'world_life:edit'
  | 'route_flow:edit'
  | 'journey:load'
  | 'journey:release'
  | 'celestial_reading:set'
  | 'apocalypse:variant'
  | 'region_climate:turn'

export function runCosmography(
  name: CosmographyAction,
  body: Record<string, unknown>
) {
  return unwrap(
    api.POST(`/api/actions/${name}` as '/api/actions/galaxy:create', {
      body: body as never,
    })
  )
}

export function useCosmographyAction<T>(
  name: CosmographyAction,
  toBody: (vars: T) => Record<string, unknown>,
  success?: string,
  also: readonly QueryKey[] = []
) {
  return useGodAction<T>({
    run: (vars) => runCosmography(name, toBody(vars)),
    success,
    invalidate: [cosmographyKeys.view, ...also],
  })
}

export function catalogLabel(
  records: readonly KindRecord[] | undefined,
  value: string
): string {
  return (
    records?.find((record) => record.value === value)?.label ??
    value.replaceAll('_', ' ')
  )
}

export function catalogTable(
  records: readonly KindRecord[] | undefined
): Record<string, string> {
  return Object.fromEntries(
    (records ?? []).map((record) => [record.value, record.label])
  )
}
