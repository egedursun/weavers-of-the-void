import { useState } from 'react'
import { Ban, Crown, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type CosmicBeingRecord,
  type CosmographyCatalog,
  catalogLabel,
  catalogTable,
  useCosmography,
  useCosmographyAction,
} from './api'
import { BEING_AGENDAS, BEING_PHASES, BEING_SCALES } from './labels'
import { type Ladder, ladderOf, nameTable } from './ladder'
import { Meter, RecordEditor, RecordPick, RecordRow } from './parts'

const phaseTable = Object.fromEntries(
  Object.entries(BEING_PHASES).map(([key, value]) => [key, value.label])
)

export function BeingCard({
  being,
  ladder,
  catalog,
}: {
  being: CosmicBeingRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction<{
    values: Record<string, unknown>
    release: string[]
  }>('cosmic_being:edit', (vars) => ({ being_id: being.entity_id, ...vars }))
  const bind = useCosmographyAction<void>(
    'cosmic_being:bind',
    () => ({ being_id: being.entity_id }),
    'The being is bound to you'
  )
  const banish = useCosmographyAction<void>(
    'cosmic_being:banish',
    () => ({ being_id: being.entity_id }),
    'The being is banished'
  )
  const busy =
    edit.isPending || bind.isPending || banish.isPending ? 'Working' : null
  const phase = BEING_PHASES[being.phase]
  const bound = being.phase === 'bound'
  const banished = being.phase === 'banished'
  return (
    <RecordRow
      icon={phase.icon}
      tone={phase.tone}
      title={
        <EntityLink kind='entity' id={String(being.entity_id)}>
          {being.name}
        </EntityLink>
      }
      caption={`${catalogLabel(catalog?.being_kinds, being.being_kind)} · ${BEING_SCALES[being.scale]} scale · ${phase.label} · aim: ${BEING_AGENDAS[being.agenda].toLowerCase()}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || bound}
            disabledReason={busy ?? (bound ? 'It is already bound' : undefined)}
            onClick={() => bind.mutate()}
          >
            <Link2 />
            Bind
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null || banished}
            disabledReason={
              busy ?? (banished ? 'It is already banished' : undefined)
            }
            onClick={() => banish.mutate()}
          >
            <Ban />
            Banish
          </Button>
        </div>
      }
    >
      <Meter label='Might' value={being.might} tone='warning' />
      <RecordEditor
        title='Reshape this being'
        note='Might, phase, aim, scale and home you set are held until you release them.'
        fields={[
          { key: 'might', label: 'Might', kind: 'number', min: 0, max: 100 },
          { key: 'phase', label: 'Phase', kind: 'pick', table: phaseTable },
          { key: 'agenda', label: 'Aim', kind: 'pick', table: BEING_AGENDAS },
          { key: 'scale', label: 'Scale', kind: 'pick', table: BEING_SCALES },
          {
            key: 'home_dimension_id',
            label: 'Home dimension',
            kind: 'pick',
            table: nameTable(ladder.data.dimensions),
          },
          {
            key: 'galaxy_id',
            label: 'Galaxy it roams',
            kind: 'pick',
            table: nameTable(ladder.data.galaxies),
          },
        ]}
        locked={being.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function CallForm({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const [kind, setKind] = useState('')
  const [world, setWorld] = useState('')
  const [region, setRegion] = useState<number | null>(null)
  const call = useCosmographyAction<void>(
    'cosmic_being:call',
    () => ({ kind, world_id: Number(world), region_id: region }),
    'A cosmic being answers your call'
  )
  const busy = call.isPending ? 'The being is coming' : null
  const missing =
    kind === '' || world === '' ? 'Choose a kind and a world first' : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 rounded-lg border border-dashed p-3 md:grid-cols-3'>
      <MindPicker
        label='Kind'
        value={kind}
        table={catalogTable(catalog?.being_kinds)}
        blocked={busy}
        onPick={setKind}
      />
      <MindPicker
        label='World'
        value={world}
        table={ladder.data.world_names}
        blocked={busy}
        onPick={setWorld}
      />
      <RecordPick
        label='Region'
        types={['region']}
        value={region}
        onChange={setRegion}
        worldId={world ? Number(world) : undefined}
      />
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => call.mutate()}
      >
        <Crown />
        Call it
      </Button>
    </div>
  )
}

export function BeingsPanel({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  return (
    <Section
      id='section-cosmic-being'
      title='Cosmic beings'
      description='Beings of galaxies and dimensions, with their scale, phase and aim.'
      icon={Crown}
      tone='warning'
    >
      <div
        data-surface='CosmicBeingSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {ladder.data.beings.length === 0 ? (
          <EmptyState
            icon={Crown}
            size='compact'
            title='No cosmic being walks the cosmos'
            description='Call one below, or wait for the veils to thin.'
          />
        ) : (
          <PagedList
            items={ladder.data.beings}
            initial={5}
            noun={['being', 'beings']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.entity_id}
          >
            {(row) => (
              <BeingCard being={row} ladder={ladder} catalog={catalog} />
            )}
          </PagedList>
        )}
        <CallForm ladder={ladder} catalog={catalog} />
      </div>
    </Section>
  )
}

export function CosmicBeingSection({
  entityId,
  catalog,
}: {
  entityId: number
  catalog?: CosmographyCatalog
}) {
  const view = useCosmography()
  if (!view.data) return null
  const ladder = ladderOf(view.data)
  const being = view.data.beings.find((row) => row.entity_id === entityId)
  return (
    <Section
      id='section-cosmic-being'
      title='As a cosmic being'
      icon={Crown}
      tone='warning'
    >
      {being ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          <BeingCard being={being} ladder={ladder} catalog={catalog} />
        </ul>
      ) : (
        <EmptyState
          icon={Crown}
          size='compact'
          title='No profile yet'
          description='Its profile forms at the next epoch.'
        />
      )}
    </Section>
  )
}
