import { useState } from 'react'
import { Link2, Scale, Unlink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import {
  type DimensionRecord,
  type HeldLawRecord,
  cosmographyKeys,
  useCosmographyAction,
} from '../api'
import { Chip, ForgeCard, Meter, RecordPick, RecordRow } from '../parts'

export function DimensionLaws({
  dimension,
  laws,
  worldCount,
}: {
  dimension: DimensionRecord
  laws: readonly HeldLawRecord[]
  worldCount: number
}) {
  const [law, setLaw] = useState<number | null>(null)
  const refresh = [cosmographyKeys.wiki(dimension.id)]
  const bind = useCosmographyAction<number>(
    'dimension:bind_law',
    (lawId) => ({ dimension_id: dimension.id, law_id: lawId }),
    'The law holds across the dimension',
    refresh
  )
  const release = useCosmographyAction<number>(
    'dimension:release_law',
    (lawId) => ({ law_id: lawId }),
    'The law holds only on its own world again',
    refresh
  )
  const busy = bind.isPending || release.isPending ? 'Working' : null
  const missing =
    worldCount === 0
      ? `No world lies in ${dimension.name} yet; a law needs a world to hold from`
      : law === null
        ? 'Choose a natural law first'
        : null
  return (
    <Section
      id='section-dimension-laws'
      title='Laws that hold here'
      description='Natural laws in force on every world of this dimension: those its kind carries and those bound across it.'
      icon={Scale}
      tone='verdigris'
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {laws.length === 0 ? (
          <EmptyState
            icon={Scale}
            size='inline'
            title='No law holds across it'
            description='Its kind carries none; bind a natural law below.'
          />
        ) : (
          <PagedList
            items={[...laws]}
            initial={6}
            noun={['law', 'laws']}
            className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
            itemKey={(row) => `${row.law}-${row.entity_id ?? 'kind'}`}
          >
            {(row) => (
              <RecordRow
                icon={Scale}
                tone={row.entity_id === null ? 'info' : 'verdigris'}
                title={
                  row.entity_id !== null ? (
                    <EntityLink kind='entity' id={String(row.entity_id)}>
                      {row.name ?? row.label}
                    </EntityLink>
                  ) : (
                    row.label
                  )
                }
                caption={row.description}
                aside={
                  row.entity_id === null ? (
                    <Chip>By its kind</Chip>
                  ) : (
                    <Button
                      size='sm'
                      variant='ghost'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        row.entity_id !== null && release.mutate(row.entity_id)
                      }
                    >
                      <Unlink />
                      Release
                    </Button>
                  )
                }
              >
                <Meter label='Strength' value={row.strength} tone='success' />
              </RecordRow>
            )}
          </PagedList>
        )}
        <ForgeCard
          icon={Link2}
          tone='verdigris'
          title='Bind a law across this dimension'
          note='The law then holds on every world inside it, not only on its own.'
          columns={2}
          meta={<Chip icon={Scale}>{`${laws.length} in force`}</Chip>}
          action={
            <Button
              size='sm'
              disabled={busy !== null || missing !== null}
              disabledReason={busy ?? missing ?? undefined}
              onClick={() => law !== null && bind.mutate(law)}
            >
              <Link2 />
              Bind it
            </Button>
          }
        >
          <RecordPick
            label='Natural law'
            types={['natural_law']}
            value={law}
            onChange={setLaw}
          />
        </ForgeCard>
      </div>
    </Section>
  )
}
