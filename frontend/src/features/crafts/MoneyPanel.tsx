import { useState } from 'react'
import { Coins, Plus, ScrollText, ShieldCheck } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type CraftsNodeView, useCraftsAction } from './api'
import { ACQUIRED, COVERS, RIGHT_KINDS } from './labels'
import { MANY, SPAN, useCraftsRow } from './model'

type View = CraftsNodeView
type Insurer = NonNullable<View['insurer']>
type Policy = View['policies'][number]
type Right = View['rights'][number]

const INSURERS = ['faction'] as const
const HOLDERS = ['mortal', 'house', 'settlement', 'people', 'faction'] as const
const SUBJECTS = ['artwork', 'rite', 'house', 'structure'] as const

function InsurerCard({
  row,
  blocked,
}: {
  row: Insurer
  blocked: string | null
}) {
  const action = useCraftsRow(
    'insurer:edit',
    'insurer:delete',
    { insurer_id: row.insurer.id },
    blocked
  )
  return (
    <Held
      icon={ShieldCheck}
      tone={row.ruined ? 'danger' : 'gold'}
      title={`${row.insurer.name} insures`}
      caption={`Pool ${row.pool} · belief in risk ${row.risk_belief} · premium ${row.premium_pct}% · ${plural(row.claims_seen, 'claim', 'claims')} counted${row.ruined ? ' · ruined' : ''}`}
      removeLabel='Stop it insuring'
      editTitle='Set the insurer'
      note='Premiums fill the pool and claims drain it; a year of claims raises its belief in risk and so its premiums. A pool run dry ruins it, and those it insured turn against it.'
      fields={[
        { key: 'pool', label: 'Pool', kind: 'number', min: -MANY, max: MANY },
        {
          key: 'risk_belief',
          label: 'Belief in risk',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'premium_pct',
          label: 'Premium (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'ruined', label: 'Ruined', kind: 'pick', table: YES_NO },
        {
          key: 'claims_seen',
          label: 'Claims counted',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Belief in risk (${row.risk_belief} of ${SPAN})`}
        value={row.risk_belief}
        tone='warning'
        icon={ShieldCheck}
      />
    </Held>
  )
}

function PolicyCard({ row, blocked }: { row: Policy; blocked: string | null }) {
  const action = useCraftsRow(
    'insurance_policy:edit',
    'insurance_policy:delete',
    { record_id: row.id },
    blocked
  )
  const cover = COVERS[row.cover]
  return (
    <Held
      icon={cover.icon}
      tone={row.active ? cover.tone : 'muted'}
      title={`${cover.label} of ${row.holder.name}`}
      caption={`Premium ${row.premium} · pays up to ${row.sum_insured} · ${plural(row.claims, 'claim', 'claims')} · since epoch ${row.since_epoch}${row.active ? '' : ' · lapsed'}`}
      removeLabel='Tear up the policy'
      editTitle='Set the policy'
      note='The holder pays its premium each epoch or the policy lapses; a lost cargo, a struck town or an ended life is paid from the pool.'
      fields={[
        {
          key: 'insurer_entity_id',
          label: 'Insurer',
          kind: 'node',
          types: INSURERS,
        },
        { key: 'cover', label: 'Cover', kind: 'pick', table: table(COVERS) },
        {
          key: 'premium',
          label: 'Premium',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'sum_insured',
          label: 'Pays up to',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'active', label: 'In force', kind: 'pick', table: YES_NO },
        { key: 'claims', label: 'Claims', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Insurer', <Ref key='insurer' node={row.insurer} empty='no one' />],
          ['Holder', <Ref key='holder' node={row.holder} empty='no one' />],
        ]}
      />
    </Held>
  )
}

function choices(rows: { id: number; name: string }[]): Record<string, string> {
  return Object.fromEntries(rows.map((item) => [String(item.id), item.name]))
}

function RightCard({
  row,
  data,
  blocked,
}: {
  row: Right
  data: View
  blocked: string | null
}) {
  const techniques = Object.fromEntries(
    data.technique_choices.map((item) => [item.technique, item.label])
  )
  const contest = data.contest_choices.find(
    (item) => item.id === row.contest_id
  )
  const union = data.union_choices.find((item) => item.id === row.marriage_id)
  const action = useCraftsRow(
    'incorporeal_right:edit',
    'incorporeal_right:delete',
    { record_id: row.id },
    blocked
  )
  const kind = RIGHT_KINDS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={row.name}
      caption={`${kind.label} · ${ACQUIRED[row.acquired].label.toLowerCase()} · held since epoch ${row.since_epoch}`}
      removeLabel='Strike the right'
      editTitle='Set the right'
      note='A held right passes to the heir; others who take it up insult the holder, and copying a design or a mark is theft before the courts. A licensee pays the holder each epoch.'
      fields={[
        {
          key: 'holder_node_id',
          label: 'Holder',
          kind: 'node',
          types: HOLDERS,
        },
        {
          key: 'kind',
          label: 'Right to',
          kind: 'pick',
          table: table(RIGHT_KINDS),
        },
        {
          key: 'subject_node_id',
          label: 'Work or rite',
          kind: 'node',
          types: SUBJECTS,
        },
        { key: 'name', label: 'What it is called', kind: 'text' },
        {
          key: 'acquired',
          label: 'How it was had',
          kind: 'pick',
          table: table(ACQUIRED),
        },
        {
          key: 'licensed_to_node_id',
          label: 'Licensed to',
          kind: 'node',
          types: HOLDERS,
        },
        {
          key: 'dish_id',
          label: 'Dish of a recipe',
          kind: 'pick',
          table: choices(data.dish_choices),
        },
        {
          key: 'technique',
          label: 'Technique it covers',
          kind: 'pick',
          table: techniques,
        },
        {
          key: 'contest_id',
          label: 'Contest it was won in',
          kind: 'pick',
          table: choices(data.contest_choices),
        },
        {
          key: 'marriage_id',
          label: 'Union it passed with',
          kind: 'pick',
          table: choices(data.union_choices),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Holder', <Ref key='holder' node={row.holder} empty='no one' />],
          [
            'Of',
            <Ref key='subject' node={row.subject} empty='nothing named' />,
          ],
          [
            'Licensed to',
            <Ref key='licensee' node={row.licensed_to} empty='no one' />,
          ],
          ['Dish', row.dish ?? 'no dish'],
          ['Technique', row.technique_label ?? 'no technique'],
          ['Won in', contest !== undefined ? contest.name : 'no contest'],
          ['Passed with', union !== undefined ? union.name : 'no union'],
        ]}
      />
    </Held>
  )
}

export function MoneyPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const faction = kind === 'faction'
  const [insurer, setInsurer] = useState<number | null>(null)
  const [cover, setCover] = useState('life')
  const [rightKind, setRightKind] = useState('song')
  const [name, setName] = useState('')
  const [subject, setSubject] = useState<number | null>(null)
  const [dish, setDish] = useState('')
  const [technique, setTechnique] = useState('')
  const insuring = useCraftsAction(
    'insurer:set',
    (_: void) => ({ insurer_id: nodeId }),
    'It insures from now on'
  )
  const writing = useCraftsAction(
    'insurance_policy:create',
    (_: void) => ({
      insurer_entity_id: insurer ?? 0,
      holder_node_id: nodeId,
      cover: cover as Policy['cover'],
    }),
    'The policy is written'
  )
  const holding = useCraftsAction(
    'incorporeal_right:create',
    (_: void) => ({
      holder_node_id: nodeId,
      kind: rightKind as Right['kind'],
      subject_node_id: subject,
      name: name.trim(),
      dish_id: dish ? Number(dish) : null,
      technique: technique ? (technique as Right['technique']) : null,
    }),
    'The right is held'
  )
  const insurerBusy = why(
    blocked ??
      (!faction
        ? 'Only an association or company insures'
        : data.insurer
          ? 'It insures already; adjust it above'
          : null),
    insuring.isPending
  )
  const policyBusy = why(
    blocked ?? (insurer === null ? 'Choose an insurer' : null),
    writing.isPending
  )
  const rightBusy = why(
    blocked ??
      (!name.trim()
        ? 'Write what the right is called'
        : rightKind === 'recipe' && !dish
          ? 'A right to a recipe names a dish'
          : rightKind === 'technique' && !technique
            ? 'A right to a technique names a technique it holds'
            : null),
    holding.isPending
  )
  return (
    <div data-surface='MoneyPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-insurance'
        title='Policies and their claims'
        legend={[
          { text: 'Pays up to', variant: 'success' },
          { text: 'Claims', variant: 'destructive' },
        ]}
        rows={data.policies.map((row) => ({
          key: String(row.id),
          caption: `${COVERS[row.cover].label} of ${row.holder.name}: pays up to ${row.sum_insured}, ${plural(row.claims, 'claim', 'claims')}`,
          segments: [
            { value: Math.min(SPAN, row.sum_insured), fill: 'fill-success' },
            { value: Math.min(SPAN, row.claims), fill: 'fill-destructive' },
          ],
        }))}
        max={SPAN}
        noun={['policy', 'policies']}
        empty='Nothing here is insured.'
      />
      {data.insurer ? (
        <InsurerCard row={data.insurer} blocked={blocked} />
      ) : (
        <Muted variant='caption'>It insures no one.</Muted>
      )}
      <Listed
        title='Insurance policies'
        items={data.policies}
        empty='Nothing here is insured.'
        noun={['policy', 'policies']}
        itemKey={(item) => item.id}
      >
        {(item) => <PolicyCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Held rights'
        items={data.rights}
        empty='No right to a song, rite, design or name touches this.'
        noun={['right', 'rights']}
        itemKey={(item) => item.id}
      >
        {(item) => <RightCard row={item} data={data} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Coins}
        tone='gold'
        title='Insure'
        note='Let an association or company insure, or insure this with an insurer.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={insurerBusy !== null}
              disabledReason={insurerBusy ?? undefined}
              onClick={() => insuring.mutate()}
            >
              <ShieldCheck />
              Make it an insurer
            </Button>
            <Button
              size='sm'
              disabled={policyBusy !== null}
              disabledReason={policyBusy ?? undefined}
              onClick={() => writing.mutate()}
            >
              <Plus />
              Write a policy
            </Button>
          </div>
        }
      >
        <NodePicker
          label='Insurer'
          value={insurer}
          onChange={setInsurer}
          blocked={blocked}
          types={INSURERS}
        />
        <MindPicker
          label='Cover'
          value={cover}
          table={table(COVERS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setCover}
        />
      </ForgeCard>
      <ForgeCard
        icon={ScrollText}
        tone='verdigris'
        title='Give it a right'
        note='A right this holds to a song, a rite, a design, a name or a privilege.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={rightBusy !== null}
            disabledReason={rightBusy ?? undefined}
            onClick={() => holding.mutate()}
          >
            <Plus />
            Hold the right
          </Button>
        }
      >
        <MindPicker
          label='Right to'
          value={rightKind}
          table={table(RIGHT_KINDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setRightKind}
        />
        <TextField
          label='What it is called'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <NodePicker
          label='Work or rite'
          value={subject}
          onChange={setSubject}
          blocked={blocked}
          types={SUBJECTS}
        />
        <MindPicker
          label='Dish of a recipe'
          value={dish}
          table={choices(data.dish_choices)}
          placeholder='No dish'
          blocked={
            data.dish_choices.length === 0
              ? 'No dish is known in this world'
              : blocked
          }
          onPick={setDish}
        />
        <MindPicker
          label='Technique it covers'
          value={technique}
          table={Object.fromEntries(
            data.technique_choices.map((item) => [item.technique, item.label])
          )}
          placeholder='No technique'
          blocked={
            data.technique_choices.length === 0
              ? 'It holds no technique'
              : blocked
          }
          onPick={setTechnique}
        />
      </ForgeCard>
    </div>
  )
}
