import { useState } from 'react'
import {
  Baby,
  GitBranch,
  HeartHandshake,
  Recycle,
  ScrollText,
  Users,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
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
  ADOPTIONS,
  FIRST_SIDES,
  KIN_TERMS,
  DESCENTS,
  GROUPS,
  LEGACIES,
  RESIDENCES,
  SYSTEMS,
  YES_NO,
} from './labels'
import { clamp, LINE_TYPES, MANY, SPAN, useRow } from './model'
import { TextField } from './parts'
import {
  KIN_MATCHES,
  PARTNER_SCOPES,
  PLURAL_SIDES,
  UNION_ARRANGEMENTS,
  UNION_DESCENTS,
  UNION_DISSOLUTIONS,
  UNION_EXCHANGES,
  UNION_FORMS,
  UNION_PURPOSES,
  UNION_RESIDENCES,
} from './unionLabels'

type Kinship = NonNullable<CyclesView['kinship']>
type Union = NonNullable<CyclesView['union']>
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
          key: 'kin_terms',
          label: 'Kin terms',
          kind: 'pick',
          table: table(KIN_TERMS),
        },
        {
          key: 'adoption',
          label: 'Adoption custom',
          kind: 'pick',
          table: table(ADOPTIONS),
        },
        {
          key: 'first_side',
          label: 'Which side is first',
          kind: 'pick',
          table: table(FIRST_SIDES),
        },
        {
          key: 'sibling_union_first',
          label: 'Widow weds a sibling of the first side',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'sibling_union_second',
          label: 'Widow weds a sibling of the second side',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={KIN_TERMS[row.kin_terms].icon}>
            {KIN_TERMS[row.kin_terms].label}
          </Chip>
          <Chip icon={ADOPTIONS[row.adoption].icon}>
            {ADOPTIONS[row.adoption].label}
          </Chip>
          <Chip icon={FIRST_SIDES[row.first_side].icon}>
            {FIRST_SIDES[row.first_side].label}
          </Chip>
          {row.sibling_union_first && (
            <Chip icon={HeartHandshake}>Sibling union, first side</Chip>
          )}
          {row.sibling_union_second && (
            <Chip icon={HeartHandshake}>Sibling union, second side</Chip>
          )}
        </>
      }
    />
  )
}

const NO_SIDE = 'Choose which side the people counts as first'

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
    useState<keyof typeof RESIDENCES>('new_household')
  const [terms, setTerms] = useState<keyof typeof KIN_TERMS>('lineal')
  const [adoption, setAdoption] = useState<keyof typeof ADOPTIONS>('foster')
  const [side, setSide] = useState<keyof typeof FIRST_SIDES | ''>('')
  const setting = useCycleAction(
    'kinship:set',
    (_: void) => ({
      people_id: peopleId,
      descent,
      residence,
      kin_terms: terms,
      adoption,
      first_side: side === '' ? undefined : side,
    }),
    'Their ways of kin are set'
  )
  const busy = why(isPeople ? blocked : NOT_PEOPLE, setting.isPending)
  const ready = busy ?? (side === '' ? NO_SIDE : null)
  return (
    <ForgeCard
      icon={GitBranch}
      tone='verdigris'
      title='Set their ways of kin'
      note='Reckon descent, residence, kin terms and adoption. First and second are the two sides as the people names them.'
      columns={4}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={ready !== null}
          disabledReason={ready ?? undefined}
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
        label='Kin terms'
        value={terms}
        table={table(KIN_TERMS)}
        blocked={busy}
        onPick={(value) => setTerms(value as keyof typeof KIN_TERMS)}
      />
      <MindPicker
        label='Adoption custom'
        value={adoption}
        table={table(ADOPTIONS)}
        blocked={busy}
        onPick={(value) => setAdoption(value as keyof typeof ADOPTIONS)}
      />
      <MindPicker
        label='Which side is first'
        value={side}
        table={table(FIRST_SIDES)}
        blocked={busy}
        placeholder='Choose the first side'
        onPick={(value) => setSide(value as keyof typeof FIRST_SIDES)}
      />
    </ForgeCard>
  )
}

const UNION_NOTE =
  'First and second are the two sides of a union as the people names them. The form and circles allow or bar each match; the purpose weighs what a match is sought for; the joined move as residence says; the exchange passes as a gift; lines run as descent says; partings follow the way unions end; a term union ends when its term is out.'

function UnionCard({
  peopleId,
  row,
  blocked,
}: {
  peopleId: number
  row: Union
  blocked: string | null
}) {
  const action = useRow(
    'union:edit',
    'union:delete',
    { people_id: peopleId },
    blocked
  )
  const form = UNION_FORMS[row.form]
  return (
    <Held
      icon={form.icon}
      tone={form.tone ?? 'info'}
      title={`Unions: ${form.label.toLowerCase()}`}
      caption={`${UNION_PURPOSES[row.purpose].label} · ${UNION_RESIDENCES[row.residence].label}`}
      removeLabel='Read anew from their ways'
      editTitle='Set their customs of union'
      note={UNION_NOTE}
      fields={[
        {
          key: 'form',
          label: 'Form of a union',
          kind: 'pick',
          table: table(UNION_FORMS),
        },
        {
          key: 'plural_side',
          label: 'Side that may take several partners',
          kind: 'pick',
          table: table(PLURAL_SIDES),
        },
        {
          key: 'purpose',
          label: 'What unions are for',
          kind: 'pick',
          table: table(UNION_PURPOSES),
        },
        {
          key: 'residence',
          label: 'Where the joined live',
          kind: 'pick',
          table: table(UNION_RESIDENCES),
        },
        {
          key: 'descent',
          label: 'Through whom lines run',
          kind: 'pick',
          table: table(UNION_DESCENTS),
        },
        {
          key: 'exchange',
          label: 'What passes between families',
          kind: 'pick',
          table: table(UNION_EXCHANGES),
        },
        {
          key: 'exchange_value',
          label: 'Worth of the exchange',
          kind: 'number',
          min: 0,
        },
        {
          key: 'arrangement',
          label: 'Who arranges a union',
          kind: 'pick',
          table: table(UNION_ARRANGEMENTS),
        },
        {
          key: 'dissolution',
          label: 'How a union ends',
          kind: 'pick',
          table: table(UNION_DISSOLUTIONS),
        },
        {
          key: 'endogamy',
          label: 'Partners share their',
          kind: 'pick',
          table: table(PARTNER_SCOPES),
        },
        {
          key: 'exogamy',
          label: 'Partners come from another',
          kind: 'pick',
          table: table(PARTNER_SCOPES),
        },
        {
          key: 'kin_match',
          label: 'Kin sought as partners',
          kind: 'pick',
          table: table(KIN_MATCHES),
        },
        {
          key: 'term_epochs',
          label: 'Epochs a term union lasts',
          kind: 'number',
          min: 1,
          max: 100,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={UNION_DESCENTS[row.descent].icon}>
            Lines run {UNION_DESCENTS[row.descent].label.toLowerCase()}
          </Chip>
          {row.form === 'plural' && (
            <Chip icon={PLURAL_SIDES[row.plural_side].icon}>
              Several partners:{' '}
              {PLURAL_SIDES[row.plural_side].label.toLowerCase()}
            </Chip>
          )}
          <Chip icon={UNION_EXCHANGES[row.exchange].icon}>
            {row.exchange === 'none'
              ? UNION_EXCHANGES.none.label
              : `${UNION_EXCHANGES[row.exchange].label}, worth ${row.exchange_value}`}
          </Chip>
          <Chip icon={KIN_MATCHES[row.kin_match].icon}>
            {KIN_MATCHES[row.kin_match].label}
          </Chip>
          <Chip icon={UNION_ARRANGEMENTS[row.arrangement].icon}>
            {UNION_ARRANGEMENTS[row.arrangement].label}
          </Chip>
          <Chip icon={UNION_DISSOLUTIONS[row.dissolution].icon}>
            Ended {UNION_DISSOLUTIONS[row.dissolution].label.toLowerCase()}
          </Chip>
          <Chip icon={PARTNER_SCOPES[row.endogamy].icon}>
            {row.endogamy === 'none'
              ? 'Partners need share nothing'
              : `Partners share their ${PARTNER_SCOPES[row.endogamy].label.toLowerCase()}`}
          </Chip>
          <Chip icon={PARTNER_SCOPES[row.exogamy].icon}>
            {row.exogamy === 'none'
              ? 'Partners may come from anywhere'
              : `Partners come from another ${PARTNER_SCOPES[row.exogamy].label.toLowerCase()}`}
          </Chip>
          <Chip icon={UNION_FORMS.contract.icon}>
            A term union lasts {plural(row.term_epochs, 'epoch', 'epochs')}
          </Chip>
        </>
      }
    />
  )
}

function UnionForge({
  peopleId,
  isPeople,
  blocked,
}: {
  peopleId: number
  isPeople: boolean
  blocked: string | null
}) {
  const [form, setForm] = useState<Union['form']>('pair')
  const [side, setSide] = useState<Union['plural_side']>('either')
  const [worth, setWorth] = useState('10')
  const [kinMatch, setKinMatch] = useState<Union['kin_match']>('none')
  const [purpose, setPurpose] = useState<Union['purpose']>('kinship')
  const [residence, setResidence] =
    useState<Union['residence']>('new_household')
  const [descent, setDescent] = useState<Union['descent']>('through_both')
  const [exchange, setExchange] = useState<Union['exchange']>('none')
  const [arrangement, setArrangement] =
    useState<Union['arrangement']>('both_consent')
  const [dissolution, setDissolution] =
    useState<Union['dissolution']>('by_custom')
  const [endogamy, setEndogamy] = useState<Union['endogamy']>('none')
  const [exogamy, setExogamy] = useState<Union['exogamy']>('none')
  const [term, setTerm] = useState('4')
  const setting = useCycleAction(
    'union:set',
    (_: void) => ({
      people_id: peopleId,
      form,
      plural_side: side,
      purpose,
      residence,
      descent,
      exchange,
      exchange_value: clamp(worth, MANY, 0),
      arrangement,
      dissolution,
      endogamy,
      exogamy,
      kin_match: kinMatch,
      term_epochs: clamp(term, 100, 1),
    }),
    'Their customs of union are set'
  )
  const busy = why(isPeople ? blocked : NOT_PEOPLE, setting.isPending)
  return (
    <ForgeCard
      icon={HeartHandshake}
      tone='success'
      title='Set their customs of union'
      note='Shape what a union is among this people, from its form and purpose to how it ends; nothing here assumes who the partners are.'
      columns={4}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <HeartHandshake />
          Set their customs of union
        </Button>
      }
    >
      <MindPicker
        label='Form'
        value={form}
        table={table(UNION_FORMS)}
        blocked={busy}
        onPick={(value) => setForm(value as Union['form'])}
      />
      <MindPicker
        label='Several partners on'
        value={side}
        table={table(PLURAL_SIDES)}
        blocked={
          busy ?? (form === 'plural' ? null : 'Only a plural form names a side')
        }
        onPick={(value) => setSide(value as Union['plural_side'])}
      />
      <MindPicker
        label='Purpose'
        value={purpose}
        table={table(UNION_PURPOSES)}
        blocked={busy}
        onPick={(value) => setPurpose(value as Union['purpose'])}
      />
      <MindPicker
        label='Residence'
        value={residence}
        table={table(UNION_RESIDENCES)}
        blocked={busy}
        onPick={(value) => setResidence(value as Union['residence'])}
      />
      <MindPicker
        label='Lines run'
        value={descent}
        table={table(UNION_DESCENTS)}
        blocked={busy}
        onPick={(value) => setDescent(value as Union['descent'])}
      />
      <MindPicker
        label='Exchange'
        value={exchange}
        table={table(UNION_EXCHANGES)}
        blocked={busy}
        onPick={(value) => setExchange(value as Union['exchange'])}
      />
      <NumberField
        label='Worth of the exchange'
        value={worth}
        min={0}
        blocked={
          busy ??
          (exchange === 'none' ? 'Nothing passes, so nothing is worth' : null)
        }
        onChange={setWorth}
      />
      <MindPicker
        label='Arranged by'
        value={arrangement}
        table={table(UNION_ARRANGEMENTS)}
        blocked={busy}
        onPick={(value) => setArrangement(value as Union['arrangement'])}
      />
      <MindPicker
        label='Ended'
        value={dissolution}
        table={table(UNION_DISSOLUTIONS)}
        blocked={busy}
        onPick={(value) => setDissolution(value as Union['dissolution'])}
      />
      <MindPicker
        label='Partners share'
        value={endogamy}
        table={table(PARTNER_SCOPES)}
        blocked={busy}
        onPick={(value) => setEndogamy(value as Union['endogamy'])}
      />
      <MindPicker
        label='Partners from another'
        value={exogamy}
        table={table(PARTNER_SCOPES)}
        blocked={busy}
        onPick={(value) => setExogamy(value as Union['exogamy'])}
      />
      <MindPicker
        label='Kin sought'
        value={kinMatch}
        table={table(KIN_MATCHES)}
        blocked={busy}
        onPick={(value) => setKinMatch(value as Union['kin_match'])}
      />
      <NumberField
        label='Term in epochs'
        value={term}
        min={1}
        max={100}
        blocked={busy}
        onChange={setTerm}
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
      caption={`${plural(row.marriages, 'marriage', 'marriages')} since epoch ${row.since_epoch}, the last in epoch ${row.last_epoch}`}
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
          act={setting}
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
          act={setting}
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
          act={setting}
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
      note='A successor people keeps the ways, gods, techniques and arts of the people it came from, and of the peoples it took in, and names them in its founding myth.'
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
      note='Name a way of war or a rite by its key, a style by its five axes as ornament,geometry,colour,scale,symmetry from 0 to 100, a god or an art form by its id, a technique by its key, or a value.'
      columns={3}
      action={
        <Button
          act={setting}
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
      <TextField
        label='What is kept'
        value={key}
        blocked={isPeople ? blocked : NOT_PEOPLE}
        onChange={setKey}
      />
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
      {data.union ? (
        <UnionCard peopleId={nodeId} row={data.union} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isPeople
            ? 'Their customs of union are read at the next epoch.'
            : NOT_PEOPLE}
        </Muted>
      )}
      <UnionForge peopleId={nodeId} isPeople={isPeople} blocked={blocked} />
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
