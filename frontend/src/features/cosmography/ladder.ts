import type {
  ClusterRecord,
  Cosmography,
  DimensionRecord,
  GalaxyRecord,
} from './api'

export type Ladder = {
  data: Cosmography
  names: Map<number, string>
  dimensionOfCluster: (cluster: ClusterRecord) => number | null
  dimensionOfGalaxy: (galaxy: GalaxyRecord) => number | null
  clustersIn: (dimensionId: number) => ClusterRecord[]
  childClusters: (clusterId: number) => ClusterRecord[]
  galaxiesIn: (clusterId: number) => GalaxyRecord[]
  looseGalaxies: (dimensionId: number) => GalaxyRecord[]
  prime: DimensionRecord | null
}

export function ladderOf(data: Cosmography): Ladder {
  const names = new Map<number, string>()
  for (const row of [...data.dimensions, ...data.clusters, ...data.galaxies])
    names.set(row.id, row.name)
  const clusters = new Map(data.clusters.map((row) => [row.id, row]))
  const prime =
    data.dimensions.find((row) => row.dimension_kind === 'prime') ??
    data.dimensions[0] ??
    null
  const dimensionOfCluster = (cluster: ClusterRecord): number | null => {
    const seen = new Set<number>()
    let current: ClusterRecord | undefined = cluster
    while (current && !seen.has(current.id)) {
      seen.add(current.id)
      if (current.parent_cluster_id === null)
        return current.dimension_id ?? prime?.id ?? null
      current = clusters.get(current.parent_cluster_id)
    }
    return prime?.id ?? null
  }
  const dimensionOfGalaxy = (galaxy: GalaxyRecord): number | null => {
    if (galaxy.cluster_id !== null) {
      const cluster = clusters.get(galaxy.cluster_id)
      return cluster ? dimensionOfCluster(cluster) : (prime?.id ?? null)
    }
    return galaxy.dimension_id ?? prime?.id ?? null
  }
  return {
    data,
    names,
    dimensionOfCluster,
    dimensionOfGalaxy,
    clustersIn: (dimensionId) =>
      data.clusters.filter(
        (row) =>
          row.parent_cluster_id === null &&
          (row.dimension_id ?? prime?.id ?? null) === dimensionId
      ),
    childClusters: (clusterId) =>
      data.clusters.filter((row) => row.parent_cluster_id === clusterId),
    galaxiesIn: (clusterId) =>
      data.galaxies.filter((row) => row.cluster_id === clusterId),
    looseGalaxies: (dimensionId) =>
      data.galaxies.filter(
        (row) =>
          row.cluster_id === null &&
          (row.dimension_id ?? prime?.id ?? null) === dimensionId
      ),
    prime,
  }
}

export function nameTable(
  rows: readonly { id: number; name: string }[]
): Record<string, string> {
  return Object.fromEntries(rows.map((row) => [String(row.id), row.name]))
}
