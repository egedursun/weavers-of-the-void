import { useState } from 'react'
import {
  Ban,
  Gavel,
  Link2,
  Lock,
  ShieldCheck,
  Sparkles,
  Sun,
  Swords,
  Trash2,
  Undo2,
  Zap,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
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
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { SON_STATUS_LABEL } from '@/features/pantheon/labels'
import { Bars } from '@/features/sacred/parts'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type StarModifierView,
  type TransformKind,
  type TransformNodeView,
  type TransformProspectView,
  type KindChangeView,
  useNodeTransformations,
  useTransformAction,
} from './api'
import {
  PROSPECT_STANCES,
  STAR_MODIFIER_SOURCES,
  TRANSFORM_ENDS,
  TRANSFORM_ICON,
  TRANSFORM_KINDS,
  TRANSFORM_STATES,
  TRANSFORM_TRIGGERS,
} from './labels'

const SHOWN = 6
const MOST_EPOCHS = 100000

type Edit = {
  values: Record<string, number | string | boolean | null>
  release: string[]
}

const RECORD_FIELDS: readonly Field[] = [
  {
    key: 'trigger',
    label: 'What brought it about',
    kind: 'pick',
    table: table(TRANSFORM_TRIGGERS),
  },
  { key: 'subject_name', label: 'Name it had before', kind: 'text' },
  { key: 'result_name', label: 'Name it took after', kind: 'text' },
]

const PROSPECT_FIELDS: readonly Field[] = [
  { key: 'progress', label: 'Progress', kind: 'number', min: 0, max: 100 },
  {
    key: 'stance',
    label: 'The Creator’s stance',
    kind: 'pick',
    table: table(PROSPECT_STANCES),
  },
  {
    key: 'trigger',
    label: 'What drives it',
    kind: 'pick',
    table: table(TRANSFORM_TRIGGERS),
  },
  {
    key: 'warned_epoch',
    label: 'Epoch of the warning',
    kind: 'number',
    min: 0,
    max: MOST_EPOCHS,
  },
  {
    key: 'due_epoch',
    label: 'Epoch it comes due',
    kind: 'number',
    min: 0,
    max: MOST_EPOCHS,
  },
]

function modifierFields(view: TransformNodeView): readonly Field[] {
  return [
    {
      key: 'source',
      label: 'Source of the change',
      kind: 'pick',
      table: table(STAR_MODIFIER_SOURCES),
    },
    {
      key: 'luminosity_pct',
      label: 'Change to its light, in a hundred',
      kind: 'number',
      min: -view.luminosity_shift_max,
      max: view.luminosity_shift_max,
    },
    {
      key: 'age_epochs',
      label: 'Epochs its life moves forward',
      kind: 'number',
      min: 0,
      max: MOST_EPOCHS,
    },
    {
      key: 'decay',
      label: 'Fading each epoch',
      kind: 'number',
      min: 0,
      max: 100,
    },
  ]
}

function Change({
  row,
  blocked,
  own,
}: {
  row: KindChangeView
  blocked: string | null
  own: 'before' | 'after'
}) {
  const kind = TRANSFORM_KINDS[row.kind]
  const state = TRANSFORM_STATES[row.state]
  const trigger = TRANSFORM_TRIGGERS[row.trigger]
  const editing = useTransformAction(
    'transformation:edit',
    (vars: Edit) => ({ transformation_id: row.id, ...vars }),
    'The record keeps its new values'
  )
  const reverting = useTransformAction(
    'transform:revert',
    (_: void) => ({ transformation_id: row.id }),
    'The transformation is undone'
  )
  const removing = useTransformAction(
    'transformation:delete',
    (_: void) => ({ transformation_id: row.id }),
    'The record is struck out'
  )
  const other = own === 'before' ? row.subject : row.result
  const otherName = own === 'before' ? row.subject_name : row.result_name
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Epoch ${row.epoch}: ${row.text ?? (own === 'before' ? `was ${otherName || 'another thing'}` : `became ${otherName ?? 'another thing'}`)}`}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1'>
          <Chip icon={state.icon}>{state.label}</Chip>
          <Chip icon={trigger.icon}>{trigger.label}</Chip>
        </div>
      }
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Link2
          aria-hidden='true'
          className='size-icon-sm text-muted-foreground'
        />
        <Muted variant='caption'>
          {own === 'before' ? 'It was' : 'It became'}
        </Muted>
        <Ref node={other} empty={otherName || 'a thing no longer kept'} />
      </div>
      <RecordEditor
        title='Set this record'
        note='Values you set are held against the engine until you release them.'
        fields={RECORD_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Undo2}
          label='Undo it'
          busy={why(
            blocked ??
              (row.revertible
                ? null
                : row.state === 'reverted'
                  ? 'It is already undone'
                  : 'Only a change of this epoch that kept a ledger can be undone'),
            reverting.isPending
          )}
          onClick={() => reverting.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike out the record'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Prospect({
  row,
  nodeId,
  blocked,
}: {
  row: TransformProspectView
  nodeId: number
  blocked: string | null
}) {
  const kind = TRANSFORM_KINDS[row.kind]
  const stance = PROSPECT_STANCES[row.stance]
  const editing = useTransformAction(
    'transform_prospect:edit',
    (vars: Edit) => ({ prospect_id: row.id, ...vars }),
    'The prospect keeps its new values'
  )
  const removing = useTransformAction(
    'transform_prospect:delete',
    (_: void) => ({ prospect_id: row.id }),
    'The prospect is struck out'
  )
  const blocking = useTransformAction(
    row.stance === 'blocked' ? 'transform:release' : 'transform:block',
    (_: void) => ({ kind: row.kind, subject_id: nodeId }),
    row.stance === 'blocked' ? 'It may come again' : 'It is blocked'
  )
  const warned =
    row.warned_epoch !== null
      ? `; warned in epoch ${row.warned_epoch}, due in epoch ${row.due_epoch ?? row.warned_epoch}`
      : ''
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`${row.progress} of 100, last moved in epoch ${row.updated_epoch}${warned}`}
      aside={<Chip icon={stance.icon}>{stance.label}</Chip>}
    >
      <RecordEditor
        title='Set this prospect'
        note='Values you set are held against the engine until you release them.'
        fields={PROSPECT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={row.stance === 'blocked' ? ShieldCheck : Ban}
          label={row.stance === 'blocked' ? 'Let it come' : 'Block it'}
          busy={why(blocked, blocking.isPending)}
          onClick={() => blocking.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike out the prospect'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Hand({
  view,
  blocked,
}: {
  view: TransformNodeView
  blocked: string | null
}) {
  const choices = Object.fromEntries(
    view.open_kinds.map((kind) => [kind, TRANSFORM_KINDS[kind]])
  )
  const [picked, setPicked] = useState<string>(view.open_kinds[0] ?? '')
  const kind = (picked || view.open_kinds[0]) as TransformKind | undefined
  const forceable = kind !== undefined && view.forceable.includes(kind)
  const noKind = view.open_kinds.length
    ? null
    : 'Nothing of this kind changes into anything else'
  const forcing = useTransformAction(
    'transform:force',
    (_: void) => ({ kind: kind as TransformKind, subject_id: view.node.id }),
    'It is changed'
  )
  const blocking = useTransformAction(
    'transform:block',
    (_: void) => ({ kind: kind as TransformKind, subject_id: view.node.id }),
    'It is blocked'
  )
  const releasing = useTransformAction(
    'transform:release',
    (_: void) => ({ kind: kind as TransformKind, subject_id: view.node.id }),
    'It may come again'
  )
  const forceReason =
    blocked ??
    noKind ??
    (forceable
      ? null
      : 'This change happens at its own moment; it can be blocked but not forced')
  return (
    <ForgeCard
      icon={Zap}
      tone='gold'
      title='Your hand over its changes'
      note='Force a change now, or block it so it never comes until you let it.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={why(forceReason, forcing.isPending) !== null}
            disabledReason={why(forceReason, forcing.isPending) ?? undefined}
            onClick={() => forcing.mutate()}
          >
            <Zap />
            Force it now
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={why(blocked ?? noKind, blocking.isPending) !== null}
            disabledReason={
              why(blocked ?? noKind, blocking.isPending) ?? undefined
            }
            onClick={() => blocking.mutate()}
          >
            <Ban />
            Block it
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={why(blocked ?? noKind, releasing.isPending) !== null}
            disabledReason={
              why(blocked ?? noKind, releasing.isPending) ?? undefined
            }
            onClick={() => releasing.mutate()}
          >
            <ShieldCheck />
            Let it come
          </Button>
        </div>
      }
    >
      <ChoiceField
        label='The change'
        icon={TRANSFORM_ICON}
        value={kind ?? ''}
        table={choices}
        blocked={blocked ?? noKind}
        onPick={setPicked}
      />
    </ForgeCard>
  )
}

function Rescue({
  view,
  blocked,
}: {
  view: TransformNodeView
  blocked: string | null
}) {
  const sonId = view.node.id
  const [redeemer, setRedeemer] = useState(
    view.redeemers[0] ? String(view.redeemers[0].id) : ''
  )
  const [legend, setLegend] = useState(
    view.legends[0] ? String(view.legends[0].id) : ''
  )
  const cleansing = useTransformAction(
    'son:sanity',
    (_: void) => ({ son_id: sonId, value: view.corruption_band + 1 }),
    'The son is cleansed'
  )
  const forbidding = useTransformAction(
    'son:outer_bargain',
    (_: void) => ({ son_id: sonId, mode: 'forbid' as const }),
    'Bargains with the outside are forbidden to the son'
  )
  const chaining = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/punish', {
          params: { path: { son_id: sonId } },
          body: { kind: 'chain' },
        })
      ),
    success: 'The son is chained',
  })
  const ruling = useTransformAction(
    'ruling:decree',
    (_: void) => ({
      motion: 'punish_son' as const,
      target_id: sonId,
      punishment: 'chain' as const,
    }),
    'The council holds the son'
  )
  const questing = useTransformAction(
    'heroquest:begin',
    (_: void) => ({
      quester_id: Number(redeemer),
      legend_id: Number(legend),
    }),
    'A worshipper sets out to redeem the son'
  )
  const redeemers = Object.fromEntries(
    view.redeemers.map((node) => [
      String(node.id),
      { label: node.name, icon: Swords, tone: 'info' as const },
    ])
  )
  const legends = Object.fromEntries(
    view.legends.map((node) => [
      String(node.id),
      { label: node.name, icon: Sparkles, tone: 'verdigris' as const },
    ])
  )
  const questReason =
    blocked ??
    (!view.redeemers.length
      ? 'No mortal who worships this son can walk a heroquest'
      : !view.legends.length
        ? 'No legend tells of this son to walk'
        : null)
  return (
    <ForgeCard
      icon={ShieldCheck}
      tone='danger'
      title='Save it from corruption'
      note={`Its sanity is ${view.sanity ?? 0}; at or below ${view.corruption_band} after bargains with the outside it may pass out of the cosmos.`}
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <StepButton
            icon={Sun}
            label='Cleanse its mind'
            busy={why(blocked, cleansing.isPending)}
            onClick={() => cleansing.mutate()}
          />
          <StepButton
            icon={Ban}
            label='Forbid bargains'
            busy={why(blocked, forbidding.isPending)}
            onClick={() => forbidding.mutate()}
          />
          <StepButton
            icon={Lock}
            label='Chain it'
            busy={why(blocked, chaining.isPending)}
            onClick={() => chaining.mutate()}
          />
          <StepButton
            icon={Gavel}
            label='Have the council hold it'
            busy={why(blocked, ruling.isPending)}
            onClick={() => ruling.mutate()}
          />
          <StepButton
            icon={Swords}
            label='Send a redemption heroquest'
            busy={why(questReason, questing.isPending)}
            onClick={() => questing.mutate()}
          />
        </div>
      }
    >
      <ChoiceField
        label='Worshipper who walks it'
        icon={Swords}
        value={redeemer}
        table={redeemers}
        blocked={blocked ?? (view.redeemers.length ? null : 'No worshipper')}
        onPick={setRedeemer}
      />
      <ChoiceField
        label='Legend walked'
        icon={Sparkles}
        value={legend}
        table={legends}
        blocked={blocked ?? (view.legends.length ? null : 'No legend')}
        onPick={setLegend}
      />
    </ForgeCard>
  )
}

function Modifier({
  row,
  view,
  blocked,
}: {
  row: StarModifierView
  view: TransformNodeView
  blocked: string | null
}) {
  const source = STAR_MODIFIER_SOURCES[row.source]
  const editing = useTransformAction(
    'star_modifier:edit',
    (vars: Edit) => ({ modifier_id: row.id, ...vars }),
    'The change keeps its new values'
  )
  const removing = useTransformAction(
    'star_modifier:delete',
    (_: void) => ({ modifier_id: row.id }),
    'The change to its light is lifted'
  )
  return (
    <RecordRow
      icon={source.icon}
      tone={source.tone}
      title={`${row.luminosity_pct > 0 ? '+' : ''}${row.luminosity_pct} in a hundred of its light`}
      caption={`Since epoch ${row.epoch}; its life moved ${row.age_epochs} epochs forward${row.aged ? '' : ' (not yet)'}; fades ${row.decay} each epoch`}
      aside={<Chip icon={source.icon}>{source.label}</Chip>}
    >
      {row.cause ? (
        <div className='flex min-w-0 items-center gap-2'>
          <Muted variant='caption'>Brought about by</Muted>
          <Ref node={row.cause} />
        </div>
      ) : null}
      <RecordEditor
        title='Set this change'
        note='Values you set are held against the engine until you release them.'
        fields={modifierFields(view)}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Lift this change'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function StarLight({
  view,
  blocked,
}: {
  view: TransformNodeView
  blocked: string | null
}) {
  const [shift, setShift] = useState('-10')
  const [age, setAge] = useState('0')
  const [decay, setDecay] = useState('0')
  const page = useShowMore(view.star_modifiers, SHOWN, SHOWN * 2)
  const making = useTransformAction(
    'star_modifier:create',
    (_: void) => ({
      star_id: view.node.id,
      luminosity_pct: Number(shift) || 0,
      age_epochs: Number(age) || 0,
      decay: Number(decay) || 0,
    }),
    'The star’s light is changed'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <KpiTile
        label='Light changed by'
        value={`${view.luminosity_shift > 0 ? '+' : ''}${view.luminosity_shift} in a hundred`}
        icon={Sun}
        tone={view.luminosity_shift < 0 ? 'danger' : 'gold'}
      />
      {view.star_modifiers.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          {page.visible.map((row) => (
            <Modifier key={row.id} row={row} view={view} blocked={blocked} />
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={Sun}
          size='inline'
          title='Its light is its own'
          description='No death of a god and no hand has changed how brightly it burns.'
        />
      )}
      <ShowMore state={page} />
      <ForgeCard
        icon={Sun}
        tone='gold'
        title='Change how brightly it burns'
        note='The change sits on the light its mass and age give it; its worlds warm or cool with it.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={why(blocked, making.isPending) !== null}
            disabledReason={why(blocked, making.isPending) ?? undefined}
            onClick={() => making.mutate()}
          >
            <Sun />
            Change its light
          </Button>
        }
      >
        <NumberField
          label='Change, in a hundred'
          value={shift}
          min={-view.luminosity_shift_max}
          max={view.luminosity_shift_max}
          onChange={setShift}
        />
        <NumberField
          label='Epochs its life moves forward'
          value={age}
          max={MOST_EPOCHS}
          onChange={setAge}
        />
        <NumberField
          label='Fading each epoch'
          value={decay}
          max={100}
          onChange={setDecay}
        />
      </ForgeCard>
    </div>
  )
}

function Body({
  view,
  blocked,
}: {
  view: TransformNodeView
  blocked: string | null
}) {
  const before = useShowMore(view.came_from, SHOWN, SHOWN * 2)
  const after = useShowMore(view.became, SHOWN, SHOWN * 2)
  const ahead = useShowMore(view.prospects, SHOWN, SHOWN * 2)
  const end = view.end ? TRANSFORM_ENDS[view.end] : null
  const corrupting =
    view.son_status !== null &&
    view.son_status !== 'dead' &&
    ((view.sanity ?? 100) <= view.corruption_band ||
      view.prospects.some((row) => row.kind === 'corruption'))
  return (
    <div
      data-surface='TransformSection'
      className='flex min-w-0 flex-col gap-6'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
        <KpiTile
          label='Kind of thing'
          value={end?.label ?? 'Beyond change'}
          icon={end?.icon ?? TRANSFORM_ICON}
          tone={end?.tone ?? 'muted'}
        />
        <KpiTile
          label='Changes of kind'
          value={String(view.came_from.length + view.became.length)}
          icon={TRANSFORM_ICON}
          tone='info'
        />
        <KpiTile
          label='Changes under way'
          value={String(view.prospects.length)}
          icon={Zap}
          tone={view.prospects.length ? 'warning' : 'muted'}
        />
      </div>
      {view.son_status ? (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Chip icon={TRANSFORM_ICON}>{SON_STATUS_LABEL[view.son_status]}</Chip>
          {view.body ? (
            <>
              <Muted variant='caption'>Lives in the mortal body</Muted>
              <Ref node={view.body} />
            </>
          ) : null}
        </div>
      ) : null}
      {view.anchor_world || view.anchor_star ? (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Muted variant='caption'>Its body is</Muted>
          <Ref node={view.anchor_world ?? view.anchor_star} />
        </div>
      ) : null}
      <Section
        id='section-transformations-before'
        title='What it was before'
        description='The kinds of thing it was, and how it changed.'
        icon={Undo2}
        tone='muted'
      >
        {view.came_from.length ? (
          <ul className='flex min-w-0 flex-col gap-2'>
            {before.visible.map((row) => (
              <Change key={row.id} row={row} blocked={blocked} own='before' />
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={Undo2}
            size='inline'
            title='Always what it is'
            description='It has never been another kind of thing.'
          />
        )}
        <ShowMore state={before} />
      </Section>
      <Section
        id='section-transformations-after'
        title='What it became'
        description='What it turned into, kept even when it is gone.'
        icon={TRANSFORM_ICON}
        tone='info'
      >
        {view.became.length ? (
          <ul className='flex min-w-0 flex-col gap-2'>
            {after.visible.map((row) => (
              <Change key={row.id} row={row} blocked={blocked} own='after' />
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={TRANSFORM_ICON}
            size='inline'
            title='Not yet changed'
            description='It has not turned into anything else.'
          />
        )}
        <ShowMore state={after} />
      </Section>
      <Section
        id='section-transformations-ahead'
        title='Changes under way'
        description={`Conditions the engine watches each epoch; a fall or a corruption is announced ${plural(view.warn_epochs, 'epoch')} before it comes.`}
        icon={Zap}
        tone='warning'
      >
        <Bars
          chart='chart-transformations'
          title='Progress toward each change'
          legend={[{ text: 'Progress', variant: 'warning' }]}
          rows={ahead.visible.map((row) => ({
            key: String(row.id),
            caption: TRANSFORM_KINDS[row.kind].label,
            segments: [{ value: row.progress, fill: 'fill-warning' }],
          }))}
          max={100}
          noun={['change', 'changes']}
          empty='No change of kind is under way for it.'
        />
        {view.prospects.length ? (
          <ul className='flex min-w-0 flex-col gap-2'>
            {ahead.visible.map((row) => (
              <Prospect
                key={row.id}
                row={row}
                nodeId={view.node.id}
                blocked={blocked}
              />
            ))}
          </ul>
        ) : null}
        <ShowMore state={ahead} />
        <Hand view={view} blocked={blocked} />
        {corrupting ? <Rescue view={view} blocked={blocked} /> : null}
      </Section>
      {view.node.kind === 'star' ? (
        <Section
          id='section-transformations-light'
          title='Its light'
          description='Changes to how brightly it burns: the death of its god, or the Creator’s hand.'
          icon={Sun}
          tone='gold'
        >
          <StarLight view={view} blocked={blocked} />
        </Section>
      ) : null}
    </div>
  )
}

export function TransformSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeTransformations(nodeId)
  return (
    <Section
      id='section-transformations'
      title='Transformations'
      description='What it was, what it became, and the changes of kind ahead of it, each one yours to force, block or undo.'
      icon={TRANSFORM_ICON}
      tone='gold'
    >
      {query.isPending ? (
        <LoadingBlock label='Reading its changes of kind' />
      ) : query.isError ? (
        <EmptyState
          icon={TRANSFORM_ICON}
          size='inline'
          title='This could not be read'
          description={query.error.message}
        />
      ) : (
        <Body view={query.data} blocked={readOnlyReason} />
      )}
    </Section>
  )
}
