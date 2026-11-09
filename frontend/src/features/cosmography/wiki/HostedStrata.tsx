import { Ghost } from 'lucide-react'
import { plural } from '@/lib/units'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import { STRATA } from '@/features/entity/faith/labels'
import { type HostedStratumRecord } from '../api'
import { Chip, RecordRow } from '../parts'

export function HostedStrata({
  name,
  strata,
}: {
  name: string
  strata: readonly HostedStratumRecord[]
}) {
  return (
    <Section
      id='section-hosted-strata'
      title='Afterlife strata here'
      description={`Strata of the dead that lie in ${name}: souls judged into them go to this dimension. A god of Death or Sleep who rules it draws the dead here first. Move a stratum from the afterlife panel of its realm.`}
      icon={Ghost}
      tone='muted'
    >
      {strata.length === 0 ? (
        <EmptyState
          icon={Ghost}
          size='inline'
          title='No stratum of the dead lies here'
          description='An underworld, a heaven or a hell holds the strata whose kind fits it.'
        />
      ) : (
        <PagedList
          items={[...strata]}
          initial={6}
          noun={['stratum', 'strata']}
          className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
          itemKey={(row) => String(row.id)}
        >
          {(row) => (
            <RecordRow
              icon={STRATA[row.kind]?.icon ?? Ghost}
              tone={STRATA[row.kind]?.tone ?? 'muted'}
              title={row.name}
              caption={
                row.realm ? (
                  <EntityLink kind='entity' id={String(row.realm.id)}>
                    {row.realm.name}
                  </EntityLink>
                ) : (
                  'No realm'
                )
              }
            >
              <div className='flex min-w-0 flex-wrap gap-1'>
                <Chip>{STRATA[row.kind]?.label ?? row.kind}</Chip>
                <Chip icon={Ghost}>{plural(row.population, 'soul')}</Chip>
              </div>
            </RecordRow>
          )}
        </PagedList>
      )}
    </Section>
  )
}
