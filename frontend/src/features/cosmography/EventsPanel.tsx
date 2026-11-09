import { useState } from 'react'
import { Sparkles, Trash2, Zap } from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { Button } from '@/components/ui/button'
import { EmptyState, PagedList, Section } from '@/components/domain'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import {
  type CosmographyCatalog,
  type DimensionalEventRecord,
  type GalacticEventRecord,
  catalogLabel,
  catalogTable,
  useCosmographyAction,
} from './api'
import { type Ladder, nameTable } from './ladder'
import { Chip, ForgeCard, RecordEditor, RecordRow } from './parts'

function GalacticEventRow({
  event,
  ladder,
  catalog,
}: {
  event: GalacticEventRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction(
    'galactic_event:edit',
    (values: EditValues) => ({
      event_id: event.id,
      values,
      release: [],
    })
  )
  const remove = useCosmographyAction(
    'galactic_event:delete',
    (_: void) => ({ event_id: event.id }),
    'The event is struck from the record'
  )
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  return (
    <RecordRow
      icon={Sparkles}
      tone={event.active ? 'warning' : 'muted'}
      title={`${catalogLabel(catalog?.galactic_events, event.kind)} · ${ladder.names.get(event.galaxy_id) ?? 'a galaxy'}`}
      caption={event.text ?? undefined}
      aside={
        <div className='flex shrink-0 items-center gap-1'>
          <Chip>{event.active ? 'Under way' : `Epoch ${event.epoch}`}</Chip>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Strike
          </Button>
        </div>
      }
    >
      <RecordEditor
        title='Reshape this event'
        note='Its strength and how long it lasts.'
        fields={[
          {
            key: 'intensity',
            label: 'Intensity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'until_epoch',
            label: 'Lasts until epoch',
            kind: 'number',
            min: event.epoch,
          },
        ]}
        locked={[]}
        busy={busy}
        saveLabel='Set the event this way'
        onSave={(values) => edit.mutate(values)}
        onRelease={() => undefined}
      />
    </RecordRow>
  )
}

function DimensionalEventRow({
  event,
  ladder,
  catalog,
}: {
  event: DimensionalEventRecord
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const edit = useCosmographyAction(
    'dimensional_event:edit',
    (values: EditValues) => ({
      event_id: event.id,
      values,
      release: [],
    })
  )
  const remove = useCosmographyAction(
    'dimensional_event:delete',
    (_: void) => ({ event_id: event.id }),
    'The event is struck from the record'
  )
  const busy = edit.isPending || remove.isPending ? 'Working' : null
  return (
    <RecordRow
      icon={Zap}
      tone={event.active ? 'danger' : 'muted'}
      title={`${catalogLabel(catalog?.dimensional_events, event.kind)} · ${ladder.names.get(event.dimension_id) ?? 'a dimension'}`}
      caption={event.text ?? undefined}
      aside={
        <div className='flex shrink-0 items-center gap-1'>
          <Chip>{event.active ? 'Under way' : `Epoch ${event.epoch}`}</Chip>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Strike
          </Button>
        </div>
      }
    >
      <RecordEditor
        title='Reshape this event'
        note='Its strength and how long it lasts.'
        fields={[
          {
            key: 'intensity',
            label: 'Intensity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'until_epoch',
            label: 'Lasts until epoch',
            kind: 'number',
            min: event.epoch,
          },
        ]}
        locked={[]}
        busy={busy}
        saveLabel='Set the event this way'
        onSave={(values) => edit.mutate(values)}
        onRelease={() => undefined}
      />
    </RecordRow>
  )
}

function TriggerForm({
  ladder,
  catalog,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
}) {
  const [galaxy, setGalaxy] = useState('')
  const [galacticKind, setGalacticKind] = useState('')
  const [galacticPower, setGalacticPower] = useState('50')
  const [dimension, setDimension] = useState('')
  const [planarKind, setPlanarKind] = useState('')
  const [planarPower, setPlanarPower] = useState('50')
  const galactic = useCosmographyAction(
    'galactic_event:trigger',
    (_: void) => ({
      galaxy_id: Number(galaxy),
      kind: galacticKind as ActionBody<'galactic_event:trigger'>['kind'],
      intensity: Number(galacticPower) || 50,
    }),
    'The galaxy answers your hand'
  )
  const planar = useCosmographyAction(
    'dimensional_event:trigger',
    (_: void) => ({
      dimension_id: Number(dimension),
      kind: planarKind as ActionBody<'dimensional_event:trigger'>['kind'],
      intensity: Number(planarPower) || 50,
    }),
    'The dimension answers your hand'
  )
  const busy =
    galactic.isPending || planar.isPending ? 'The heavens are moving' : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2'>
      <ForgeCard
        icon={Sparkles}
        tone='warning'
        title='A galactic event'
        note='Bring an event upon one galaxy and every star and world in it.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={busy !== null || galaxy === '' || galacticKind === ''}
            disabledReason={
              busy ??
              (galaxy === '' || galacticKind === ''
                ? 'Choose a galaxy and an event first'
                : undefined)
            }
            onClick={() => galactic.mutate()}
          >
            <Sparkles />
            Bring it about
          </Button>
        }
      >
        <MindPicker
          label='Galaxy'
          value={galaxy}
          table={nameTable(ladder.data.galaxies)}
          blocked={
            busy ??
            (ladder.data.galaxies.length === 0 ? 'No galaxy exists yet' : null)
          }
          onPick={setGalaxy}
        />
        <MindPicker
          label='Galactic event'
          value={galacticKind}
          table={catalogTable(catalog?.galactic_events)}
          blocked={busy}
          onPick={setGalacticKind}
        />
        <NumberField
          label='Intensity'
          value={galacticPower}
          min={0}
          max={100}
          disabled={busy !== null}
          onChange={setGalacticPower}
        />
      </ForgeCard>
      <ForgeCard
        icon={Zap}
        tone='info'
        title='A dimensional event'
        note='Bring an event upon one dimension and every world it holds.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={busy !== null || dimension === '' || planarKind === ''}
            disabledReason={
              busy ??
              (dimension === '' || planarKind === ''
                ? 'Choose a dimension and an event first'
                : undefined)
            }
            onClick={() => planar.mutate()}
          >
            <Zap />
            Bring it about
          </Button>
        }
      >
        <MindPicker
          label='Dimension'
          value={dimension}
          table={nameTable(ladder.data.dimensions)}
          blocked={
            busy ??
            (ladder.data.dimensions.length === 0
              ? 'No dimension exists yet'
              : null)
          }
          onPick={setDimension}
        />
        <MindPicker
          label='Dimensional event'
          value={planarKind}
          table={catalogTable(catalog?.dimensional_events)}
          blocked={busy}
          onPick={setPlanarKind}
        />
        <NumberField
          label='Intensity'
          value={planarPower}
          min={0}
          max={100}
          disabled={busy !== null}
          onChange={setPlanarPower}
        />
      </ForgeCard>
    </div>
  )
}

export function EventsPanel({
  ladder,
  catalog,
  galaxyId,
  dimensionId,
}: {
  ladder: Ladder
  catalog: CosmographyCatalog | undefined
  galaxyId?: number
  dimensionId?: number
}) {
  const galactic = ladder.data.galactic_events.filter((row) =>
    galaxyId === undefined
      ? dimensionId === undefined
      : row.galaxy_id === galaxyId
  )
  const planar = ladder.data.dimensional_events.filter((row) =>
    dimensionId === undefined
      ? galaxyId === undefined
      : row.dimension_id === dimensionId
  )
  return (
    <Section
      title='Events of the heavens'
      description='Galactic and dimensional events of the last ten epochs; those under way still act.'
      icon={Sparkles}
      tone='warning'
    >
      {galactic.length + planar.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          size='inline'
          title='The heavens are quiet'
          description='No galactic or dimensional event in the last ten epochs.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2'>
          <PagedList
            items={galactic}
            initial={5}
            noun={['galactic event', 'galactic events']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.id}
          >
            {(row) => (
              <GalacticEventRow event={row} ladder={ladder} catalog={catalog} />
            )}
          </PagedList>
          <PagedList
            items={planar}
            initial={5}
            noun={['dimensional event', 'dimensional events']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.id}
          >
            {(row) => (
              <DimensionalEventRow
                event={row}
                ladder={ladder}
                catalog={catalog}
              />
            )}
          </PagedList>
        </div>
      )}
      {galaxyId === undefined && dimensionId === undefined && (
        <TriggerForm ladder={ladder} catalog={catalog} />
      )}
    </Section>
  )
}
