import { useState } from 'react'
import { Eye, Telescope } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { MindPicker } from '@/features/entity/mind/parts'
import { useCosmography, useCosmographyAction } from './api'
import { OMENS } from './labels'
import { RecordPick, RecordRow } from './parts'

type Omen = keyof typeof OMENS
type Order = { people_id: number; reading: Omen | null }

const OMEN_NAMES = Object.fromEntries(
  Object.entries(OMENS).map(([key, value]) => [key, value.label])
)

export function CelestialReadingsSection({
  celestialId,
}: {
  celestialId: number
}) {
  const view = useCosmography()
  const [people, setPeople] = useState<number | null>(null)
  const [reading, setReading] = useState('')
  const set = useCosmographyAction<Order>(
    'celestial_reading:set',
    (vars) => ({ celestial_id: celestialId, ...vars }),
    'The reading of the sky is set'
  )
  const busy = set.isPending ? 'Working' : null
  const readings = (view.data?.readings ?? []).filter(
    (row) => row.celestial_entity_id === celestialId
  )
  const missing =
    people === null || reading === ''
      ? 'Choose a people and a reading first'
      : null
  return (
    <Section
      id='section-celestial-readings'
      title='How peoples read it'
      description='Each people reads this body as a good or an evil sign; their rites and courage follow the reading.'
      icon={Telescope}
      tone='info'
    >
      <div
        data-surface='CelestialReadingsSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {view.isPending ? (
          <LoadingBlock label='Reading the sky' />
        ) : readings.length === 0 ? (
          <EmptyState
            icon={Telescope}
            size='compact'
            title='No people reads it yet'
            description='Peoples read the sky as they watch it, or set a reading below.'
          />
        ) : (
          <PagedList
            items={readings}
            initial={6}
            noun={['reading', 'readings']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.people_entity_id}
          >
            {(row) => {
              const omen = OMENS[row.reading]
              return (
                <RecordRow
                  icon={omen.icon}
                  tone={omen.tone}
                  title={
                    <EntityLink kind='entity' id={String(row.people_entity_id)}>
                      {view.data?.people_names[String(row.people_entity_id)] ??
                        `People #${row.people_entity_id}`}
                    </EntityLink>
                  }
                  caption={`${omen.label} since epoch ${row.epoch}${row.locked.length > 0 ? ' · held' : ''}`}
                  aside={
                    <Button
                      size='sm'
                      variant='ghost'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        set.mutate({
                          people_id: row.people_entity_id,
                          reading: null,
                        })
                      }
                    >
                      <Eye />
                      Let them read it again
                    </Button>
                  }
                />
              )
            }}
          </PagedList>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2 rounded-lg border border-dashed p-3 sm:grid-cols-3'>
          <RecordPick
            label='People'
            types={['people']}
            value={people}
            onChange={setPeople}
          />
          <MindPicker
            label='Reading'
            value={reading}
            table={OMEN_NAMES}
            blocked={busy}
            onPick={setReading}
          />
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() =>
              people !== null &&
              set.mutate({ people_id: people, reading: reading as Omen })
            }
          >
            <Telescope />
            Set the reading
          </Button>
        </div>
      </div>
    </Section>
  )
}
