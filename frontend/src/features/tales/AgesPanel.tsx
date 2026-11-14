import { useState } from 'react'
import { BookOpen, RefreshCcw, Repeat } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type TalesNodeView, useTalesAction } from './api'
import { CYCLES, ROLES, TEMPLATES, VARIANTS } from './labels'
import {
  MANY,
  MORTAL_TYPES,
  SPAN,
  useTalesRow,
  useTalesStep,
  withNoRole,
} from './model'

type Age = TalesNodeView['ages'][number]
type Echo = TalesNodeView['echoes'][number]

const LINEAR =
  'Only a cosmos that turns in ages can turn one; make it turn first'

function AgeCard({ row, blocked }: { row: Age; blocked: string | null }) {
  const action = useTalesRow(
    'age:edit',
    'age:delete',
    { age_id: row.id },
    blocked
  )
  const variant = row.variant ? VARIANTS[row.variant] : null
  return (
    <Held
      icon={row.ended_epoch === null ? RefreshCcw : BookOpen}
      tone={row.ended_epoch === null ? 'gold' : 'muted'}
      title={`Age ${row.number}`}
      caption={`From epoch ${row.began_epoch}${row.ended_epoch !== null ? ` to epoch ${row.ended_epoch}` : ', under way'}${variant ? ` · ended in ${variant.label.toLowerCase()}` : ''}`}
      removeLabel='Strike the age'
      editTitle='Set the age'
      note='When the doom clock runs out in a cosmos that turns in ages, the age ends: the ruins and relics of the age are found, its tales are half-remembered by the share it carries, its arts are lost by the rest, and its great lives echo into the next age.'
      fields={[
        { key: 'number', label: 'Number', kind: 'number', min: 1, max: MANY },
        {
          key: 'began_epoch',
          label: 'Began in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'ended_epoch',
          label: 'Ended in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'variant',
          label: 'Ended in',
          kind: 'pick',
          table: { none: 'Not ended', ...table(VARIANTS) },
        },
        {
          key: 'carried',
          label: 'Lore carried',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={variant ? <Tag item={variant} /> : undefined}
    >
      <Meter
        label={`Lore carried into the next age (${row.carried} of ${SPAN})`}
        value={row.carried}
        tone='info'
        icon={BookOpen}
      />
    </Held>
  )
}

function EchoCard({
  row,
  age,
  blocked,
}: {
  row: Echo
  age: number | null
  blocked: string | null
}) {
  const action = useTalesRow(
    'age_echo:edit',
    'age_echo:delete',
    { echo_id: row.id },
    blocked
  )
  const template = TEMPLATES[row.template]
  return (
    <Held
      icon={Repeat}
      tone={row.echo ? 'gold' : template.tone}
      title={`An echo of ${template.label.toLowerCase()}`}
      caption={`In age ${age ?? 'unknown'} · weight ${row.weight}${row.echo ? ` · reborn in ${row.echo.name}` : ' · not yet reborn'}`}
      removeLabel='Silence the echo'
      editTitle='Set the echo'
      note='A great life of an age before echoes into this one: its tale is read more readily, and a newborn may take it up, its soul reborn.'
      fields={[
        {
          key: 'template',
          label: 'Tale',
          kind: 'pick',
          table: table(TEMPLATES),
        },
        {
          key: 'role',
          label: 'Part',
          kind: 'pick',
          table: withNoRole(table(ROLES)),
        },
        {
          key: 'source_node_id',
          label: 'Life it echoes',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'echo_node_id',
          label: 'Reborn in',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        { key: 'weight', label: 'Weight', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={row.role ? <Tag item={ROLES[row.role]} /> : undefined}
    >
      <Facts
        items={[
          [
            'Life it echoes',
            <Ref key='source' node={row.source} empty='a life forgotten' />,
          ],
          ['Reborn in', <Ref key='echo' node={row.echo} empty='no one yet' />],
        ]}
      />
    </Held>
  )
}

export function AgesPanel({
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
  const cycle = CYCLES[data.cycle]
  const current = data.ages.find((row) => row.ended_epoch === null) ?? null
  const [pick, setPick] = useState<string>(data.cycle)
  const [source, setSource] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [template, setTemplate] = useState('quest')
  const setting = useTalesAction(
    'age:cycle',
    (_: void) => ({ cycle: pick as TalesNodeView['cycle'] }),
    'The course of the cosmos is set'
  )
  const turning = useTalesStep(
    'age:turn',
    {},
    blocked ?? (data.cycle === 'cyclic' ? null : LINEAR),
    'The age turns'
  )
  const echoing = useTalesAction(
    'age_echo:create',
    (_: void) => ({
      age_id: current?.id ?? 0,
      template: template as Echo['template'],
      source_id: source,
      weight: 60,
    }),
    'A life will echo'
  )
  const cycleBusy = why(
    blocked ??
      (pick === data.cycle ? 'That is already the course of the cosmos' : null),
    setting.isPending
  )
  const echoBusy = why(
    blocked ??
      (current === null
        ? 'No age is under way; the cosmos does not turn in ages'
        : null),
    echoing.isPending
  )
  return (
    <div data-surface='AgesPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-ages'
        title='Lore each age carried'
        legend={[
          { text: 'Carried', variant: 'secondary' },
          { text: 'Under way', variant: 'warning' },
        ]}
        rows={data.ages.map((row) => ({
          key: row.id,
          caption: `Age ${row.number}: from epoch ${row.began_epoch}${row.ended_epoch !== null ? `, carried ${row.carried}` : ', under way'}`,
          segments: [
            {
              value: row.ended_epoch === null ? SPAN : row.carried,
              fill: row.ended_epoch === null ? 'fill-warning' : 'fill-info',
            },
          ],
        }))}
        max={SPAN}
        noun={['age', 'ages']}
        empty='The cosmos has counted no age.'
      />
      <Muted variant='caption'>The cosmos {cycle.label.toLowerCase()}.</Muted>
      <Listed
        title='Ages'
        items={data.ages}
        empty='The cosmos has counted no age.'
        noun={['age', 'ages']}
        itemKey={(item) => item.id}
      >
        {(item) => <AgeCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Echoes'
        items={data.echoes}
        empty='No echo touches this.'
        noun={['echo', 'echoes']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <EchoCard
            row={item}
            age={
              data.ages.find((row) => row.id === item.age_id)?.number ?? null
            }
            blocked={blocked}
          />
        )}
      </Listed>
      <ForgeCard
        icon={RefreshCcw}
        tone='gold'
        title='The course of the cosmos'
        note='A cosmos that runs on ends each world it ruins; one that turns in ages begins a new age at each end.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={RefreshCcw}
              label='Turn the age now'
              busy={turning.busy}
              onClick={turning.run}
            />
            <Button
              size='sm'
              disabled={cycleBusy !== null}
              disabledReason={cycleBusy ?? undefined}
              onClick={() => setting.mutate()}
            >
              <RefreshCcw />
              Set the course
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Course'
          value={pick}
          table={table(CYCLES)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setPick}
        />
      </ForgeCard>
      <ForgeCard
        icon={Repeat}
        tone='info'
        title='Let a life echo'
        note='A life of this age echoes in the age under way: its tale is read more readily and a newborn may take it up.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={echoBusy !== null}
            disabledReason={echoBusy ?? undefined}
            onClick={() => echoing.mutate()}
          >
            <Repeat />
            Let it echo
          </Button>
        }
      >
        <NodePicker
          label='Life'
          value={source}
          onChange={setSource}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
        <MindPicker
          label='Tale'
          value={template}
          table={table(TEMPLATES)}
          placeholder='Choose a tale'
          blocked={blocked}
          onPick={setTemplate}
        />
      </ForgeCard>
    </div>
  )
}
