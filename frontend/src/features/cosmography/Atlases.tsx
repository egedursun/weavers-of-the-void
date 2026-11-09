import { Layers, Orbit } from 'lucide-react'
import {
  EmptyState,
  EntityLink,
  Medallion,
  PagedList,
  Section,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { GalaxyMap } from './GalaxyMap'
import { type CosmographyCatalog, catalogLabel } from './api'
import { CAUSALITIES, GALAXY_AGES, NUCLEI } from './labels'
import { type Ladder } from './ladder'
import { Chip, Meter } from './parts'

export function GalaxyAtlas({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const galaxies = ladder.data.galaxies
  return (
    <Section
      id='cosmography-galaxies'
      title='Galaxies'
      description='Every galaxy with its arms, structures and stars. Open one to shape it.'
      icon={Orbit}
      tone='gold'
    >
      {galaxies.length === 0 ? (
        <EmptyState
          icon={Orbit}
          size='compact'
          title='No galaxy yet'
          description='Set one with the forms above; until then the stars wander between galaxies.'
        />
      ) : (
        <PagedList
          items={galaxies}
          initial={4}
          noun={['galaxy', 'galaxies']}
          className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'
          itemKey={(row) => row.id}
        >
          {(galaxy) => (
            <li className='flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-3'>
              <div className='flex min-w-0 items-center gap-2'>
                <Medallion
                  icon={NUCLEI[galaxy.nucleus].icon}
                  tone={NUCLEI[galaxy.nucleus].tone}
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col'>
                  <EntityLink kind='galaxy' id={String(galaxy.id)}>
                    {galaxy.name}
                  </EntityLink>
                  <Muted as='span' variant='caption' truncate>
                    {`${catalogLabel(catalog?.galaxy_types, galaxy.galaxy_type)} · ${GALAXY_AGES[galaxy.age_stage]}`}
                  </Muted>
                </div>
                <Chip>{NUCLEI[galaxy.nucleus].label}</Chip>
              </div>
              <GalaxyMap
                galaxy={galaxy}
                structures={ladder.data.structures.filter(
                  (row) => row.galaxy_id === galaxy.id
                )}
                stars={ladder.data.stars
                  .filter((row) => row.galaxy_id === galaxy.id)
                  .map((row) => ({
                    id: row.id,
                    name: row.name,
                    x: row.x,
                    y: row.y,
                  }))}
              />
              <Meter
                label='Star formation'
                value={galaxy.star_formation}
                tone='success'
              />
            </li>
          )}
        </PagedList>
      )}
    </Section>
  )
}

export function DimensionAtlas({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const dimensions = ladder.data.dimensions
  return (
    <Section
      id='cosmography-dimensions'
      title='Dimensions'
      description='Every layer of the one cosmos, with its veil, its stability and how its time runs against the prime.'
      icon={Layers}
      tone='info'
    >
      {dimensions.length === 0 ? (
        <EmptyState
          icon={Layers}
          size='compact'
          title='No dimension yet'
          description='The first epoch lays the prime dimension; you can bring one into being above.'
        />
      ) : (
        <PagedList
          items={dimensions}
          initial={6}
          noun={['dimension', 'dimensions']}
          className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3'
          itemKey={(row) => row.id}
        >
          {(dimension) => (
            <li className='flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-3'>
              <div className='flex min-w-0 items-center gap-2'>
                <Medallion icon={Layers} tone='info' size='sm' />
                <div className='flex min-w-0 flex-1 flex-col'>
                  <EntityLink kind='dimension' id={String(dimension.id)}>
                    {dimension.name}
                  </EntityLink>
                  <Muted as='span' variant='caption' truncate>
                    {`${catalogLabel(catalog?.dimension_kinds, dimension.dimension_kind)} · time ×${dimension.time_factor}`}
                  </Muted>
                </div>
                <Chip>{CAUSALITIES[dimension.causality]}</Chip>
              </div>
              <Meter label='Veil' value={dimension.veil} tone='info' />
              <Meter
                label='Stability'
                value={dimension.stability}
                tone='success'
              />
              <Meter
                label='Hostility'
                value={dimension.hostility}
                tone='destructive'
              />
            </li>
          )}
        </PagedList>
      )}
    </Section>
  )
}
