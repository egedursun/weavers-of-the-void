import { useState } from 'react'
import { Eye, Shield, Split, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { Button } from '@/components/ui/button'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { RiftControl, useRiftControls } from './RiftControl'
import { type RiftRecord, useCosmography, useCosmographyAction } from './api'
import { RIFT_CAUSES, RIFT_STATES } from './labels'
import { type Ladder, ladderOf, nameTable } from './ladder'
import {
  Chip,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordPick,
  RecordRow,
} from './parts'

const OPEN = new Set(['opening', 'open', 'closing'])

function RiftRow({
  rift,
  ladder,
  worldNames,
}: {
  rift: RiftRecord
  ladder: Ladder
  worldNames: Record<string, string>
}) {
  const edit = useCosmographyAction(
    'rift:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      rift_id: rift.id,
      ...vars,
    })
  )
  const seal = useCosmographyAction(
    'rift:seal',
    (_: void) => ({ rift_id: rift.id }),
    'The rift is sealed'
  )
  const remove = useCosmographyAction(
    'rift:delete',
    (_: void) => ({ rift_id: rift.id }),
    'The rift is gone from the record'
  )
  const controls = useRiftControls()
  const busy =
    edit.isPending || seal.isPending || remove.isPending ? 'Working' : null
  const state = RIFT_STATES[rift.state]
  const open = OPEN.has(rift.state)
  return (
    <RecordRow
      icon={state.icon}
      tone={state.tone}
      title={`${worldNames[String(rift.world_id)] ?? 'A world'} into ${ladder.names.get(rift.dimension_id) ?? 'another dimension'}`}
      caption={`${state.label} · ${RIFT_CAUSES[rift.cause]} · opened in epoch ${rift.opened_epoch}${rift.opened_by_node_id !== null ? ` by ${ladder.names.get(rift.opened_by_node_id) ?? 'a god'}` : ''}${rift.sealed_epoch !== null ? ` · closed in epoch ${rift.sealed_epoch}` : ''}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            act={seal}
            size='sm'
            variant='outline'
            disabled={busy !== null || !open}
            disabledReason={
              busy ?? (open ? undefined : 'This rift is already closed')
            }
            onClick={() => seal.mutate()}
          >
            <Shield />
            Seal
          </Button>
          <Button
            act={remove}
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Remove
          </Button>
        </div>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <Meter label='Size' value={rift.size} tone='destructive' />
        <Meter label='Stability' value={rift.stability} tone='verdigris' />
      </div>
      {rift.target_world_id !== null && (
        <Muted variant='caption'>
          A passage leads to{' '}
          <EntityLink kind='world' id={String(rift.target_world_id)}>
            {worldNames[String(rift.target_world_id)] ?? 'a world'}
          </EntityLink>
        </Muted>
      )}
      <RecordEditor
        act={edit}
        title='Reshape this rift'
        note='Size and stability you set are held; a rift at no stability collapses.'
        fields={[
          { key: 'size', label: 'Size', kind: 'number', min: 0, max: 100 },
          {
            key: 'stability',
            label: 'Stability',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'state',
            label: 'State',
            kind: 'pick',
            table: Object.fromEntries(
              Object.entries(RIFT_STATES).map(([key, value]) => [
                key,
                value.label,
              ])
            ),
          },
          {
            key: 'target_world_id',
            label: 'Passage to',
            kind: 'pick',
            table: worldNames,
          },
        ]}
        locked={rift.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
      <RiftControl
        riftId={rift.id}
        control={controls.data?.controls.find((row) => row.rift_id === rift.id)}
        blocked={busy}
      />
    </RecordRow>
  )
}

function OpenRiftForm({
  ladder,
  worldNames,
  openCount,
}: {
  ladder: Ladder
  worldNames: Record<string, string>
  openCount: number
}) {
  const [world, setWorld] = useState('')
  const [region, setRegion] = useState<number | null>(null)
  const [dimension, setDimension] = useState('')
  const [target, setTarget] = useState('')
  const open = useCosmographyAction(
    'rift:open',
    (_: void) => ({
      world_id: Number(world),
      region_id: region,
      dimension_id: Number(dimension),
      target_world_id: target ? Number(target) : null,
    }),
    'A rift tore open'
  )
  const busy = open.isPending ? 'The rift is tearing' : null
  const missing =
    world === '' || dimension === ''
      ? 'Choose a world and a dimension first'
      : null
  return (
    <ForgeCard
      icon={Split}
      tone='danger'
      title='Tear a rift'
      note='Open a region of a world onto another dimension; a passage may lead on to a second world.'
      columns={4}
      meta={<Chip icon={Eye}>{`${openCount} open now`}</Chip>}
      action={
        <Button
          act={open}
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => open.mutate()}
        >
          <Split />
          Tear the rift
        </Button>
      }
    >
      <MindPicker
        label='World'
        value={world}
        table={worldNames}
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
      <MindPicker
        label='Into dimension'
        value={dimension}
        table={nameTable(ladder.data.dimensions)}
        blocked={
          busy ??
          (ladder.data.dimensions.length < 2
            ? 'A rift needs a second dimension'
            : null)
        }
        onPick={setDimension}
      />
      <MindPicker
        label='Passage to world'
        value={target}
        table={worldNames}
        blocked={busy}
        onPick={setTarget}
      />
    </ForgeCard>
  )
}

export function RiftsPanel({
  ladder,
  worldId,
  dimensionId,
}: {
  ladder: Ladder
  worldId?: number
  dimensionId?: number
}) {
  const worldNames = ladder.data.world_names
  const rifts = ladder.data.rifts.filter(
    (row) =>
      (worldId === undefined || row.world_id === worldId) &&
      (dimensionId === undefined || row.dimension_id === dimensionId)
  )
  return (
    <Section
      id='section-rifts'
      title='Rifts'
      description='Tears between the regions of worlds and other dimensions.'
      icon={Eye}
      tone='danger'
    >
      <div data-surface='RiftsPanel' className='flex min-w-0 flex-col gap-3'>
        {rifts.length === 0 ? (
          <EmptyState
            icon={Eye}
            size='inline'
            title='No rift is open'
            description='The veils hold; tear one below.'
          />
        ) : (
          <PagedList
            items={rifts}
            initial={5}
            noun={['rift', 'rifts']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.id}
          >
            {(row) => (
              <RiftRow rift={row} ladder={ladder} worldNames={worldNames} />
            )}
          </PagedList>
        )}
        <OpenRiftForm
          ladder={ladder}
          worldNames={worldNames}
          openCount={rifts.filter((row) => OPEN.has(row.state)).length}
        />
      </div>
    </Section>
  )
}

export function RiftsForWorld({ worldId }: { worldId: number }) {
  const view = useCosmography()
  if (!view.data) return null
  return <RiftsPanel ladder={ladderOf(view.data)} worldId={worldId} />
}
