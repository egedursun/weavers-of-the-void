import { useState } from 'react'
import { Feather, Landmark, Plus, Tag as TagIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { ForgeCard } from '@/features/cosmography/parts'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Tag } from '@/features/wars/military/parts'
import { type CustomsNodeView, useCustomsAction } from './api'
import {
  GRADES,
  MARK_KINDS,
  MEANINGS,
  MEMBERSHIPS,
  NAME_FORMS,
  PATHS,
} from './labels'
import { MANY, REALM_TYPES, useCustomsRow } from './model'

type View = CustomsNodeView
type Mark = View['marks'][number]
type NameForm = View['names'][number]
type Member = NonNullable<View['membership']>

const NOT_A_MORTAL =
  'Only a mortal bears marks, names, an age-set and a standing in a realm'

function MarkCard({ row, blocked }: { row: Mark; blocked: string | null }) {
  const action = useCustomsRow(
    'body_mark:edit',
    'body_mark:delete',
    { record_id: row.id },
    blocked
  )
  const kind = MARK_KINDS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${kind.label} of ${MEANINGS[row.meaning].label.toLowerCase()}`}
      caption={`Placed in epoch ${row.placed_epoch}${row.augment_id !== null ? ' · shows an augment' : ''}`}
      removeLabel='Take the mark away'
      editTitle='Set the mark'
      note='Others read the mark: deeds and status bring renown, clan, marriage and age-set bind to the community, protection and mourning calm, and a brand of crime shames.'
      fields={[
        { key: 'kind', label: 'Mark', kind: 'pick', table: table(MARK_KINDS) },
        {
          key: 'meaning',
          label: 'Meaning',
          kind: 'pick',
          table: table(MEANINGS),
        },
        {
          key: 'placed_epoch',
          label: 'Placed in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={MEANINGS[row.meaning]} />}
    />
  )
}

function NameCard({
  holder,
  row,
  blocked,
}: {
  holder: number
  row: NameForm
  blocked: string | null
}) {
  const action = useCustomsRow(
    'name_form:edit',
    'name_form:delete',
    { holder_id: holder, form: row.form },
    blocked
  )
  const form = NAME_FORMS[row.form]
  return (
    <Held
      icon={form.icon}
      tone={form.tone}
      title={row.name}
      caption={`${form.label} · given in epoch ${row.given_epoch}`}
      removeLabel='Strike the name'
      editTitle='Set the name'
      note='A name given at a turn of life by the custom of its people; a secret name is the true name.'
      fields={[
        { key: 'name', label: 'Name given', kind: 'text' },
        {
          key: 'given_epoch',
          label: 'Given in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function MemberCard({
  holder,
  row,
  blocked,
}: {
  holder: number
  row: Member
  blocked: string | null
}) {
  const action = useCustomsRow(
    'membership:edit',
    'membership:delete',
    { mortal_id: holder },
    blocked
  )
  const category = MEMBERSHIPS[row.category]
  return (
    <Held
      icon={category.icon}
      tone={category.tone}
      title={`${category.label} of ${row.realm.name}`}
      caption={`${PATHS[row.path].label} · since epoch ${row.since_epoch}`}
      removeLabel='Strike the standing'
      editTitle='Set the standing'
      note='The rights of the category decide office, marriage, arms and the courts; a foreigner who lives long enough may be naturalised.'
      fields={[
        {
          key: 'polity_entity_id',
          label: 'Realm',
          kind: 'node',
          types: REALM_TYPES,
        },
        {
          key: 'category',
          label: 'Category',
          kind: 'pick',
          table: table(MEMBERSHIPS),
        },
        { key: 'path', label: 'Path', kind: 'pick', table: table(PATHS) },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Ref node={row.realm} empty='no realm' />
    </Held>
  )
}

export function BodyPanel({
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
  const mortal = kind === 'mortal'
  const [mark, setMark] = useState('tattoo')
  const [meaning, setMeaning] = useState('deed')
  const [form, setForm] = useState('deed')
  const [name, setName] = useState('')
  const [setId, setSetId] = useState(
    data.age_sets[0] ? String(data.age_sets[0].id) : ''
  )
  const [realm, setRealm] = useState<number | null>(
    data.membership?.realm.id ?? null
  )
  const [category, setCategory] = useState('citizen')
  const marking = useCustomsAction(
    'body_mark:create',
    (_: void) => ({
      holder_node_id: nodeId,
      kind: mark as Mark['kind'],
      meaning: meaning as Mark['meaning'],
    }),
    'The body is marked'
  )
  const naming = useCustomsAction(
    'name_form:set',
    (_: void) => ({
      holder_id: nodeId,
      form: form as NameForm['form'],
      name: name.trim(),
    }),
    'The name is given'
  )
  const joining = useCustomsAction(
    'age_set_member:set',
    (_: void) => ({ mortal_id: nodeId, age_set_id: Number(setId || '0') }),
    'It joins the age-set'
  )
  const leaving = useCustomsAction(
    'age_set_member:delete',
    (_: void) => ({ mortal_id: nodeId }),
    'It leaves the age-set'
  )
  const editing = useCustomsAction(
    'age_set_member:edit',
    (_: void) => ({
      mortal_id: nodeId,
      values: { age_set_id: Number(setId || '0') },
      release: [],
    }),
    'Set so'
  )
  const belonging = useCustomsAction(
    'membership:set',
    (_: void) => ({
      mortal_id: nodeId,
      polity_entity_id: realm ?? 0,
      category: category as Member['category'],
      path: 'grant',
    }),
    'Its standing is set'
  )
  const gate = blocked ?? (mortal ? null : NOT_A_MORTAL)
  const markBusy = why(gate, marking.isPending)
  const nameBusy = why(
    gate ?? (!name.trim() ? 'Write the name' : null),
    naming.isPending
  )
  const setBusy = why(
    gate ?? (!setId ? 'Its people binds no age-set' : null),
    joining.isPending,
    editing.isPending,
    leaving.isPending
  )
  const memberBusy = why(
    gate ?? (realm === null ? 'Choose a realm' : null),
    belonging.isPending
  )
  const current =
    data.age_sets.find((row) => row.id === data.age_set_id) ?? null
  return (
    <div data-surface='MarksPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Marks'
        items={data.marks}
        empty='It bears no mark.'
        noun={['mark', 'marks']}
        itemKey={(item) => item.id}
      >
        {(item) => <MarkCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Names'
        items={data.names}
        empty='It has been given no names by custom.'
        noun={['name', 'names']}
        itemKey={(item) => item.form}
      >
        {(item) => <NameCard holder={nodeId} row={item} blocked={blocked} />}
      </Listed>
      <Muted variant='caption'>
        {current
          ? `It belongs to the ${current.name}, in the grade of ${GRADES[current.grade].label.toLowerCase()}.`
          : 'It belongs to no age-set.'}
      </Muted>
      {data.membership ? (
        <MemberCard holder={nodeId} row={data.membership} blocked={blocked} />
      ) : (
        <Muted variant='caption'>It holds no standing in a realm.</Muted>
      )}
      <ForgeCard
        icon={TagIcon}
        tone='info'
        title='Mark it and name it'
        note='A mark of a meaning, and a name of a turn of life.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={markBusy !== null}
              disabledReason={markBusy ?? undefined}
              onClick={() => marking.mutate()}
            >
              <Plus />
              Mark it
            </Button>
            <Button
              size='sm'
              disabled={nameBusy !== null}
              disabledReason={nameBusy ?? undefined}
              onClick={() => naming.mutate()}
            >
              <Feather />
              Name it
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Mark'
          value={mark}
          table={table(MARK_KINDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMark}
        />
        <MindPicker
          label='Meaning'
          value={meaning}
          table={table(MEANINGS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setMeaning}
        />
        <MindPicker
          label='Name of'
          value={form}
          table={table(NAME_FORMS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setForm}
        />
        <TextField
          label='Name given'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
      </ForgeCard>
      <ForgeCard
        icon={GRADES.youths.icon}
        tone='verdigris'
        title='Its age-set'
        note='Set it among the age-sets of its people, or take it out.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              variant='outline'
              disabled={setBusy !== null || data.age_set_id === null}
              disabledReason={
                setBusy ??
                (data.age_set_id === null
                  ? 'It belongs to no age-set'
                  : undefined)
              }
              onClick={() => leaving.mutate()}
            >
              Take it out
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={setBusy !== null || data.age_set_id === null}
              disabledReason={
                setBusy ??
                (data.age_set_id === null
                  ? 'It belongs to no age-set'
                  : undefined)
              }
              onClick={() => editing.mutate()}
            >
              Move it
            </Button>
            <Button
              size='sm'
              disabled={setBusy !== null || data.age_set_id !== null}
              disabledReason={
                setBusy ??
                (data.age_set_id !== null
                  ? 'It belongs to one already; move it'
                  : undefined)
              }
              onClick={() => joining.mutate()}
            >
              <Plus />
              Set it
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Age-set'
          value={setId}
          table={Object.fromEntries(
            data.age_sets.map((row) => [String(row.id), row.name])
          )}
          placeholder='Choose'
          blocked={blocked}
          onPick={setSetId}
        />
      </ForgeCard>
      <ForgeCard
        icon={Landmark}
        tone='gold'
        title='Its standing in a realm'
        note='The category decides which rights it holds.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={memberBusy !== null}
            disabledReason={memberBusy ?? undefined}
            onClick={() => belonging.mutate()}
          >
            <Landmark />
            Set the standing
          </Button>
        }
      >
        <NodePicker
          label='Realm'
          value={realm}
          onChange={setRealm}
          blocked={blocked}
          types={REALM_TYPES}
        />
        <MindPicker
          label='Category'
          value={category}
          table={table(MEMBERSHIPS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setCategory}
        />
      </ForgeCard>
    </div>
  )
}
