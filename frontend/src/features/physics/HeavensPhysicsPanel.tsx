import { Gem, Orbit, Pickaxe, Zap } from 'lucide-react'
import { EmptyState, EntityLink, PagedList } from '@/components/domain'
import { RecordRow } from '@/features/cosmography/parts'
import { CosmicFeaturesPanel } from './CosmicFeaturesPanel'
import { ImpactsPanel } from './ImpactsPanel'
import { TerraformPanel } from './TerraformPanel'
import { useHeavensPhysics } from './api'
import { fixed } from './format'
import { SYSTEM_ROLES } from './labels'
import { QuerySection } from './parts'

export function HeavensPhysicsPanel() {
  const query = useHeavensPhysics()
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <QuerySection
        id='section-heavens-systems'
        title='Star systems'
        description='Every system of the heavens, its stars and the band where its worlds are temperate.'
        icon={Orbit}
        tone='info'
        query={query}
      >
        {(view) =>
          view.systems.length === 0 ? (
            <EmptyState
              icon={Orbit}
              size='inline'
              title='No star stands in a system yet'
              description='Every star gathers into its own system at the next epoch; join them from a star page.'
            />
          ) : (
            <PagedList
              items={[...view.systems]}
              initial={8}
              noun={['system', 'systems']}
              className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
              itemKey={(row) => String(row.id)}
            >
              {(row) => (
                <RecordRow
                  icon={Orbit}
                  tone='info'
                  title={row.name}
                  caption={`Temperate from ${fixed(row.band_inner)} to ${fixed(row.band_outer)} orbits · stars ${fixed(row.separation)} orbits apart`}
                >
                  <PagedList
                    items={row.members}
                    initial={12}
                    noun={['entry', 'entries']}
                    as='div'
                    className='flex min-w-0 flex-wrap gap-2'
                    itemKey={(member) => member.star_id}
                  >
                    {(member) => (
                      <EntityLink
                        key={member.star_id}
                        kind='star'
                        id={String(member.star_id)}
                      >
                        {`${member.name} (${SYSTEM_ROLES[member.role].label.toLowerCase()})`}
                      </EntityLink>
                    )}
                  </PagedList>
                </RecordRow>
              )}
            </PagedList>
          )
        }
      </QuerySection>
      <QuerySection
        id='section-heavens-features'
        title='Features of the heavens'
        description='Every asteroid field, wormhole, comet, rogue world and gravity well.'
        icon={Gem}
        tone='gold'
        query={query}
      >
        {(view) => <CosmicFeaturesPanel features={view.features} />}
      </QuerySection>
      <QuerySection
        id='section-heavens-impacts'
        title='Impacts'
        description='Every body that fell or is falling on a world.'
        icon={Zap}
        tone='danger'
        query={query}
      >
        {(view) => (
          <ImpactsPanel
            worldId={null}
            impacts={view.impacts}
            epoch={view.epoch}
          />
        )}
      </QuerySection>
      <QuerySection
        id='section-heavens-terraform'
        title='Terraforming'
        description='Every work that reshapes a world.'
        icon={Pickaxe}
        tone='verdigris'
        query={query}
      >
        {(view) => (
          <TerraformPanel worldId={null} projects={view.terraforming} />
        )}
      </QuerySection>
    </div>
  )
}
