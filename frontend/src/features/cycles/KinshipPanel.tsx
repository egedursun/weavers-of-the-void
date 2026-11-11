import { useState } from 'react'
import {
  Baby,
  GitBranch,
  HeartHandshake,
  Recycle,
  ScrollText,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type CyclesView, useCycleAction } from './api'
import {
  CASTES,
  COUSINS,
  DESCENTS,
  GROUPS,
  LEGACIES,
  PAYMENTS,
  PREFERENCES,
  RESIDENCES,
  SYSTEMS,
  YES_NO,
} from './labels'
import { clamp, LINE_TYPES, MANY, SPAN, useRow } from './model'

type Kinship = NonNullable<CyclesView['kinship']>
type Reproduction = NonNullable<CyclesView['reproduction']>
type Caste = NonNullable<CyclesView['caste']>
type Alliance = CyclesView['alliances'][number]
type Legacy = CyclesView['legacies'][number]

const NOT_PEOPLE = 'Only a people keeps these ways'
const NOT_MORTAL = 'Only a mortal has a caste'
const NOT_LINE = 'Alliances join houses or the lines of mortals'

function KinshipCard({
  peopleId,
  row,
  blocked,
}: {
  peopleId: number
  row: Kinship
  blocked: string | null
}) {
  const action = useRow(
    'kinship:edit',
    'kinship:delete',
    { people_id: peopleId },
    blocked
  )
  const descent = DESCENTS[row.descent]
  return (
    <Held
      icon={descent.icon}
      tone={descent.tone}
      title={descent.label}
      caption={`${RESIDENCES[row.residence].label} · ${GROUPS[row.descent_group].label}`}
      removeLabel='Read anew from their customs'
      editTitle='Set their ways of kin'
      note='Inheritance follows descent; couples move as residence says; matches weigh the preferred spouse; exchanges of spouses between lines build alliances and pacts; payments pass as gifts.'
      fields={[
        {
          key: 'descent',
          label: 'Descent',
          kind: 'pick',
          table: table(DESCENTS),
        },
        {
          key: 'residence',
          label: 'Where couples live',
          kind: 'pick',
          table: table(RESIDENCES),
        },
        {
          key: 'descent_group',
          label: 'Descent groups',
          kind: 'pick',
          table: table(GROUPS),
        },
        {
          key: 'cousin_terms',
          label: 'Cousin terms',
          kind: 'pick',
          table: table(COUSINS),
        },
        {
          key: 'preference',
          label: 'Preferred spouse',
          kind: 'pick',
          table: table(PREFERENCES),
        },
        {
          key: 'payment',
          label: 'Marriage payment',
          kind: 'pick',
          table: table(PAYMENTS),
        },
        {
          key: 'payment_value',
          label: 'Worth of the payment',
          kind: 'number',
          min: 0,
        },
        { key: 'levirate', label: 'Levirate', kind: 'pick', table: YES_NO },
        { key: 'sororate', label: 'Sororate', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={COUSINS[row.cousin_terms].icon}>
            {COUSINS[row.cousin_terms].label}
          </Chip>
          <Chip icon={PREFERENCES[row.preference].icon}>
            {PREFERENCES[row.preference].label}
          </Chip>
          <Chip icon={PAYMENTS[row.payment].icon}>
            {row.payment === 'none'
              ? PAYMENTS.none.label
              : `${PAYMENTS[row.payment].label}, ${row.payment_value}`}
          </Chip>
          {row.levirate && <Chip icon={HeartHandshake}>Levirate</Chip>}
          {row.sororate && <Chip icon={HeartHandshake}>Sororate</Chip>}
        </>
      }
    />
  )
}

function KinshipForge({
  peopleId,
  isPeople,
  blocked,
}: {
  peopleId: number
  isPeople: boolean
  blocked: string | null
}) {
  const [descent, setDescent] = useState<keyof typeof DESCENTS>('bilateral')
  const [residence, setResidence] =
    useState<keyof typeof RESIDENCES>('neolocal')
  const [preference, setPreference] = useState<keyof typeof PREFERENCES>('none')
  const [payment, setPayment] = useState<keyof typeof PAYMENTS>('none')
  const setting = useCycleAction(
    'kinship:set',
    (_: void) => ({
      people_id: peopleId,
      descent,
      residence,
      preference,
      payment,
    }),
    'Their ways of kin are set'
  )
  const busy = why(isPeople ? blocked : NOT_PEOPLE, setting.isPending)
  return (
    <ForgeCard
      icon={GitBranch}
      tone='verdigris'
      title='Set their ways of kin'
      note='Reckon descent, residence, the preferred spouse and the marriage payment.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <GitBranch />
          Set them
        </Button>
      }
    >
      <MindPicker
        label='Descent'
        value={descent}
        table={table(DESCENTS)}
        blocked={busy}
        onPick={(value) => setDescent(value as keyof typeof DESCENTS)}
      />
      <MindPicker
        label='Residence'
        value={residence}
        table={table(RESIDENCES)}
        blocked={busy}
        onPick={(value) => setResidence(value as keyof typeof RESIDENCES)}
      />
      <MindPicker
        label='Preferred spouse'
        value={preference}
        table={table(PREFERENCES)}
        blocked={busy}
        onPick={(value) => setPreference(value as keyof typeof PREFERENCES)}
      />
      <MindPicker
        label='Payment'
        value={payment}
        table={table(PAYMENTS)}
        blocked={busy}
        onPick={(value) => setPayment(value as keyof typeof PAYMENTS)}
      />
    </ForgeCard>
  )
}

function AllianceCard({
  row,
  blocked,
}: {
  row: Alliance
  blocked: string | null
}) {
  const action = useRow(
    'alliance:edit',
    'alliance:delete',
    { giver_id: row.giver.id, taker_id: row.taker.id },
    blocked
  )
  return (
    <Held
      icon={HeartHandshake}
      tone='success'
      title={`${row.giver.name} gives spouses to ${row.taker.name}`}
      caption={`${row.marriages} marriages since epoch ${row.since_epoch}, the last in epoch ${row.last_epoch}`}
      removeLabel='Strike the alliance'
      editTitle='Set the alliance'
      note='Each marriage between the lines builds regard; enough of them bind their realms in a marriage pact, and the line that gives more spouses than it takes ranks apart.'
      fields={[
        { key: 'marriages', label: 'Marriages', kind: 'number', min: 0 },
        {
          key: 'treaty_id',
          label: 'Marriage pact',
          kind: 'node',
          types: ['treaty'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Spouse-giving line', <Ref key='giver' node={row.giver} />],
          ['Spouse-taking line', <Ref key='taker' node={row.taker} />],
          ['Pact', <Ref key='treaty' node={row.treaty} empty='no pact yet' />],
        ]}
      />
    </Held>
  )
}

function AllianceForge({
  nodeId,
  isLine,
  blocked,
}: {
  nodeId: number
  isLine: boolean
  blocked: string | null
}) {
  const [other, setOther] = useState<number | null>(null)
  const [marriages, setMarriages] = useState('1')
  const setting = useCycleAction(
    'alliance:set',
    (_: void) => ({
      giver_id: nodeId,
      taker_id: other ?? 0,
      marriages: clamp(marriages, MANY),
    }),
    'The alliance is set'
  )
  const busy = why(
    isLine
      ? other === null
        ? 'Choose the line that takes the spouses'
        : blocked
      : NOT_LINE,
    setting.isPending
  )
  return (
    <ForgeCard
      icon={HeartHandshake}
      tone='success'
      title='Join two lines by marriage'
      note='This line gives spouses to the other.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <HeartHandshake />
          Join them
        </Button>
      }
    >
      <NodePicker
        label='Spouse-taking line'
        value={other}
        onChange={setOther}
        blocked={isLine ? blocked : NOT_LINE}
        types={LINE_TYPES}
      />
      <NumberField
        label='Marriages'
        value={marriages}
        min={0}
        blocked={isLine ? blocked : NOT_LINE}
        onChange={setMarriages}
      />
    </ForgeCard>
  )
}

function ReproductionCard({
  peopleId,
  row,
  blocked,
}: {
  peopleId: number
  row: Reproduction
  blocked: string | null
}) {
  const action = useRow(
    'reproduction:edit',
    'reproduction:delete',
    { people_id: peopleId },
    blocked
  )
  const system = SYSTEMS[row.system]
  return (
    <Held
      icon={system.icon}
      tone={system.tone}
      title={system.label}
      caption={
        row.system === 'sequential'
          ? `Sex changes at age ${row.change_age}`
          : 'How their young are born'
      }
      removeLabel='Read anew from their bodies'
      editTitle='Set how they bear their young'
      note='Births, the sexes of the newborn, who bears, who may marry, castes, growth and levies all follow the system.'
      fields={[
        { key: 'system', label: 'System', kind: 'pick', table: table(SYSTEMS) },
        {
          key: 'change_age',
          label: 'Age of the change',
          kind: 'number',
          min: 0,
        },
        {
          key: 'breeder_pct',
          label: 'Breeders (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'soldier_pct',
          label: 'Soldiers (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'worker_pct',
          label: 'Workers (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      {row.system === 'caste' ? (
        <div className='@container/tiles min-w-0'>
          <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-3'>
            <KpiTile
              label='Breeders'
              value={`${row.breeder_pct}%`}
              icon={CASTES.breeder.icon}
              tone='gold'
            />
            <KpiTile
              label='Soldiers'
              value={`${row.soldier_pct}%`}
              icon={CASTES.soldier.icon}
              tone='danger'
            />
            <KpiTile
              label='Workers'
              value={`${row.worker_pct}%`}
              icon={CASTES.worker.icon}
              tone='info'
            />
          </div>
        </div>
      ) : (
        <Facts
          items={[
            ['Age of the change', row.change_age],
            [
              'Breeders, soldiers, workers',
              `${row.breeder_pct}% · ${row.soldier_pct}% · ${row.worker_pct}%`,
            ],
          ]}
        />
      )}
    </Held>
  )
}

function ReproductionForge({
  peopleId,
  isPeople,
  blocked,
}: {
  peopleId: number
  isPeople: boolean
  blocked: string | null
}) {
  const [system, setSystem] = useState<keyof typeof SYSTEMS>('two_sex')
  const [age, setAge] = useState('30')
  const setting = useCycleAction(
    'reproduction:set',
    (_: void) => ({
      people_id: peopleId,
      system,
      change_age: clamp(age, MANY),
    }),
    'How they bear their young is set'
  )
  const busy = why(isPeople ? blocked : NOT_PEOPLE, setting.isPending)
  return (
    <ForgeCard
      icon={Baby}
      tone='info'
      title='Set how they bear their young'
      note='Two sexes, a change with age, either sex when fertile, castes or budding.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Recycle />
          Set it
        </Button>
      }
    >
      <MindPicker
        label='System'
        value={system}
        table={table(SYSTEMS)}
        blocked={busy}
        onPick={(value) => setSystem(value as keyof typeof SYSTEMS)}
      />
      <NumberField
        label='Age of the change'
        value={age}
        min={0}
        blocked={busy}
        onChange={setAge}
      />
    </ForgeCard>
  )
}

function CasteCard({
  mortalId,
  row,
  blocked,
}: {
  mortalId: number
  row: Caste
  blocked: string | null
}) {
  const action = useRow(
    'caste:edit',
    'caste:delete',
    { mortal_id: mortalId },
    blocked
  )
  const caste = CASTES[row.caste]
  return (
    <Held
      icon={caste.icon}
      tone={caste.tone}
      title={`Of the ${caste.label.toLowerCase()} caste`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Strike the caste'
      editTitle='Set the caste'
      note='In a caste people only breeders bear young and marry.'
      fields={[
        { key: 'caste', label: 'Caste', kind: 'pick', table: table(CASTES) },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function CasteForge({
  mortalId,
  isMortal,
  blocked,
}: {
  mortalId: number
  isMortal: boolean
  blocked: string | null
}) {
  const [caste, setCaste] = useState<keyof typeof CASTES>('worker')
  const setting = useCycleAction(
    'caste:set',
    (_: void) => ({ mortal_id: mortalId, caste }),
    'The caste is set'
  )
  const busy = why(isMortal ? blocked : NOT_MORTAL, setting.isPending)
  return (
    <ForgeCard
      icon={Users}
      tone='warning'
      title='Set a caste'
      note='Make this mortal a worker, a soldier or a breeder.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Users />
          Set it
        </Button>
      }
    >
      <MindPicker
        label='Caste'
        value={caste}
        table={table(CASTES)}
        blocked={busy}
        onPick={(value) => setCaste(value as keyof typeof CASTES)}
      />
    </ForgeCard>
  )
}

function LegacyCard({
  peopleId,
  row,
  blocked,
}: {
  peopleId: number
  row: Legacy
  blocked: string | null
}) {
  const action = useRow(
    'legacy:edit',
    'legacy:delete',
    { people_id: peopleId, kind: row.kind, key: row.key },
    blocked
  )
  const kind = LEGACIES[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${kind.label}: ${row.key_label}`}
      caption={`Kept since epoch ${row.since_epoch}`}
      removeLabel='Strike the legacy'
      editTitle='Set the legacy'
      note='A successor people keeps the ways of the people it came from, and names it in its founding myth.'
      fields={[
        {
          key: 'predecessor_entity_id',
          label: 'Kept from',
          kind: 'node',
          types: ['people'],
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          [
            'Kept from',
            <Ref key='from' node={row.predecessor} empty='their own past' />,
          ],
        ]}
      />
    </Held>
  )
}

function LegacyForge({
  peopleId,
  isPeople,
  blocked,
}: {
  peopleId: number
  isPeople: boolean
  blocked: string | null
}) {
  const [kind, setKind] = useState<keyof typeof LEGACIES>('martial_style')
  const [key, setKey] = useState('')
  const [from, setFrom] = useState<number | null>(null)
  const setting = useCycleAction(
    'legacy:set',
    (_: void) => ({
      people_id: peopleId,
      kind,
      key: key.trim(),
      predecessor_id: from,
    }),
    'The legacy is kept'
  )
  const busy = why(
    isPeople ? (key.trim() === '' ? 'Name what is kept' : blocked) : NOT_PEOPLE,
    setting.isPending
  )
  return (
    <ForgeCard
      icon={ScrollText}
      tone='gold'
      title='Have them keep a legacy'
      note='Name a way of war, an aesthetic or a rite by its key, a god by its id, or a value.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <ScrollText />
          Keep it
        </Button>
      }
    >
      <MindPicker
        label='Kind of legacy'
        value={kind}
        table={table(LEGACIES)}
        blocked={isPeople ? blocked : NOT_PEOPLE}
        onPick={(value) => setKind(value as keyof typeof LEGACIES)}
      />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`legacy-key-${peopleId}`}>What is kept</FieldLabel>
        <Input
          id={`legacy-key-${peopleId}`}
          value={key}
          disabled={!isPeople || blocked !== null}
          onChange={(event) => setKey(event.target.value)}
        />
      </div>
      <NodePicker
        label='Kept from'
        value={from}
        onChange={setFrom}
        blocked={isPeople ? blocked : NOT_PEOPLE}
        types={['people']}
      />
    </ForgeCard>
  )
}

export function KinshipPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: CyclesView
  blocked: string | null
}) {
  const isPeople = kind === 'people'
  const isMortal = kind === 'mortal'
  const isLine = kind === 'house' || isMortal
  return (
    <div data-surface='KinshipPanel' className='flex min-w-0 flex-col gap-4'>
      {data.kinship ? (
        <KinshipCard peopleId={nodeId} row={data.kinship} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isPeople
            ? 'Their ways of kin are read at the next epoch.'
            : NOT_PEOPLE}
        </Muted>
      )}
      <KinshipForge peopleId={nodeId} isPeople={isPeople} blocked={blocked} />
      {data.reproduction ? (
        <ReproductionCard
          peopleId={nodeId}
          row={data.reproduction}
          blocked={blocked}
        />
      ) : null}
      <ReproductionForge
        peopleId={nodeId}
        isPeople={isPeople}
        blocked={blocked}
      />
      {data.caste ? (
        <CasteCard mortalId={nodeId} row={data.caste} blocked={blocked} />
      ) : null}
      <CasteForge mortalId={nodeId} isMortal={isMortal} blocked={blocked} />
      <Listed
        title='Marriage alliances'
        items={data.alliances}
        empty='No line is bound to another by marriage here.'
        noun={['alliance', 'alliances']}
        itemKey={(item) => `${item.giver.id}-${item.taker.id}`}
      >
        {(item) => <AllianceCard row={item} blocked={blocked} />}
      </Listed>
      <AllianceForge nodeId={nodeId} isLine={isLine} blocked={blocked} />
      <Listed
        title='Legacies kept'
        items={data.legacies}
        empty='No legacy of an older people is kept here.'
        noun={['legacy', 'legacies']}
        itemKey={(item) => `${item.kind}-${item.key}`}
      >
        {(item) => (
          <LegacyCard peopleId={nodeId} row={item} blocked={blocked} />
        )}
      </Listed>
      <LegacyForge peopleId={nodeId} isPeople={isPeople} blocked={blocked} />
    </div>
  )
}
