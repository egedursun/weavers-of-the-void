import { Layers, Orbit, Workflow } from 'lucide-react'
import { EntityLink, Medallion, PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  type ClusterRecord,
  type CosmographyCatalog,
  type GalaxyRecord,
  catalogLabel,
} from './api'
import { NUCLEI } from './labels'
import { type Ladder } from './ladder'
import { Chip, Meter } from './parts'

function GalaxyTile({
  galaxy,
  catalog,
}: {
  galaxy: GalaxyRecord
  catalog: CosmographyCatalog | undefined
}) {
  const nucleus = NUCLEI[galaxy.nucleus]
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Orbit} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <EntityLink kind='galaxy' id={String(galaxy.id)}>
            {galaxy.name}
          </EntityLink>
          <Muted as='span' variant='caption' truncate>
            {catalogLabel(catalog?.galaxy_types, galaxy.galaxy_type)}
          </Muted>
        </div>
        <Chip icon={nucleus.icon}>{nucleus.label}</Chip>
      </div>
      <Meter
        label='Star formation'
        value={galaxy.star_formation}
        tone='success'
      />
      {galaxy.merging_with_galaxy_id !== null && (
        <Meter label='Merging' value={galaxy.merge_progress} tone='warning' />
      )}
    </li>
  )
}

function ClusterBranch({
  cluster,
  ladder,
  catalog,
}: {
  cluster: ClusterRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const galaxies = ladder.galaxiesIn(cluster.id)
  const children = ladder.childClusters(cluster.id)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border border-dashed p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Workflow} tone='verdigris' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <EntityLink kind='cluster' id={String(cluster.id)}>
            {cluster.name}
          </EntityLink>
          <Muted as='span' variant='caption' truncate>
            {`${catalogLabel(catalog?.cluster_kinds, cluster.cluster_kind)} · ${galaxies.length} galaxies`}
          </Muted>
        </div>
      </div>
      {children.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          {children.map((child) => (
            <ClusterBranch
              key={child.id}
              cluster={child}
              ladder={ladder}
              catalog={catalog}
            />
          ))}
        </ul>
      )}
      {galaxies.length > 0 && (
        <PagedList
          items={galaxies}
          initial={6}
          noun={['galaxy', 'galaxies']}
          className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
          itemKey={(item) => item.id}
        >
          {(galaxy) => <GalaxyTile galaxy={galaxy} catalog={catalog} />}
        </PagedList>
      )}
    </li>
  )
}

export function ScaleTree({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  return (
    <ul className='flex min-w-0 flex-col gap-3'>
      {ladder.data.dimensions.map((dimension) => {
        const clusters = ladder.clustersIn(dimension.id)
        const loose = ladder.looseGalaxies(dimension.id)
        return (
          <li
            key={dimension.id}
            className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'
          >
            <div className='flex min-w-0 flex-wrap items-center gap-3'>
              <Medallion icon={Layers} tone='info' />
              <div className='flex min-w-0 flex-1 basis-48 flex-col'>
                <EntityLink kind='dimension' id={String(dimension.id)}>
                  {dimension.name}
                </EntityLink>
                <Text as='span' variant='caption'>
                  {catalogLabel(
                    catalog?.dimension_kinds,
                    dimension.dimension_kind
                  )}
                </Text>
              </div>
              <div className='grid min-w-0 flex-1 basis-60 grid-cols-2 gap-2'>
                <Meter label='Veil' value={dimension.veil} tone='info' />
                <Meter
                  label='Stability'
                  value={dimension.stability}
                  tone='verdigris'
                />
              </div>
            </div>
            {clusters.length + loose.length === 0 ? (
              <Muted variant='caption'>
                Nothing has been gathered in this dimension yet.
              </Muted>
            ) : (
              <ul className='flex min-w-0 flex-col gap-2'>
                {clusters.map((cluster) => (
                  <ClusterBranch
                    key={cluster.id}
                    cluster={cluster}
                    ladder={ladder}
                    catalog={catalog}
                  />
                ))}
                {loose.map((galaxy) => (
                  <GalaxyTile
                    key={galaxy.id}
                    galaxy={galaxy}
                    catalog={catalog}
                  />
                ))}
              </ul>
            )}
          </li>
        )
      })}
    </ul>
  )
}
