import { useState } from 'react'
import { CirclePlus, Crown, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { creatorSignKindValues, domainValues } from '@/api/generated/schema'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
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
import { wordOf } from '@/features/entity/affairs/labels'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type CovenantView,
  type CreatorBondsView,
  useCreatorBonds,
} from './api'
import {
  COVENANT_STATES,
  CREATOR_ICON,
  DUTIES,
  FAVOURS,
  HERESIES,
  NATURES,
  PROMISES,
  STANCES,
} from './labels'

const SHOWN = 4
const HOLD =
  'Values you set are held against the engine until you release them.'
const NOT_PEOPLE =
  'Only a people holds a view of the Creator, pictures it and keeps covenants'
const ASPECTS = Object.fromEntries(
  domainValues.map((value) => [
    value,
    wordOf(domainValues, value).toLowerCase(),
  ])
)

type Edit = { values: EditValues; release: string[] }

const STANDING_FIELDS: readonly Field[] = [
  { key: 'awe', label: 'Awe', kind: 'number', min: 0, max: 100 },
  { key: 'love', label: 'Love', kind: 'number', min: 0, max: 100 },
  { key: 'dread', label: 'Dread', kind: 'number', min: 0, max: 100 },
  { key: 'gratitude', label: 'Gratitude', kind: 'number', min: 0, max: 100 },
  { key: 'resentment', label: 'Resentment', kind: 'number', min: 0, max: 100 },
  {
    key: 'ignorance',
    label: 'Ignorance of the Creator',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'stance', label: 'Stance', kind: 'pick', table: table(STANCES) },
  { key: 'heresy', label: 'Heresy', kind: 'pick', table: table(HERESIES) },
]
const DEPICTION_FIELDS: readonly Field[] = [
  { key: 'name', label: 'Name they give the Creator', kind: 'text' },
  {
    key: 'nature',
    label: 'Nature they see',
    kind: 'pick',
    table: table(NATURES),
  },
  { key: 'aspect', label: 'Aspect they stress', kind: 'pick', table: ASPECTS },
]
const COVENANT_FIELDS: readonly Field[] = [
  { key: 'duty', label: 'Their duty', kind: 'pick', table: table(DUTIES) },
  {
    key: 'promise',
    label: "The Creator's promise",
    kind: 'pick',
    table: table(PROMISES),
  },
  { key: 'state', label: 'State', kind: 'pick', table: table(COVENANT_STATES) },
  { key: 'until_epoch', label: 'Lasts until epoch', kind: 'number', min: 0 },
  { key: 'breaches', label: 'Breaches', kind: 'number', min: 0, max: 50 },
]
const CHOSEN_FIELDS: readonly Field[] = [
  { key: 'favour', label: 'Favour', kind: 'pick', table: table(FAVOURS) },
]

function Covenant({
  row,
  blocked,
}: {
  row: CovenantView
  blocked: string | null
}) {
  const state = COVENANT_STATES[row.state]
  const editing = useMadeAction(
    'covenant:edit',
    (vars: Edit) => ({
      covenant_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The covenant is set so'
  )
  const removing = useMadeAction(
    'covenant:delete',
    (_: void) => ({ covenant_id: row.id }),
    'The covenant is struck'
  )
  return (
    <RecordRow
      icon={state.icon}
      tone={state.tone ?? 'info'}
      title={`${DUTIES[row.duty].label} for ${PROMISES[row.promise].label.toLowerCase()}: ${state.label.toLowerCase()}`}
      caption={`since epoch ${row.since_epoch}${row.until_epoch !== null ? `, until epoch ${row.until_epoch}` : ', with no end set'}; ${row.breaches} breach${row.breaches === 1 ? '' : 'es'}; sealed by a sign of ${wordOf(creatorSignKindValues, row.seal_sign).toLowerCase()}`}
    >
      <RecordEditor
        title='Set the covenant'
        note={HOLD}
        fields={COVENANT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function PeopleBonds({
  view,
  nodeId,
  blocked,
}: {
  view: CreatorBondsView
  nodeId: number
  blocked: string | null
}) {
  const covenants = useShowMore(view.covenants, SHOWN, SHOWN)
  const [duty, setDuty] = useState<string>('worship')
  const [promise, setPromise] = useState<string>('protection')
  const [epochs, setEpochs] = useState('6')
  const standing = useMadeAction(
    'creator_standing:edit',
    (vars: Edit) => ({
      people_id: nodeId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'Their view of the Creator is set'
  )
  const depicting = useMadeAction(
    'depiction:edit',
    (vars: Edit) => ({
      people_id: nodeId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'Their image of the Creator is set'
  )
  const offering = useMadeAction(
    'covenant:offer',
    (_: void) => ({
      people_id: nodeId,
      duty: duty as CovenantView['duty'],
      promise: promise as CovenantView['promise'],
      epochs: Math.max(1, Number(epochs) || 1),
    }),
    'A covenant is offered'
  )
  const row = view.standing
  return (
    <>
      {row ? (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-4'>
            <KpiTile
              label='Stance'
              value={STANCES[row.stance].label}
              icon={STANCES[row.stance].icon}
              tone={STANCES[row.stance].tone ?? 'info'}
            />
            <KpiTile
              label='Awe'
              value={String(row.awe)}
              icon={Crown}
              tone='gold'
            />
            <KpiTile
              label='Love'
              value={String(row.love)}
              icon={CREATOR_ICON}
              tone='success'
            />
            <KpiTile
              label='Resentment'
              value={String(row.resentment)}
              icon={HERESIES.anti_god.icon}
              tone={row.resentment ? 'danger' : 'muted'}
            />
          </div>
          <RecordRow
            icon={HERESIES[row.heresy].icon}
            tone={HERESIES[row.heresy].tone ?? 'info'}
            title={`Dread ${row.dread}, gratitude ${row.gratitude}, ignorance ${row.ignorance}; ${HERESIES[row.heresy].label.toLowerCase()}`}
            caption={`Weighed anew in epoch ${row.updated_epoch}`}
          >
            <RecordEditor
              title='Set their view of the Creator'
              note={HOLD}
              fields={STANDING_FIELDS}
              locked={row.locked}
              busy={why(blocked, standing.isPending)}
              onSave={(values) => standing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                standing.mutate({ values: {}, release: keys })
              }
            />
          </RecordRow>
        </>
      ) : (
        <EmptyState
          icon={CREATOR_ICON}
          size='inline'
          title='No view of the Creator yet'
          description='It is weighed at the next epoch.'
        />
      )}
      <RecordRow
        icon={
          view.depiction ? NATURES[view.depiction.nature].icon : CREATOR_ICON
        }
        tone='gold'
        title={
          view.depiction
            ? `They call the Creator ${view.depiction.name}`
            : 'They have not yet pictured the Creator'
        }
        caption={
          view.depiction
            ? `${NATURES[view.depiction.nature].label}${view.depiction.aspect ? `, stressing ${wordOf(domainValues, view.depiction.aspect).toLowerCase()}` : ''}`
            : 'Set it below or wait for the next epoch'
        }
      >
        <RecordEditor
          title='Set their image of the Creator'
          note={HOLD}
          fields={DEPICTION_FIELDS}
          locked={view.depiction?.locked ?? []}
          busy={why(blocked, depicting.isPending)}
          onSave={(values) => depicting.mutate({ values, release: [] })}
          onRelease={(keys) => depicting.mutate({ values: {}, release: keys })}
        />
      </RecordRow>
      <ul className='flex min-w-0 flex-col gap-2'>
        {covenants.visible.map((item) => (
          <Covenant key={item.id} row={item} blocked={blocked} />
        ))}
      </ul>
      <ShowMore state={covenants} />
      <ForgeCard
        icon={CirclePlus}
        tone='gold'
        title='Offer a covenant'
        note='They seal it if they hold the Creator in worship or reverence; each breach of their duty strains it until it breaks.'
        columns={3}
        action={
          <StepButton
            icon={CirclePlus}
            label='Offer it'
            variant='default'
            busy={why(blocked, offering.isPending)}
            onClick={() => offering.mutate()}
          />
        }
      >
        <ChoiceField
          label='Their duty'
          value={duty}
          table={DUTIES}
          blocked={blocked}
          onPick={setDuty}
        />
        <ChoiceField
          label="The Creator's promise"
          value={promise}
          table={PROMISES}
          blocked={blocked}
          onPick={setPromise}
        />
        <NumberField
          label='Epochs it lasts'
          value={epochs}
          min={1}
          max={1000}
          onChange={setEpochs}
        />
      </ForgeCard>
    </>
  )
}

function Chosen({
  view,
  nodeId,
  blocked,
}: {
  view: CreatorBondsView
  nodeId: number
  blocked: string | null
}) {
  const [favour, setFavour] = useState<string>('renown')
  const choosing = useMadeAction(
    'chosen:choose',
    (_: void) => ({
      node_id: nodeId,
      favour: favour as NonNullable<CreatorBondsView['chosen']>['favour'],
    }),
    'The Creator has chosen it'
  )
  const editing = useMadeAction(
    'chosen:edit',
    (vars: Edit) => ({
      node_id: nodeId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The favour is set'
  )
  const releasing = useMadeAction(
    'chosen:release',
    (_: void) => ({ node_id: nodeId }),
    'It is chosen no longer'
  )
  return view.chosen ? (
    <RecordRow
      icon={FAVOURS[view.chosen.favour].icon}
      tone='gold'
      title={`Chosen by the Creator: ${FAVOURS[view.chosen.favour].label.toLowerCase()}`}
      caption={`since epoch ${view.chosen.since_epoch}; the chosen gain renown and draw envy`}
    >
      <RecordEditor
        title='Set the favour'
        note={HOLD}
        fields={CHOSEN_FIELDS}
        locked={view.chosen.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Release it'
        busy={why(blocked, releasing.isPending)}
        onClick={() => releasing.mutate()}
      />
    </RecordRow>
  ) : (
    <ForgeCard
      icon={Crown}
      tone='gold'
      title='Choose it'
      note='The chosen gain renown and favour each epoch, and draw the envy of those around them.'
      columns={2}
      action={
        <StepButton
          icon={Crown}
          label='Choose it'
          variant='default'
          busy={why(blocked, choosing.isPending)}
          onClick={() => choosing.mutate()}
        />
      }
    >
      <ChoiceField
        label='Favour'
        value={favour}
        table={FAVOURS}
        blocked={blocked}
        onPick={setFavour}
      />
    </ForgeCard>
  )
}

export function CreatorBondsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useCreatorBonds(nodeId)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-creator-bonds'
      title='The Creator: how it is held and favoured here'
      description='Peoples hold the Creator in awe, love, dread, gratitude, resentment or ignorance; they picture it in their own way, keep or break covenants and may fall into heresy. Any thing can be chosen.'
      icon={CREATOR_ICON}
      tone='gold'
    >
      <div
        data-surface='CreatorBondsSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its bond with the Creator' />
        ) : query.isError ? (
          <EmptyState
            icon={CREATOR_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            {query.data.far_epochs !== null ? (
              <Chip icon={CREATOR_ICON}>
                {query.data.far_epochs
                  ? `Far from the Creator's eye for ${query.data.far_epochs} epoch${query.data.far_epochs === 1 ? '' : 's'}`
                  : "Under the Creator's eye"}
              </Chip>
            ) : null}
            {query.data.is_people ? (
              <PeopleBonds
                view={query.data}
                nodeId={nodeId}
                blocked={blocked}
              />
            ) : (
              <EmptyState
                icon={CREATOR_ICON}
                size='inline'
                title='No view to weigh here'
                description={NOT_PEOPLE}
              />
            )}
            <Chosen view={query.data} nodeId={nodeId} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
