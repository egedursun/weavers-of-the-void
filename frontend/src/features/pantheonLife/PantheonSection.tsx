import { useState } from 'react'
import { CirclePlus, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import {
  type PantheonOfView,
  type PantheonTieView,
  type SyncretismView,
  usePantheonOf,
} from './api'
import { PANTHEON_ICON, STRUCTURES, SYNCRETISM_ICON, TIES } from './labels'

const SHOWN = 4
const HOLD =
  'Values you set are held against the engine until you release them.'
const GODS = ['son', 'foreign_god'] as const
const SONS = ['son'] as const
const FOREIGN = ['foreign_god'] as const
const PEOPLES = ['people'] as const

type Edit = { values: EditValues; release: string[] }

const PANTHEON_FIELDS: readonly Field[] = [
  {
    key: 'structure',
    label: 'How its gods stand together',
    kind: 'pick',
    table: table(STRUCTURES),
  },
  {
    key: 'head_node_id',
    label: 'Head of the pantheon',
    kind: 'node',
    types: [],
  },
]
const TIE_FIELDS: readonly Field[] = [
  {
    key: 'tie',
    label: 'Tie between the gods',
    kind: 'pick',
    table: table(TIES),
  },
]
const SYNCRETISM_FIELDS: readonly Field[] = [
  {
    key: 'dominant_node_id',
    label: 'The god that dominates',
    kind: 'node',
    types: [],
  },
]

function Tie({
  row,
  blocked,
}: {
  row: PantheonTieView
  blocked: string | null
}) {
  const named = TIES[row.tie]
  const target = { god_id: row.god.id, other_id: row.other.id }
  const editing = useMadeAction(
    'pantheon_tie:edit',
    (vars: Edit) => ({
      ...target,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The tie is set'
  )
  const removing = useMadeAction(
    'pantheon_tie:delete',
    (_: void) => target,
    'The tie is undone'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={named.tone ?? 'info'}
      title={`${row.god.name}: ${named.label.toLowerCase()} ${row.other.name}`}
      caption={`since epoch ${row.since_epoch}`}
    >
      <Ref node={row.other} empty='no god named' />
      <RecordEditor
        act={editing}
        title='Set the tie'
        note={HOLD}
        fields={TIE_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Undo the tie'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Joined({
  row,
  blocked,
}: {
  row: SyncretismView
  blocked: string | null
}) {
  const editing = useMadeAction(
    'syncretism:edit',
    (vars: Edit) => ({
      syncretism_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The joined worship is set'
  )
  const removing = useMadeAction(
    'syncretism:delete',
    (_: void) => ({ syncretism_id: row.id }),
    'The gods are held apart'
  )
  return (
    <RecordRow
      icon={SYNCRETISM_ICON}
      tone='verdigris'
      title={`${row.people.name} hold ${row.son.name} and ${row.foreign_god.name} as one`}
      caption={`since epoch ${row.since_epoch}; ${row.dominant ? `${row.dominant.name} dominates and draws the other's faith` : 'neither dominates'}`}
    >
      <RecordEditor
        act={editing}
        title='Set the joined worship'
        note={HOLD}
        fields={SYNCRETISM_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Hold them apart'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Structure({
  view,
  blocked,
}: {
  view: PantheonOfView
  blocked: string | null
}) {
  const row = view.pantheon
  const editing = useMadeAction(
    'pantheon:edit',
    (vars: Edit) => ({
      world_id: row?.world.id ?? 0,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The pantheon is set'
  )
  if (!row)
    return (
      <EmptyState
        icon={PANTHEON_ICON}
        size='inline'
        title='No pantheon stands here yet'
        description='A world gains a pantheon at the next epoch once gods dwell in it.'
      />
    )
  const named = STRUCTURES[row.structure]
  return (
    <RecordRow
      icon={named.icon}
      tone={named.tone ?? 'info'}
      title={`The gods of ${row.world.name}: ${named.label.toLowerCase()}`}
      caption={`since epoch ${row.since_epoch}; ${row.head ? `headed by ${row.head.name}` : 'with no head'}`}
    >
      <Ref node={row.head} empty='no head named' />
      <RecordEditor
        act={editing}
        title='Set the pantheon'
        note={HOLD}
        fields={PANTHEON_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
    </RecordRow>
  )
}

function Forges({
  view,
  nodeId,
  blocked,
}: {
  view: PantheonOfView
  nodeId: number
  blocked: string | null
}) {
  const [other, setOther] = useState<number | null>(null)
  const [tie, setTie] = useState<string>('kin')
  const [son, setSon] = useState<number | null>(null)
  const [foreign, setForeign] = useState<number | null>(null)
  const [people, setPeople] = useState<number | null>(null)
  const tying = useMadeAction(
    'pantheon_tie:set',
    (_: void) => ({
      god_id: nodeId,
      other_id: other ?? 0,
      tie: tie as PantheonTieView['tie'],
    }),
    'The gods are tied'
  )
  const joining = useMadeAction(
    'syncretism:create',
    (_: void) => ({
      foreign_god_id: foreign ?? 0,
      son_id: son ?? 0,
      people_id: people ?? 0,
    }),
    'The two gods are held as one'
  )
  const notGod = view.is_god ? null : 'Only a god holds ties to other gods'
  const noOther =
    other === null
      ? 'Pick the other god first'
      : other === nodeId
        ? 'A god holds no tie to itself'
        : null
  const missing =
    son === null || foreign === null || people === null
      ? 'Pick a son, a foreign god and a people first'
      : null
  return (
    <>
      <ForgeCard
        icon={CirclePlus}
        tone='gold'
        title='Tie it to another god'
        note='Ties pull each god toward or away from the others each epoch: partners and kin draw close, rivals apart.'
        columns={2}
        action={
          <StepButton
            act={tying}
            icon={CirclePlus}
            label='Tie them'
            variant='default'
            busy={why(blocked ?? notGod ?? noOther, tying.isPending)}
            onClick={() => tying.mutate()}
          />
        }
      >
        <ThingPicker
          label='The other god'
          value={other}
          onChange={setOther}
          blocked={blocked ?? notGod}
          kinds={GODS}
        />
        <ChoiceField
          label='Tie'
          value={tie}
          table={TIES}
          blocked={blocked ?? notGod}
          onPick={setTie}
        />
      </ForgeCard>
      <ForgeCard
        icon={SYNCRETISM_ICON}
        tone='verdigris'
        title='Join a son and a foreign god in worship'
        note='A people that holds two gods as one passes faith from the lesser to the dominant each epoch.'
        columns={3}
        action={
          <StepButton
            act={joining}
            icon={SYNCRETISM_ICON}
            label='Join them'
            variant='default'
            busy={why(blocked ?? missing, joining.isPending)}
            onClick={() => joining.mutate()}
          />
        }
      >
        <ThingPicker
          label='Son'
          value={son}
          onChange={setSon}
          blocked={blocked}
          kinds={SONS}
        />
        <ThingPicker
          label='Foreign god'
          value={foreign}
          onChange={setForeign}
          blocked={blocked}
          kinds={FOREIGN}
        />
        <ThingPicker
          label='People'
          value={people}
          onChange={setPeople}
          blocked={blocked}
          types={PEOPLES}
        />
      </ForgeCard>
    </>
  )
}

export function PantheonSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = usePantheonOf(nodeId)
  const ties = useShowMore(query.data?.ties ?? [], SHOWN, SHOWN)
  const joined = useShowMore(query.data?.syncretisms ?? [], SHOWN, SHOWN)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-pantheon'
      title='Pantheon: how the gods here stand together'
      description='The gods of a world stand as a council, a family, a court, rivals, a pair or loosely; they hold ties to one another, may be held as one by a people, fade when forgotten and return when called.'
      icon={PANTHEON_ICON}
      tone='gold'
    >
      <div
        data-surface='PantheonSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the pantheon' />
        ) : query.isError ? (
          <EmptyState
            icon={PANTHEON_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Structure view={query.data} blocked={blocked} />
            {query.data.ties.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {ties.visible.map((row) => (
                    <Tie
                      key={`${row.god.id}-${row.other.id}`}
                      row={row}
                      blocked={blocked}
                    />
                  ))}
                </ul>
                <ShowMore state={ties} />
              </>
            ) : (
              <EmptyState
                icon={PANTHEON_ICON}
                size='inline'
                title='No ties to other gods'
                description={`${query.data.node.name} holds no tie to another god; tie it below.`}
              />
            )}
            {query.data.syncretisms.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {joined.visible.map((row) => (
                    <Joined key={row.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={joined} />
              </>
            ) : null}
            <Forges view={query.data} nodeId={nodeId} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
