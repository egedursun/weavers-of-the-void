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
  starsIn: (galaxyId: number) => Cosmography['stars']
  placementsIn: (galaxyId: number) => Cosmography['placements']
  prime: DimensionRecord | null
}

function grouped<T, K>(
  rows: readonly T[],
  keyOf: (row: T) => K | null
): Map<K, T[]> {
  const groups = new Map<K, T[]>()
  for (const row of rows) {
    const key = keyOf(row)
    if (key === null) continue
    const group = groups.get(key)
    if (group) group.push(row)
    else groups.set(key, [row])
  }
  return groups
}

export function ladderOf(data: Cosmography): Ladder {
  const names = new Map<number, string>()
  for (const row of [...data.dimensions, ...data.clusters, ...data.galaxies])
    names.set(row.id, row.name)
  for (const table of [
    data.actor_names,
    data.people_names,
    data.world_names,
    data.star_names,
  ])
    for (const [id, name] of Object.entries(table ?? {}))
      if (!names.has(Number(id))) names.set(Number(id), name)
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
  const topClusters = grouped(data.clusters, (row) =>
    row.parent_cluster_id === null
      ? (row.dimension_id ?? prime?.id ?? null)
      : null
  )
  const children = grouped(data.clusters, (row) => row.parent_cluster_id)
  const members = grouped(data.galaxies, (row) => row.cluster_id)
  const loose = grouped(data.galaxies, (row) =>
    row.cluster_id === null ? (row.dimension_id ?? prime?.id ?? null) : null
  )
  const stars = grouped(data.stars, (row) => row.galaxy_id)
  const placements = grouped(data.placements, (row) => row.galaxy_id)
  return {
    data,
    names,
    dimensionOfCluster,
    dimensionOfGalaxy,
    clustersIn: (dimensionId) => topClusters.get(dimensionId) ?? [],
    childClusters: (clusterId) => children.get(clusterId) ?? [],
    galaxiesIn: (clusterId) => members.get(clusterId) ?? [],
    looseGalaxies: (dimensionId) => loose.get(dimensionId) ?? [],
    starsIn: (galaxyId) => stars.get(galaxyId) ?? [],
    placementsIn: (galaxyId) => placements.get(galaxyId) ?? [],
    prime,
  }
}

export function nameTable(
  rows: readonly { id: number; name: string }[]
): Record<string, string> {
  return Object.fromEntries(rows.map((row) => [String(row.id), row.name]))
}
