import { useState } from 'react'
import { Crown, Droplet, Droplets, Minus, Plus, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { PROFESSIONS } from '@/features/entity/mortal/labels'
import { NumberField } from '@/features/entity/realm/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type FolkwaysNodeView, useFolkwaysAction } from './api'
import { IMPURITY_SOURCES, PURIFICATIONS, PURITY_STATES } from './labels'
import { MANY, SPAN, useFolkwaysRow, useFolkwaysStep, withNone } from './model'

type Purity = NonNullable<FolkwaysNodeView['purity']>
type Rank = FolkwaysNodeView['ranks'][number]
type Source = FolkwaysNodeView['sources'][number]
type Method = FolkwaysNodeView['methods'][number]

const NOT_A_MORTAL = 'Only a mortal is pure or impure and holds a rank'
const NO_PEOPLE = 'Only a people, or one of its folk, keeps rules of purity'

function PurityCard({
  nodeId,
  row,
  ranks,
  blocked,
}: {
  nodeId: number
  row: Purity
  ranks: Rank[]
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'purity:edit',
    'purity:delete',
    { mortal_id: nodeId },
    blocked
  )
  const state = PURITY_STATES[row.state]
  const rank = ranks.find((item) => item.id === row.rank_id) ?? null
  const source = row.source ? IMPURITY_SOURCES[row.source] : null
  return (
    <Held
      icon={state.icon}
      tone={state.tone}
      title={state.label}
      caption={`Since epoch ${row.since_epoch}${row.until_epoch !== null ? ` until epoch ${row.until_epoch}` : ''}${rank ? ` · rank ${rank.name}` : ''}`}
      removeLabel='Forget its purity'
      editTitle='Set its purity'
      note='The impure are shut out of gatherings and shared meals, and the pure will not wed them; the defiled are cleansed only by a rite, not by waiting. A rank passes to children, bars marriage with other ranks where it is kept apart, and bars the professions of other ranks.'
      fields={[
        {
          key: 'state',
          label: 'State',
          kind: 'pick',
          table: table(PURITY_STATES),
        },
        {
          key: 'source',
          label: 'Made impure by',
          kind: 'pick',
          table: withNone(table(IMPURITY_SOURCES), 'Nothing'),
        },
        {
          key: 'until_epoch',
          label: 'Until epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'rank_id',
          label: 'Rank',
          kind: 'pick',
          table: withNone(
            Object.fromEntries(
              ranks.map((item) => [String(item.id), item.name])
            ),
            'No rank'
          ),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={source ? <Tag item={source} /> : undefined}
    />
  )
}

function SourceCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Source
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'impurity_source:edit',
    'impurity_source:delete',
    { people_id: people, source: row.source },
    blocked
  )
  const spec = IMPURITY_SOURCES[row.source]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={`Chance ${row.weight}% on a touch · lasts ${row.lasts} epochs`}
      removeLabel='Strike the source'
      editTitle='Set the source'
      note='What the people counts impure. A mortal who touches it is made impure by its chance, defiled if it weighs heavily enough, for as long as it lasts.'
      fields={[
        {
          key: 'weight',
          label: 'Chance on a touch',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'lasts',
          label: 'Lasts (epochs)',
          kind: 'number',
          min: 1,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Chance on a touch (${row.weight} of ${SPAN})`}
        value={row.weight}
        tone='warning'
        icon={spec.icon}
      />
    </Held>
  )
}

function MethodCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Method
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'purification:edit',
    'purification:delete',
    { people_id: people, method: row.method },
    blocked
  )
  const spec = PURIFICATIONS[row.method]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={`${row.epochs} epochs · costs ${row.cost} · succeeds ${row.success}%`}
      removeLabel='Strike the purification'
      editTitle='Set the purification'
      note='A way the people purifies. The impure take the cheapest way open to them once their impurity has run its course; waiting does not cleanse the defiled.'
      fields={[
        { key: 'epochs', label: 'Epochs', kind: 'number', min: 0, max: MANY },
        { key: 'cost', label: 'Cost', kind: 'number', min: 0, max: MANY },
        {
          key: 'success',
          label: 'Success (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function RankCard({ row, blocked }: { row: Rank; blocked: string | null }) {
  const action = useFolkwaysRow(
    'purity_rank:edit',
    'purity_rank:delete',
    { rank_id: row.id },
    blocked
  )
  const [job, setJob] = useState('farmer')
  const member = row.professions.includes(job)
  const working = useFolkwaysAction(
    'purity_rank:profession',
    (_: void) => ({
      rank_id: row.id,
      profession: job as never,
      member: !member,
    }),
    member ? 'The rank gives up that work' : 'The rank takes up that work'
  )
  const busy = why(blocked, working.isPending)
  return (
    <Held
      icon={Crown}
      tone='gold'
      title={row.name}
      caption={`Standing ${row.standing} · ${row.endogamous ? 'weds within' : 'weds beyond'} · ${row.commensal ? 'eats apart' : 'eats with all'}`}
      removeLabel='Strike the rank'
      editTitle='Set the rank'
      note='A hereditary rank of the people: its folk do the work it holds and no other rank may; where it weds within, its folk may not wed other ranks.'
      fields={[
        { key: 'name', label: 'Rank name', kind: 'text' },
        {
          key: 'standing',
          label: 'Standing',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'endogamous',
          label: 'Weds within',
          kind: 'pick',
          table: YES_NO,
        },
        { key: 'commensal', label: 'Eats apart', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='flex min-w-0 flex-wrap gap-1'>
        {row.professions.length ? (
          row.professions.map((item) => (
            <Badge key={item} size='sm' variant='secondary'>
              {PROFESSIONS[item]?.label ?? item}
            </Badge>
          ))
        ) : (
          <Muted variant='caption'>It holds no work of its own.</Muted>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <MindPicker
          label='Work'
          value={job}
          table={table(PROFESSIONS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setJob}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => working.mutate()}
        >
          {member ? <Minus /> : <Plus />}
          {member ? 'Take the work away' : 'Give it the work'}
        </Button>
      </div>
    </Held>
  )
}

export function PurityPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: FolkwaysNodeView
  blocked: string | null
}) {
  const mortal = kind === 'mortal'
  const people = data.people?.id ?? null
  const [source, setSource] = useState('the_dead')
  const [chance, setChance] = useState('50')
  const [method, setMethod] = useState('washing')
  const [cost, setCost] = useState('0')
  const [name, setName] = useState('')
  const [standing, setStanding] = useState('50')
  const marking = useFolkwaysAction(
    'purity:set',
    (_: void) => ({ mortal_id: nodeId, values: {} }),
    'Its purity is read'
  )
  const cleansing = useFolkwaysStep(
    'purity:cleanse',
    { mortal_id: nodeId },
    blocked ??
      (!mortal
        ? NOT_A_MORTAL
        : data.purity?.state === 'pure' || !data.purity
          ? 'It is pure already'
          : null),
    'It is made pure'
  )
  const sourcing = useFolkwaysAction(
    'impurity_source:set',
    (_: void) => ({
      people_id: people ?? 0,
      source: source as Source['source'],
      weight: Number(chance || '0'),
      lasts: 1,
    }),
    'The people counts it impure'
  )
  const purifying = useFolkwaysAction(
    'purification:set',
    (_: void) => ({
      people_id: people ?? 0,
      method: method as Method['method'],
      epochs: 1,
      cost: Number(cost || '0'),
      success: 80,
    }),
    'The people purifies so'
  )
  const ranking = useFolkwaysAction(
    'purity_rank:create',
    (_: void) => ({
      people_id: people ?? 0,
      name: name.trim(),
      standing: Number(standing || '0'),
      professions: [],
    }),
    'The rank is set'
  )
  const markBusy = why(
    blocked ??
      (!mortal
        ? NOT_A_MORTAL
        : data.purity
          ? 'Its purity is read; adjust it above'
          : null),
    marking.isPending
  )
  const sourceBusy = why(
    blocked ?? (people === null ? NO_PEOPLE : null),
    sourcing.isPending
  )
  const methodBusy = why(
    blocked ?? (people === null ? NO_PEOPLE : null),
    purifying.isPending
  )
  const rankBusy = why(
    blocked ??
      (people === null ? NO_PEOPLE : !name.trim() ? 'Name the rank' : null),
    ranking.isPending
  )
  return (
    <div data-surface='PurityPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-purity'
        title='What its people counts impure'
        legend={[{ text: 'Chance on a touch', variant: 'warning' }]}
        rows={data.sources.map((row) => ({
          key: row.source,
          caption: `${IMPURITY_SOURCES[row.source].label}: ${row.weight}%`,
          segments: [{ value: row.weight, fill: 'fill-warning' }],
        }))}
        max={SPAN}
        noun={['source', 'sources']}
        empty='Its people counts nothing impure.'
      />
      {data.purity && (
        <PurityCard
          nodeId={nodeId}
          row={data.purity}
          ranks={data.ranks}
          blocked={blocked}
        />
      )}
      <Listed
        title='Sources of impurity'
        items={data.sources}
        empty='Its people counts nothing impure.'
        noun={['source', 'sources']}
        itemKey={(item) => item.source}
      >
        {(item) => (
          <SourceCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      <Listed
        title='Purifications'
        items={data.methods}
        empty='Its people knows no way to purify.'
        noun={['purification', 'purifications']}
        itemKey={(item) => item.method}
      >
        {(item) => (
          <MethodCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      <Listed
        title='Ranks'
        items={data.ranks}
        empty='Its people keeps no ranks.'
        noun={['rank', 'ranks']}
        itemKey={(item) => item.id}
      >
        {(item) => <RankCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Droplet}
        tone='success'
        title='Its own purity'
        note='Read a mortal pure to hold its purity and rank by hand, or make it pure now.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Sparkles}
              label='Make it pure'
              busy={cleansing.busy}
              onClick={cleansing.run}
            />
            <Button
              size='sm'
              disabled={markBusy !== null}
              disabledReason={markBusy ?? undefined}
              onClick={() => marking.mutate()}
            >
              <Droplet />
              Read its purity
            </Button>
          </div>
        }
      >
        <Muted variant='caption'>
          {!mortal
            ? NOT_A_MORTAL
            : data.purity
              ? `It is ${PURITY_STATES[data.purity.state].label.toLowerCase()}.`
              : 'Its purity has not been read.'}
        </Muted>
      </ForgeCard>
      <ForgeCard
        icon={Droplets}
        tone='warning'
        title='Count something impure'
        note="Its people's folk who touch it are made impure by this chance."
        columns={2}
        action={
          <Button
            size='sm'
            disabled={sourceBusy !== null}
            disabledReason={sourceBusy ?? undefined}
            onClick={() => sourcing.mutate()}
          >
            <Plus />
            Count it impure
          </Button>
        }
      >
        <MindPicker
          label='Source'
          value={source}
          table={table(IMPURITY_SOURCES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSource}
        />
        <NumberField
          label='Chance on a touch'
          value={chance}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setChance}
        />
      </ForgeCard>
      <ForgeCard
        icon={Sparkles}
        tone='verdigris'
        title='Teach a way to purify'
        note='The impure take the cheapest way open to them.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={methodBusy !== null}
            disabledReason={methodBusy ?? undefined}
            onClick={() => purifying.mutate()}
          >
            <Plus />
            Teach it
          </Button>
        }
      >
        <MindPicker
          label='Way'
          value={method}
          table={table(PURIFICATIONS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMethod}
        />
        <NumberField
          label='Cost'
          value={cost}
          min={0}
          max={MANY}
          blocked={blocked}
          onChange={setCost}
        />
      </ForgeCard>
      <ForgeCard
        icon={Crown}
        tone='gold'
        title='Set a rank'
        note='A hereditary rank; give it work once it stands.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={rankBusy !== null}
            disabledReason={rankBusy ?? undefined}
            onClick={() => ranking.mutate()}
          >
            <Plus />
            Set the rank
          </Button>
        }
      >
        <TextField
          label='Rank name'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <NumberField
          label='Standing'
          value={standing}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setStanding}
        />
      </ForgeCard>
    </div>
  )
}
