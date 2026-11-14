import { useState } from 'react'
import { BookOpen, Flame, Plus, ScrollText, UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type TalesNodeView, useTalesAction } from './api'
import {
  OUTCOMES,
  PAYOFFS,
  ROLES,
  SETUP_KINDS,
  STAGES,
  TEMPLATES,
} from './labels'
import {
  FIGURE_TYPES,
  GOD_KINDS,
  MANY,
  SPAN,
  SUBJECT_TYPES,
  useTalesRow,
  useTalesStep,
} from './model'

type Arc = TalesNodeView['arcs'][number]
type Figure = Arc['figures'][number]
type Beat = Arc['history'][number]
type Setup = TalesNodeView['setups'][number]

const ENDED = 'That tale has ended'

function FigureCard({
  arc,
  row,
  blocked,
}: {
  arc: Arc
  row: Figure
  blocked: string | null
}) {
  const action = useTalesRow(
    'arc_figure:edit',
    'arc_figure:delete',
    { arc_id: arc.id, node_id: row.node.id },
    blocked
  )
  const role = ROLES[row.role]
  return (
    <Held
      icon={role.icon}
      tone={role.tone}
      title={row.node.name}
      caption={`${role.label} in the tale`}
      removeLabel='Take them out of the tale'
      editTitle='Set the figure'
      note='Figures are counterparts in the tale: a beat comes when the subject and a figure share an event, and a foe or rival who falls ends a revenge.'
      fields={[
        { key: 'role', label: 'Part', kind: 'pick', table: table(ROLES) },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={role} />}
    />
  )
}

function BeatCard({ row, blocked }: { row: Beat; blocked: string | null }) {
  const action = useTalesRow(
    'arc_beat:edit',
    'arc_beat:delete',
    { beat_id: row.id },
    blocked
  )
  const stage = STAGES[row.stage]
  return (
    <Held
      icon={stage.icon}
      tone={stage.tone}
      title={`${stage.label} in epoch ${row.epoch}`}
      caption={row.text || 'A turn of the tale'}
      removeLabel='Strike the beat'
      editTitle='Set the beat'
      note='A beat is a turn of the tale, written from the event that brought it.'
      fields={[
        { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        { key: 'text', label: 'What happened', kind: 'text', long: true },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function ArcForges({ arc, blocked }: { arc: Arc; blocked: string | null }) {
  const [figure, setFigure] = useState<number | null>(null)
  const [role, setRole] = useState('ally')
  const [stage, setStage] = useState('rising')
  const [text, setText] = useState('')
  const adding = useTalesAction(
    'arc_figure:create',
    (_: void) => ({
      arc_id: arc.id,
      node_id: figure ?? 0,
      role: role as Figure['role'],
    }),
    'A figure enters the tale'
  )
  const beating = useTalesAction(
    'arc_beat:create',
    (_: void) => ({ arc_id: arc.id, stage: stage as Beat['stage'], text }),
    'The tale takes a beat'
  )
  const closed = arc.outcome !== 'open' ? ENDED : null
  const figureBusy = why(
    blocked ?? closed ?? (figure === null ? 'Choose a figure' : null),
    adding.isPending
  )
  const beatBusy = why(blocked ?? closed, beating.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ForgeCard
        icon={UserPlus}
        tone='info'
        title='Bring a figure into the tale'
        note='A rival, a mentor, a beloved or a foe becomes a counterpart in this tale.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={figureBusy !== null}
            disabledReason={figureBusy ?? undefined}
            onClick={() => adding.mutate()}
          >
            <UserPlus />
            Bring them in
          </Button>
        }
      >
        <NodePicker
          label='Figure'
          value={figure}
          onChange={setFigure}
          blocked={blocked}
          types={FIGURE_TYPES}
          kinds={GOD_KINDS}
        />
        <MindPicker
          label='Part'
          value={role}
          table={table(ROLES)}
          placeholder='Choose a part'
          blocked={blocked}
          onPick={setRole}
        />
      </ForgeCard>
      <ForgeCard
        icon={ScrollText}
        tone='gold'
        title='Give the tale a beat'
        note='Move the tale to the stage you choose and write what happened.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={beatBusy !== null}
            disabledReason={beatBusy ?? undefined}
            onClick={() => beating.mutate()}
          >
            <Plus />
            Write it
          </Button>
        }
      >
        <MindPicker
          label='Stage'
          value={stage}
          table={table(STAGES)}
          placeholder='Choose a stage'
          blocked={blocked}
          onPick={setStage}
        />
        <TextField
          label='What happened'
          value={text}
          blocked={blocked}
          onChange={setText}
        />
      </ForgeCard>
    </div>
  )
}

function ArcCard({ row, blocked }: { row: Arc; blocked: string | null }) {
  const action = useTalesRow(
    'arc:edit',
    'arc:delete',
    { arc_id: row.id },
    blocked
  )
  const pressing = useTalesStep(
    'arc:press',
    { arc_id: row.id, drama: SPAN },
    blocked ?? (row.outcome !== 'open' ? ENDED : null),
    'The tale is pressed'
  )
  const template = TEMPLATES[row.template]
  const stage = STAGES[row.stage]
  const outcome = OUTCOMES[row.outcome]
  return (
    <Held
      icon={template.icon}
      tone={row.outcome === 'open' ? template.tone : outcome.tone}
      title={`${row.subject.name}: ${template.label}`}
      caption={`Begun in epoch ${row.started_epoch} · last beat in epoch ${row.last_beat_epoch}${row.ended_epoch !== null ? ` · ended in epoch ${row.ended_epoch}` : ''}${row.echo_id !== null ? ' · echoes an age before' : ''}`}
      removeLabel='Strike the tale'
      editTitle='Set the tale'
      note='A tale is read from the life it follows. It reaches its next stage when its subject and one of its figures share an event; it ends when its subject or its foe falls, fulfilled, failed, twisted or ironic. A tale that stalls gains drama, and drama makes the scheme or happening that would bring its next beat likelier, without forcing it.'
      fields={[
        {
          key: 'template',
          label: 'Kind of tale',
          kind: 'pick',
          table: table(TEMPLATES),
        },
        { key: 'stage', label: 'Stage', kind: 'pick', table: table(STAGES) },
        {
          key: 'outcome',
          label: 'Outcome',
          kind: 'pick',
          table: table(OUTCOMES),
        },
        { key: 'beats', label: 'Beats', kind: 'number', min: 0, max: MANY },
        { key: 'drama', label: 'Drama', kind: 'number', min: 0, max: SPAN },
        {
          key: 'ended_epoch',
          label: 'Ended in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={outcome} />}
    >
      <Meter
        label={`Drama (${row.drama} of ${SPAN})`}
        value={row.drama}
        tone='warning'
        icon={Flame}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile
            label='Stage'
            value={stage.label}
            icon={stage.icon}
            tone={stage.tone}
          />
          <KpiTile
            label='Beats'
            value={row.beats}
            icon={BookOpen}
            tone='info'
          />
        </div>
      </div>
      <Facts
        items={[
          ['Subject', <Ref key='subject' node={row.subject} empty='gone' />],
        ]}
      />
      <StepButton
        icon={Flame}
        label='Press it toward its next turn'
        busy={pressing.busy}
        onClick={pressing.run}
      />
      <Listed
        title='Figures'
        items={row.figures}
        empty='No figure stands in this tale yet.'
        noun={['figure', 'figures']}
        itemKey={(item) => item.node.id}
      >
        {(item) => <FigureCard arc={row} row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Beats'
        items={row.history}
        empty='The tale has taken no beat yet.'
        noun={['beat', 'beats']}
        itemKey={(item) => item.id}
      >
        {(item) => <BeatCard row={item} blocked={blocked} />}
      </Listed>
      <ArcForges arc={row} blocked={action.busy} />
    </Held>
  )
}

export function TalesPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: TalesNodeView
  blocked: string | null
}) {
  const subjectable = (SUBJECT_TYPES as readonly string[]).includes(kind ?? '')
  const [subject, setSubject] = useState<number | null>(
    subjectable ? nodeId : null
  )
  const [template, setTemplate] = useState('quest')
  const [figure, setFigure] = useState<number | null>(null)
  const [role, setRole] = useState('')
  const beginning = useTalesAction(
    'arc:create',
    (_: void) => ({
      subject_id: subject ?? 0,
      template: template as Arc['template'],
      figure_id: figure,
      role: role === '' ? null : (role as Figure['role']),
    }),
    'A tale begins'
  )
  const busy = why(
    blocked ?? (subject === null ? 'Choose whose life the tale follows' : null),
    beginning.isPending
  )
  return (
    <div data-surface='TalesPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-arc-drama'
        title='Drama of each tale'
        legend={[
          { text: 'Drama', variant: 'warning' },
          { text: 'The mark is its beats', variant: 'outline' },
        ]}
        rows={data.arcs.map((row) => ({
          key: row.id,
          caption: `${row.subject.name}: ${TEMPLATES[row.template].label.toLowerCase()}, ${STAGES[row.stage].label.toLowerCase()}, drama ${row.drama}`,
          segments: [{ value: row.drama, fill: 'fill-warning' }],
          mark: row.beats,
        }))}
        max={SPAN}
        noun={['tale', 'tales']}
        empty='No tale follows this life or counts it among its figures.'
      />
      <Listed
        title='Tales'
        items={data.arcs}
        empty='No tale follows this life or counts it among its figures.'
        noun={['tale', 'tales']}
        itemKey={(item) => item.id}
      >
        {(item) => <ArcCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={BookOpen}
        tone='gold'
        title='Begin a tale'
        note='A life takes the shape of a tale you choose, with a figure in a counterpart part if you name one.'
        columns={4}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => beginning.mutate()}
          >
            <BookOpen />
            Begin it
          </Button>
        }
      >
        <NodePicker
          label='Whose life'
          value={subject}
          onChange={setSubject}
          blocked={blocked}
          types={SUBJECT_TYPES}
          kinds={GOD_KINDS}
        />
        <MindPicker
          label='Kind of tale'
          value={template}
          table={table(TEMPLATES)}
          placeholder='Choose a tale'
          blocked={blocked}
          onPick={setTemplate}
        />
        <NodePicker
          label='Figure'
          value={figure}
          onChange={setFigure}
          blocked={blocked}
          types={FIGURE_TYPES}
          kinds={GOD_KINDS}
        />
        <MindPicker
          label='Their part'
          value={role}
          table={table(ROLES)}
          placeholder='An ally'
          blocked={blocked}
          onPick={setRole}
        />
      </ForgeCard>
      <Muted variant='caption'>
        Lives are read as tales from what happens in them: a killing of kin, a
        rivalry, an apprenticeship, a forbidden love, an exile, a flawed rule, a
        fall or a founding.
      </Muted>
    </div>
  )
}

function SetupCard({ row, blocked }: { row: Setup; blocked: string | null }) {
  const action = useTalesRow(
    'setup:edit',
    'setup:delete',
    { setup_id: row.id },
    blocked
  )
  const kind = SETUP_KINDS[row.kind]
  const payoff = PAYOFFS[row.payoff]
  return (
    <Held
      icon={kind.icon}
      tone={payoff.tone}
      title={`${kind.label} set up in epoch ${row.opened_epoch}`}
      caption={
        row.paid_epoch !== null
          ? `${payoff.label} in epoch ${row.paid_epoch}: ${row.payoff_text}`
          : payoff.label
      }
      removeLabel='Strike the setup'
      editTitle='Set the setup'
      note='Prophecies, omens, dreams, foresights and open stories are set up to be paid off. A payoff that fulfils or subverts them is told by the chroniclers as such; one never paid lapses.'
      fields={[
        {
          key: 'kind',
          label: 'Kind of setup',
          kind: 'pick',
          table: table(SETUP_KINDS),
        },
        {
          key: 'subject_node_id',
          label: 'About',
          kind: 'node',
          types: FIGURE_TYPES,
          kinds: GOD_KINDS,
        },
        { key: 'payoff', label: 'Payoff', kind: 'pick', table: table(PAYOFFS) },
        {
          key: 'paid_epoch',
          label: 'Paid in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'payoff_text',
          label: 'How it was paid',
          kind: 'text',
          long: true,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={payoff} />}
    >
      <Facts
        items={[
          ['About', <Ref key='subject' node={row.subject} empty='no one' />],
          ['Set up by record', row.source_id > 0 ? 'yes' : 'by a god'],
        ]}
      />
    </Held>
  )
}

export function SetupsPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: TalesNodeView
  blocked: string | null
}) {
  const [kindPick, setKindPick] = useState('omen')
  const setting = useTalesAction(
    'setup:create',
    (_: void) => ({
      kind: kindPick as Setup['kind'],
      source_id: 0,
      subject_id: nodeId,
    }),
    'Something is set up'
  )
  const busy = why(blocked, setting.isPending)
  return (
    <div data-surface='SetupsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-setups'
        title='Setups and their payoffs'
        legend={[
          { text: 'Waiting', variant: 'secondary' },
          { text: 'Paid', variant: 'success' },
        ]}
        rows={data.setups.map((row) => ({
          key: row.id,
          caption: `${SETUP_KINDS[row.kind].label} of epoch ${row.opened_epoch}: ${PAYOFFS[row.payoff].label.toLowerCase()}`,
          segments: [
            {
              value: SPAN,
              fill: row.payoff === 'open' ? 'fill-info' : 'fill-success',
            },
          ],
        }))}
        max={SPAN}
        noun={['setup', 'setups']}
        empty='Nothing is set up about this.'
      />
      <Listed
        title='Setups'
        items={data.setups}
        empty='Nothing is set up about this.'
        noun={['setup', 'setups']}
        itemKey={(item) => item.id}
      >
        {(item) => <SetupCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={ScrollText}
        tone='info'
        title='Set something up about this'
        note='The chroniclers will tell its payoff as such, or it lapses.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Plus />
            Set it up
          </Button>
        }
      >
        <MindPicker
          label='Kind of setup'
          value={kindPick}
          table={table(SETUP_KINDS)}
          placeholder='Choose a kind'
          blocked={blocked}
          onPick={setKindPick}
        />
        <Muted variant='caption'>
          It is about this record and lapses if nothing pays it off in time.
        </Muted>
      </ForgeCard>
    </div>
  )
}
