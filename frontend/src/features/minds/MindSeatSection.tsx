import { useState } from 'react'
import {
  Copy,
  Flame,
  FlameKindling,
  Gauge,
  GitBranch,
  Heart,
  Merge,
  MoveRight,
  RotateCcw,
  Save,
  Split,
  Timer,
  Trash2,
} from 'lucide-react'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { WILLS } from '@/features/pursuits/labels'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type MindNodeView,
  type MindStateView,
  useMadeAction,
  useNodeMind,
  useProfileEdit,
  useRowDelete,
  useRowEdit,
} from './api'
import {
  ARCHIVE_ACCESS,
  ENERGY_KINDS,
  LINEAGE_KINDS,
  MADE_MIND_SOULS,
  MADE_MINDS_LAWS,
  MAKING_OUTCOMES,
  MIND_AFFECTS,
  MIND_ICON,
  MIND_MAKINGS,
  MIND_ORIGINS,
  MIND_PURPOSES,
  MIND_SEATS,
  MIND_UPKEEPS,
  SOUL_CONTINUITIES,
  STATE_MEDIA,
  WILL_CAUSES,
} from './labels'

const SHOWN = 6
const YES_NO = { true: 'Yes', false: 'No' }
const FLAGS = [
  ['pausable', 'Can be paused'],
  ['copyable', 'Can be copied'],
  ['restorable', 'Can be saved and restored'],
  ['mergeable', 'Can be merged'],
  ['transferable', 'Can move seats'],
  ['dormant', 'Dormant'],
  ['perfect_recall', 'Perfect recall'],
  ['souled', 'Holds a soul'],
] as const

function profileFields(view: MindNodeView): readonly Field[] {
  return [
    {
      key: 'seat',
      label: 'Seat of the mind',
      kind: 'pick',
      table: table(MIND_SEATS),
    },
    {
      key: 'seat_node_id',
      label: 'What holds the seat',
      kind: 'node',
      types: [],
    },
    {
      key: 'origin',
      label: 'Origin of the mind',
      kind: 'pick',
      table: table(MIND_ORIGINS),
    },
    { key: 'will', label: 'Will', kind: 'pick', table: table(WILLS) },
    {
      key: 'affect',
      label: 'Feeling',
      kind: 'pick',
      table: table(MIND_AFFECTS),
    },
    {
      key: 'purpose',
      label: 'Purpose',
      kind: 'pick',
      table: table(MIND_PURPOSES),
    },
    { key: 'capacity', label: 'Capacity', kind: 'number', min: 0, max: 100 },
    {
      key: 'speed_pct',
      label: 'Speed against world time (%)',
      kind: 'number',
      min: 1,
      max: view.speed_max,
    },
    { key: 'stability', label: 'Stability', kind: 'number', min: 0, max: 100 },
    {
      key: 'fidelity_pct',
      label: 'Fidelity (%)',
      kind: 'number',
      min: 0,
      max: 100,
    },
    {
      key: 'upkeep',
      label: 'What keeps it',
      kind: 'pick',
      table: table(MIND_UPKEEPS),
    },
    {
      key: 'upkeep_energy',
      label: 'Energy it runs on',
      kind: 'pick',
      table: table(ENERGY_KINDS),
    },
    { key: 'made_by_node_id', label: 'Its maker', kind: 'node', types: [] },
    {
      key: 'maker_bond',
      label: 'Bond with its maker',
      kind: 'number',
      min: -100,
      max: 100,
    },
    {
      key: 'drift_pct',
      label: 'Drift from its making (%)',
      kind: 'number',
      min: 0,
      max: 100,
    },
    ...FLAGS.map(([key, label]): Field => ({
      key,
      label,
      kind: 'pick',
      table: YES_NO,
    })),
  ]
}

const SEAT_FIELDS: readonly Field[] = [
  {
    key: 'part_node_id',
    label: 'Part that holds a share',
    kind: 'node',
    types: [],
  },
  {
    key: 'share_pct',
    label: 'Share of the mind (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'vital', label: 'Vital to the mind', kind: 'pick', table: YES_NO },
]

const STATE_FIELDS: readonly Field[] = [
  {
    key: 'fidelity_pct',
    label: 'Fidelity (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'medium_kind',
    label: 'What holds the state',
    kind: 'pick',
    table: table(STATE_MEDIA),
  },
  {
    key: 'holder_node_id',
    label: 'Keeper of the state',
    kind: 'node',
    types: [],
  },
  {
    key: 'owner_node_id',
    label: 'Owner of the state',
    kind: 'node',
    types: [],
  },
  { key: 'copies', label: 'Copies kept', kind: 'number', min: 1, max: 1000 },
  { key: 'sealed', label: 'Sealed', kind: 'pick', table: YES_NO },
]

const REMOTE_FIELDS: readonly Field[] = [
  {
    key: 'mind_node_id',
    label: 'Mind that runs the body',
    kind: 'node',
    types: [],
  },
  {
    key: 'feedback_pct',
    label: 'Feedback felt (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
]

const ARCHIVE_FIELDS: readonly Field[] = [
  {
    key: 'holder_node_id',
    label: 'Keeper of the archive',
    kind: 'node',
    types: [],
  },
  {
    key: 'upkeep',
    label: 'Upkeep each epoch',
    kind: 'number',
    min: 0,
    max: 1000,
  },
  {
    key: 'access',
    label: 'Who may reach it',
    kind: 'pick',
    table: table(ARCHIVE_ACCESS),
  },
  {
    key: 'unpaid_epochs',
    label: 'Epochs unpaid',
    kind: 'number',
    min: 0,
    max: 1000,
  },
]

const LAW_FIELDS: readonly Field[] = [
  {
    key: 'made_minds',
    label: 'Will of made minds',
    kind: 'pick',
    table: table(MADE_MINDS_LAWS),
  },
  {
    key: 'made_mind_souls',
    label: 'Souls of made minds',
    kind: 'pick',
    table: table(MADE_MIND_SOULS),
  },
  {
    key: 'soul_continuity',
    label: 'Where a soul goes on copying',
    kind: 'pick',
    table: table(SOUL_CONTINUITIES),
  },
]

function SeatPart({
  part,
  blocked,
}: {
  part: MindNodeView['seats'][number]
  blocked: string | null
}) {
  const editing = useRowEdit('mind_seats', { id: part.id })
  const removing = useRowDelete('mind_seats', { id: part.id })
  return (
    <RecordRow
      icon={MIND_SEATS.bodies.icon}
      tone='info'
      title={part.part?.name ?? 'A part no longer in the record'}
      caption={`${part.share_pct}% of the mind${part.vital ? ', vital' : ''}`}
    >
      <RecordEditor
        act={editing}
        title='Set this share of the mind'
        note='Values you set are held against the engine until you release them.'
        fields={SEAT_FIELDS}
        locked={part.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Take this share away'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function SavedState({
  state,
  blocked,
}: {
  state: MindStateView
  blocked: string | null
}) {
  const medium = STATE_MEDIA[state.medium_kind]
  const editing = useRowEdit('mind_states', { id: state.id })
  const removing = useRowDelete('mind_states', { id: state.id })
  const restoring = useMadeAction(
    'mind:restore',
    (_: void) => ({ state_id: state.id }),
    'The mind runs again from what was saved'
  )
  return (
    <RecordRow
      icon={medium.icon}
      tone={medium.tone}
      title={`State of ${state.mind?.name ?? 'a mind'} saved in epoch ${state.taken_epoch}`}
      caption={`${medium.label}, ${state.fidelity_pct}% faithful, ${state.copies === 1 ? 'one copy kept' : `copies kept: ${state.copies}`}${state.sealed ? ', sealed' : ''}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={state.holder} empty='no keeper' />
        <Ref node={state.owner} empty='no owner' />
      </div>
      <RecordEditor
        act={editing}
        title='Set this saved state'
        note='Values you set are held against the engine until you release them.'
        fields={STATE_FIELDS}
        locked={state.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          act={restoring}
          icon={RotateCcw}
          label='Restore from it'
          busy={why(blocked, restoring.isPending)}
          onClick={() => restoring.mutate()}
        />
        <StepButton
          act={removing}
          icon={Trash2}
          label='Destroy this state'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function RemoteBody({
  body,
  blocked,
}: {
  body: MindNodeView['remote_bodies'][number]
  blocked: string | null
}) {
  const key = { body_node_id: body.body?.id ?? -1 }
  const editing = useRowEdit('remote_bodies', key)
  const removing = useRowDelete('remote_bodies', key)
  const gone = body.body === null ? 'The body is gone from the record' : null
  return (
    <RecordRow
      icon={MoveRight}
      tone='info'
      title={`${body.mind?.name ?? 'A mind'} runs ${body.body?.name ?? 'a body'} from afar`}
      caption={`Since epoch ${body.since_epoch}, feedback ${body.feedback_pct}%`}
    >
      <RecordEditor
        act={editing}
        title='Set this remote link'
        note='Values you set are held against the engine until you release them.'
        fields={REMOTE_FIELDS}
        locked={body.locked}
        busy={why(blocked ?? gone, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Cut the link'
        busy={why(blocked ?? gone, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Shaping({
  view,
  blocked,
}: {
  view: MindNodeView
  blocked: string | null
}) {
  const [seat, setSeat] = useState<string>('body')
  const [seatNode, setSeatNode] = useState<number | null>(null)
  const [medium, setMedium] = useState<string>('record')
  const [keeper, setKeeper] = useState<number | null>(null)
  const [other, setOther] = useState<number | null>(null)
  const [method, setMethod] = useState<string>('craft')
  const [will, setWill] = useState<string>('instructed')
  const [purpose, setPurpose] = useState<string>('servant')
  const [maker, setMaker] = useState<number | null>(null)
  const [skill, setSkill] = useState('40')
  const id = view.node.id
  const placed = (_: void) => ({
    mind_id: id,
    seat: seat as MindNodeView['seat'],
    seat_node_id: seatNode,
  })
  const copying = useMadeAction('mind:copy', placed, 'The mind is copied')
  const moving = useMadeAction(
    'mind:transfer',
    placed,
    'The mind moves to its new seat'
  )
  const dividing = useMadeAction(
    'mind:divide',
    placed,
    'The mind divides in two'
  )
  const saving = useMadeAction(
    'mind:save',
    (_: void) => ({
      mind_id: id,
      holder_id: keeper,
      owner_id: keeper,
      medium: medium as MindStateView['medium_kind'],
    }),
    'The state of the mind is saved'
  )
  const merging = useMadeAction(
    'mind:merge',
    (_: void) => ({ first_id: id, second_id: other ?? -1 }),
    'The two minds become one'
  )
  const making = useMadeAction(
    'mind:make',
    (_: void) => ({
      mind_id: id,
      maker_id: maker,
      method: method as MindNodeView['makings'][number]['method'],
      seat: seat as MindNodeView['seat'],
      seat_node_id: seatNode,
      will: will as MindNodeView['will'],
      purpose: purpose as MindNodeView['purpose'],
      skill: Math.min(100, Math.max(0, Number(skill) || 0)),
    }),
    'A mind is made in that seat'
  )
  const granting = useMadeAction(
    'mind:soul',
    (_: void) => ({ mind_id: id, grant: true }),
    'The mind is given a soul'
  )
  const withholding = useMadeAction(
    'mind:soul',
    (_: void) => ({ mind_id: id, grant: false }),
    'The soul is withheld'
  )
  const resetting = useMadeAction(
    'mind:reset',
    (_: void) => ({ mind_id: id }),
    'The mind is set back to what its kind is born with'
  )
  const noMind =
    view.seat === 'none'
      ? `${view.node.name} holds no mind yet; make one first`
      : null
  const noOther =
    other === null
      ? 'Pick the mind to merge into this one'
      : other === id
        ? 'A mind cannot merge with itself'
        : null
  const soulless =
    view.law?.made_mind_souls === 'none'
      ? 'The law of its world gives no made mind a soul'
      : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ForgeCard
        icon={MIND_ICON}
        tone='verdigris'
        title='Make a mind in this seat'
        note='Making records the maker, the method, the quality its skill reaches and what came of it; a making can go as meant, run unstable, leave an empty seat or wake a will no one meant.'
        columns={4}
        action={
          <StepButton
            act={making}
            icon={MIND_ICON}
            label='Make the mind'
            variant='default'
            busy={why(blocked, making.isPending)}
            onClick={() => making.mutate()}
          />
        }
      >
        <ChoiceField
          label='Method of making'
          value={method}
          table={MIND_MAKINGS}
          blocked={blocked}
          onPick={setMethod}
        />
        <ChoiceField
          label='Will it is given'
          value={will}
          table={WILLS}
          blocked={blocked}
          onPick={setWill}
        />
        <ChoiceField
          label='Purpose it is made for'
          value={purpose}
          table={MIND_PURPOSES}
          blocked={blocked}
          onPick={setPurpose}
        />
        <NumberField
          label='Skill of the making'
          value={skill}
          min={0}
          max={100}
          onChange={setSkill}
        />
        <ThingPicker
          label='Maker'
          value={maker}
          onChange={setMaker}
          blocked={blocked}
        />
      </ForgeCard>
      <ForgeCard
        icon={Copy}
        tone='info'
        title='Copy, move or divide this mind'
        note='A copy is a little less faithful than its source and each generation loses more; a divided part takes a share of the capacity.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              act={copying}
              icon={Copy}
              label='Copy it'
              busy={why(blocked ?? noMind, copying.isPending)}
              onClick={() => copying.mutate()}
            />
            <StepButton
              act={moving}
              icon={MoveRight}
              label='Move it'
              busy={why(blocked ?? noMind, moving.isPending)}
              onClick={() => moving.mutate()}
            />
            <StepButton
              act={dividing}
              icon={Split}
              label='Divide it'
              busy={why(blocked ?? noMind, dividing.isPending)}
              onClick={() => dividing.mutate()}
            />
          </div>
        }
      >
        <ChoiceField
          label='Seat it runs in'
          value={seat}
          table={MIND_SEATS}
          blocked={blocked}
          onPick={setSeat}
        />
        <ThingPicker
          label='What holds the seat'
          value={seatNode}
          onChange={setSeatNode}
          blocked={blocked}
        />
      </ForgeCard>
      <ForgeCard
        icon={Save}
        tone='gold'
        title='Save its state, or merge another into it'
        note='A saved state can restore the mind later; a restored mind remembers nothing after the state was taken. Merging ends the second mind as itself.'
        columns={3}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              act={saving}
              icon={Save}
              label='Save its state'
              busy={why(blocked ?? noMind, saving.isPending)}
              onClick={() => saving.mutate()}
            />
            <StepButton
              act={merging}
              icon={Merge}
              label='Merge the other into it'
              busy={why(blocked ?? noMind ?? noOther, merging.isPending)}
              onClick={() => merging.mutate()}
            />
          </div>
        }
      >
        <ChoiceField
          label='What holds the state'
          value={medium}
          table={STATE_MEDIA}
          blocked={blocked}
          onPick={setMedium}
        />
        <ThingPicker
          label='Keeper of the state'
          value={keeper}
          onChange={setKeeper}
          blocked={blocked}
        />
        <ThingPicker
          label='Mind to merge in'
          value={other}
          onChange={setOther}
          blocked={blocked}
        />
      </ForgeCard>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          act={granting}
          icon={Flame}
          label={`Grant a soul (a son pays ${view.soul_grant_cost} essence)`}
          busy={why(blocked ?? noMind ?? soulless, granting.isPending)}
          onClick={() => granting.mutate()}
        />
        <StepButton
          act={withholding}
          icon={FlameKindling}
          label='Withhold its soul'
          busy={why(blocked ?? noMind, withholding.isPending)}
          onClick={() => withholding.mutate()}
        />
        <StepButton
          act={resetting}
          icon={RotateCcw}
          label='Set it back to what its kind is born with'
          busy={why(blocked, resetting.isPending)}
          onClick={() => resetting.mutate()}
        />
      </div>
    </div>
  )
}

function Lists({
  view,
  blocked,
}: {
  view: MindNodeView
  blocked: string | null
}) {
  const states = useShowMore(view.states, SHOWN, SHOWN * 2)
  const makings = useShowMore(view.makings, SHOWN, SHOWN * 2)
  const changes = useShowMore(view.will_changes, SHOWN, SHOWN * 2)
  const lineage = useShowMore(view.lineage, SHOWN, SHOWN * 2)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-col gap-2'>
        {view.seats.length ? (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.seats} as='li'>
              {(part) => (
                <SeatPart key={part.id} part={part} blocked={blocked} />
              )}
            </Paged>
          </ul>
        ) : (
          <EmptyState
            icon={MIND_SEATS.bodies.icon}
            size='inline'
            title='One seat only'
            description='This mind does not spread over several parts; add a part under Every record to spread it.'
          />
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        {view.states.length ? (
          <>
            <ul className='flex min-w-0 flex-col gap-2'>
              {states.visible.map((state) => (
                <SavedState key={state.id} state={state} blocked={blocked} />
              ))}
            </ul>
            <ShowMore state={states} />
          </>
        ) : (
          <EmptyState
            icon={Save}
            size='inline'
            title='No saved states'
            description='Save its state above to keep a mind that can be restored.'
          />
        )}
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        {makings.visible.map((making) => (
          <RecordRow
            key={making.id}
            icon={MIND_MAKINGS[making.method].icon}
            tone={MAKING_OUTCOMES[making.outcome].tone}
            title={`${MIND_MAKINGS[making.method].label} in epoch ${making.epoch}`}
            caption={`Quality ${making.quality}, ${MAKING_OUTCOMES[making.outcome].label.toLowerCase()}`}
            aside={<Ref node={making.maker} empty='no maker' />}
          />
        ))}
      </ul>
      <ShowMore state={makings} />
      <ul className='flex min-w-0 flex-col gap-2'>
        {changes.visible.map((change) => (
          <RecordRow
            key={change.id}
            icon={WILL_CAUSES[change.cause].icon}
            tone={WILLS[change.to_will].tone}
            title={WILLS[change.to_will].label}
            caption={`Was ${WILLS[change.from_will].label.toLowerCase()}; ${WILL_CAUSES[change.cause].label.toLowerCase()}, epoch ${change.epoch}`}
          />
        ))}
      </ul>
      <ShowMore state={changes} />
      {view.lineage.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          {lineage.visible.map((link) => (
            <RecordRow
              key={`${link.kind}-${link.other.id}-${link.epoch}`}
              icon={GitBranch}
              tone='info'
              title={
                link.outgoing
                  ? `${LINEAGE_KINDS[link.kind]?.label ?? 'Tied to'}: ${link.other.name}`
                  : `${link.other.name}, ${(LINEAGE_KINDS[link.kind]?.label ?? 'tied to').toLowerCase()} this mind`
              }
              caption={`Since epoch ${link.epoch}`}
              aside={<Ref node={link.other} />}
            />
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={GitBranch}
          size='inline'
          title='No line of minds'
          description='No copy, merge, division or link ties this mind to another.'
        />
      )}
      <ShowMore state={lineage} />
      {view.remote_bodies.map((body) => (
        <RemoteBody
          key={`${body.body?.id}-${body.mind?.id}`}
          body={body}
          blocked={blocked}
        />
      ))}
    </div>
  )
}

function ArchiveAndLaw({
  view,
  blocked,
}: {
  view: MindNodeView
  blocked: string | null
}) {
  const archiveEdit = useProfileEdit(view.node.id, 'mind_archives')
  const lawEdit = useProfileEdit(
    view.law?.world.id ?? view.node.id,
    'mind_laws'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {view.archive && (
        <RecordRow
          icon={ARCHIVE_ACCESS[view.archive.access].icon}
          tone={ARCHIVE_ACCESS[view.archive.access].tone}
          title='An archive of minds is kept here'
          caption={`${ARCHIVE_ACCESS[view.archive.access].label}, upkeep ${view.archive.upkeep}, unpaid for ${view.archive.unpaid_epochs}`}
          aside={<Ref node={view.archive.holder} empty='no keeper' />}
        >
          <RecordEditor
            act={archiveEdit}
            title='Set this archive'
            note='Values you set are held against the engine until you release them.'
            fields={ARCHIVE_FIELDS}
            locked={view.archive.locked}
            busy={why(blocked, archiveEdit.isPending)}
            onSave={(values) => archiveEdit.mutate({ values, release: [] })}
            onRelease={(keys) =>
              archiveEdit.mutate({ values: {}, release: keys })
            }
          />
        </RecordRow>
      )}
      <RecordEditor
        act={lawEdit}
        title={
          view.law
            ? `Law of minds on ${view.law.world.name}: ${MADE_MINDS_LAWS[view.law.made_minds].label.toLowerCase()}, ${MADE_MIND_SOULS[view.law.made_mind_souls].label.toLowerCase()}, ${SOUL_CONTINUITIES[view.law.soul_continuity].label.toLowerCase()}`
            : 'Law of minds'
        }
        note={
          view.law
            ? 'The law of its world: whether made minds may have will, whether they have souls and where a soul goes on copying.'
            : `${view.node.name} stands on no world, so no law of minds reaches it.`
        }
        fields={LAW_FIELDS}
        locked={view.law?.locked ?? []}
        busy={why(
          blocked ?? (view.law ? null : 'It stands on no world'),
          lawEdit.isPending
        )}
        onSave={(values) => lawEdit.mutate({ values, release: [] })}
        onRelease={(keys) => lawEdit.mutate({ values: {}, release: keys })}
      />
    </div>
  )
}

export function MindSeatSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeMind(nodeId)
  const editing = useProfileEdit(nodeId, 'mind_profiles')
  return (
    <Section
      id='section-mind-seat'
      title='Mind seat: where its mind runs, its will, its maker and its line'
      description='Every thing can hold a mind: in a body, across bodies, in an object, a place, a network, a host or a made realm. Its will, its bond with its maker, saved states, copies and souls are read and set here.'
      icon={MIND_ICON}
      tone='verdigris'
    >
      <div
        data-surface='MindSeatSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its mind' />
        ) : query.isError ? (
          <EmptyState
            icon={MIND_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
              <KpiTile
                label='Seat of the mind'
                value={MIND_SEATS[query.data.seat].label}
                icon={MIND_SEATS[query.data.seat].icon}
                tone={MIND_SEATS[query.data.seat].tone}
              />
              <KpiTile
                label='Origin of the mind'
                value={MIND_ORIGINS[query.data.origin].label}
                icon={MIND_ORIGINS[query.data.origin].icon}
                tone={MIND_ORIGINS[query.data.origin].tone}
              />
              <KpiTile
                label='Will'
                value={WILLS[query.data.will].label}
                icon={WILLS[query.data.will].icon}
                tone={WILLS[query.data.will].tone}
              />
              <KpiTile
                label='Purpose'
                value={MIND_PURPOSES[query.data.purpose].label}
                icon={MIND_PURPOSES[query.data.purpose].icon}
                tone={MIND_PURPOSES[query.data.purpose].tone}
              />
              <KpiTile
                label='Capacity, stability'
                value={`${query.data.capacity}, ${query.data.stability}`}
                icon={Gauge}
                tone='info'
              />
              <KpiTile
                label='Speed, fidelity'
                value={`${query.data.speed_pct}% of world time, ${query.data.fidelity_pct}% faithful`}
                icon={Timer}
                tone='muted'
              />
              <KpiTile
                label='Bond with its maker'
                value={String(query.data.maker_bond)}
                icon={Heart}
                tone={query.data.maker_bond < 0 ? 'danger' : 'success'}
              />
              <KpiTile
                label='Drift, epochs running'
                value={`${query.data.drift_pct}%, ${query.data.run_epochs}`}
                icon={GitBranch}
                tone={query.data.drift_pct > 50 ? 'warning' : 'muted'}
              />
              <KpiTile
                label='Soul'
                value={query.data.souled ? 'Holds a soul' : 'No soul'}
                icon={query.data.souled ? Flame : FlameKindling}
                tone={query.data.souled ? 'gold' : 'muted'}
              />
            </div>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Chip icon={MIND_AFFECTS[query.data.affect].icon}>
                {MIND_AFFECTS[query.data.affect].label}
              </Chip>
              <Chip icon={MIND_UPKEEPS[query.data.upkeep].icon}>
                Kept by {MIND_UPKEEPS[query.data.upkeep].label.toLowerCase()}
                {query.data.upkeep_energy
                  ? `, ${ENERGY_KINDS[query.data.upkeep_energy].label.toLowerCase()}`
                  : ''}
              </Chip>
              {FLAGS.filter(([key]) => query.data[key]).map(([key, label]) => (
                <Chip key={key} icon={MIND_ICON}>
                  {label}
                </Chip>
              ))}
              <Ref node={query.data.seat_node} empty='no separate seat' />
              <Ref node={query.data.made_by} empty='no maker' />
            </div>
            <RecordEditor
              act={editing}
              title='Set this mind'
              note='Values you set are held against the engine until you release them.'
              fields={profileFields(query.data)}
              locked={query.data.locked}
              busy={why(readOnlyReason, editing.isPending)}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <Shaping view={query.data} blocked={readOnlyReason} />
            <Lists view={query.data} blocked={readOnlyReason} />
            <ArchiveAndLaw view={query.data} blocked={readOnlyReason} />
          </>
        )}
      </div>
    </Section>
  )
}
