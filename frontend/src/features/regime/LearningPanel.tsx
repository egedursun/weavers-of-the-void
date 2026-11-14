import { useState } from 'react'
import {
  BookOpenCheck,
  GraduationCap,
  Library,
  Lock,
  School,
  Swords,
  UserPlus,
  Users,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp, MANY, SPAN } from '@/features/cycles/model'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { SKILL_ICONS } from '@/features/entity/mind/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type RegimeNodeView, type SchoolView, useRegimeAction } from './api'
import { CREDENTIALS, theNamed } from './labels'
import { DOCTRINE_TYPES, useRegimeRow, useRegimeStep } from './model'

type Examination = NonNullable<RegimeNodeView['examination']>
type Sitting = RegimeNodeView['sittings'][number]
type Credential = RegimeNodeView['credentials'][number]
type Freedom = NonNullable<RegimeNodeView['freedom']>
type Disciple = SchoolView['disciples'][number]

const NOT_REALM = 'Only a realm holds examinations'
const NOT_HOUSE = 'Only a house of learning has a freedom of its own'
const INTERVAL_MAX = 100

function skillLabel(skill: string | null) {
  return skill
    ? (SKILL_ICONS[skill]?.label ?? skill.replace(/_/g, ' '))
    : 'no one skill'
}

function ExamCard({
  polityId,
  row,
  blocked,
}: {
  polityId: number
  row: Examination
  blocked: string | null
}) {
  const action = useRegimeRow(
    'examination:edit',
    'examination:delete',
    { polity_id: polityId },
    blocked
  )
  const sitting = useRegimeStep(
    'examination:sit',
    { polity_id: polityId },
    blocked,
    'The examinations are held'
  )
  return (
    <Held
      icon={BookOpenCheck}
      tone='info'
      title={`Examinations every ${plural(row.interval, 'epoch', 'epochs')}`}
      caption={
        row.last_epoch === null
          ? 'Not yet held'
          : `Last held in epoch ${row.last_epoch}`
      }
      removeLabel='End the examinations'
      editTitle='Set the examinations'
      note='Scribes and nobles sit the examinations; the most learned notables earn credentials that open offices. When credentials outgrow the posts, graduates swell the aspirants and the realm demands ever more examinations.'
      fields={[
        {
          key: 'interval',
          label: 'Epochs between sittings',
          kind: 'number',
          min: 1,
          max: INTERVAL_MAX,
        },
        {
          key: 'quota',
          label: 'Places each sitting',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'pass_mark',
          label: 'Pass mark',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'demand',
          label: 'Demand for credentials',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'last_epoch',
          label: 'Last held in epoch',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-2'>
          <KpiTile
            label='Places'
            value={row.quota}
            icon={GraduationCap}
            tone='gold'
          />
          <KpiTile
            label='Pass mark'
            value={row.pass_mark}
            icon={BookOpenCheck}
            tone='info'
          />
        </div>
      </div>
      <Meter
        label='Demand for credentials'
        value={row.demand}
        tone='warning'
        icon={Users}
      />
      <StepButton
        icon={BookOpenCheck}
        label='Hold them now'
        busy={sitting.busy}
        onClick={sitting.run}
      />
    </Held>
  )
}

function ExamForge({
  polityId,
  isRealm,
  blocked,
}: {
  polityId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [every, setEvery] = useState('2')
  const [quota, setQuota] = useState('20')
  const [mark, setMark] = useState('50')
  const setting = useRegimeAction(
    'examination:set',
    (_: void) => ({
      polity_id: polityId,
      interval: clamp(every, INTERVAL_MAX, 1),
      quota: clamp(quota, MANY),
      pass_mark: clamp(mark),
    }),
    'The realm examines its officials'
  )
  const busy = why(isRealm ? blocked : NOT_REALM, setting.isPending)
  return (
    <ForgeCard
      icon={BookOpenCheck}
      tone='info'
      title='Choose officials by examination'
      note='Set how often the realm examines, how many it passes and how hard the test is.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <BookOpenCheck />
          Set them
        </Button>
      }
    >
      <NumberField
        label='Every epochs'
        value={every}
        min={1}
        max={INTERVAL_MAX}
        blocked={busy}
        onChange={setEvery}
      />
      <NumberField
        label='Places'
        value={quota}
        min={0}
        blocked={busy}
        onChange={setQuota}
      />
      <NumberField
        label='Pass mark'
        value={mark}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setMark}
      />
    </ForgeCard>
  )
}

function SittingCard({
  row,
  blocked,
}: {
  row: Sitting
  blocked: string | null
}) {
  const action = useRegimeRow(
    'exam_sitting:edit',
    'exam_sitting:delete',
    { sitting_id: row.id },
    blocked
  )
  return (
    <Held
      icon={GraduationCap}
      tone='gold'
      title={`${row.passed} of ${row.candidates} passed in ${row.polity.name}`}
      caption={`Epoch ${row.epoch} · pass mark ${row.mark}`}
      removeLabel='Strike the sitting'
      editTitle='Set the sitting'
      note='Each graduate presses for a post for several epochs and counts among the aspirants to the elite.'
      fields={[
        { key: 'candidates', label: 'Candidates', kind: 'number', min: 0 },
        { key: 'passed', label: 'Passed', kind: 'number', min: 0 },
        { key: 'mark', label: 'Pass mark', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function CredentialCard({
  row,
  blocked,
}: {
  row: Credential
  blocked: string | null
}) {
  const action = useRegimeRow(
    'credential:edit',
    'credential:delete',
    { credential_id: row.id },
    blocked
  )
  const kind = CREDENTIALS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={`${row.mortal.name}: ${kind.label.toLowerCase()}`}
      caption={`In ${skillLabel(row.skill).toLowerCase()} · epoch ${row.epoch}`}
      removeLabel='Revoke it'
      editTitle='Set the credential'
      note='Credentials raise their holder’s renown, weigh in appointments, put their holder first in line for office and, where the realm examines, open the career of office.'
      fields={[
        {
          key: 'kind',
          label: 'Credential',
          kind: 'pick',
          table: table(CREDENTIALS),
        },
        {
          key: 'granter_node_id',
          label: 'Granted by',
          kind: 'node',
          types: ['polity', 'structure', 'cult'],
        },
        {
          key: 'skill',
          label: 'In the learning of',
          kind: 'pick',
          table: table(SKILL_ICONS),
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
            'Granted by',
            <Ref key='granter' node={row.granter} empty='no one' />,
          ],
        ]}
      />
    </Held>
  )
}

function CredentialForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [credential, setCredential] =
    useState<keyof typeof CREDENTIALS>('master')
  const [skill, setSkill] = useState('lore')
  const [granter, setGranter] = useState<number | null>(
    kind === 'mortal' ? null : nodeId
  )
  const granting = useRegimeAction(
    'credential:grant',
    (_: void) => ({
      mortal_id: mortal ?? 0,
      kind: credential,
      granter_id: granter,
      skill: skill as never,
    }),
    'The credential is granted'
  )
  const busy = why(
    mortal === null ? 'Choose a mortal' : blocked,
    granting.isPending
  )
  return (
    <ForgeCard
      icon={GraduationCap}
      tone='gold'
      title='Grant a credential'
      note='A degree, an ordination or a pass in the examinations, in the learning you choose.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => granting.mutate()}
        >
          <GraduationCap />
          Grant it
        </Button>
      }
    >
      <NodePicker
        label='Holder'
        value={mortal}
        onChange={setMortal}
        blocked={blocked}
        types={['mortal']}
      />
      <MindPicker
        label='Credential'
        value={credential}
        table={table(CREDENTIALS)}
        blocked={blocked}
        onPick={(value) => setCredential(value as keyof typeof CREDENTIALS)}
      />
      <MindPicker
        label='In the learning of'
        value={skill}
        table={table(SKILL_ICONS)}
        blocked={blocked}
        onPick={setSkill}
      />
      <NodePicker
        label='Granted by'
        value={granter}
        onChange={setGranter}
        blocked={blocked}
        types={['polity', 'structure', 'cult']}
      />
    </ForgeCard>
  )
}

function FreedomCard({
  structureId,
  row,
  blocked,
}: {
  structureId: number
  row: Freedom
  blocked: string | null
}) {
  const action = useRegimeRow(
    'academic_freedom:edit',
    'academic_freedom:delete',
    { structure_id: structureId },
    blocked
  )
  return (
    <Held
      icon={row.suppressed ? Lock : Library}
      tone={row.suppressed ? 'danger' : 'success'}
      title={
        row.suppressed
          ? `Learning is suppressed at ${row.structure.name}`
          : `Learning is free at ${row.structure.name}`
      }
      caption={`Read in epoch ${row.updated_epoch}`}
      removeLabel='Let it be read anew'
      editTitle='Set the freedom of learning'
      note='Laws of censorship, a faith that guards its orthodoxy and the ruler’s regard for knowledge set the freedom of learning. Freedom quickens research and lets evidence weigh more when theories contend; suppression slows both and drives scholars to freer houses, carrying their techniques with them.'
      fields={[
        { key: 'level', label: 'Freedom', kind: 'number', min: 0, max: SPAN },
        {
          key: 'orthodoxy_node_id',
          label: 'Orthodoxy guarded by',
          kind: 'node',
          types: ['cult', 'polity'],
        },
        { key: 'suppressed', label: 'Suppressed', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Freedom of learning'
        value={row.level}
        tone={row.suppressed ? 'destructive' : 'success'}
        icon={Library}
      />
      <Facts
        items={[
          [
            'Orthodoxy guarded by',
            <Ref key='orthodoxy' node={row.orthodoxy} empty='no one' />,
          ],
        ]}
      />
    </Held>
  )
}

function FreedomForge({
  structureId,
  isStructure,
  blocked,
}: {
  structureId: number
  isStructure: boolean
  blocked: string | null
}) {
  const [level, setLevel] = useState('60')
  const setting = useRegimeAction(
    'academic_freedom:set',
    (_: void) => ({ structure_id: structureId, level: clamp(level) }),
    'The freedom is set'
  )
  const busy = why(isStructure ? blocked : NOT_HOUSE, setting.isPending)
  return (
    <ForgeCard
      icon={Library}
      tone='success'
      title='Set the freedom of this house of learning'
      note='From stifled to free; the engine keeps drifting it toward what laws and faith allow unless you hold it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Library />
          Set it
        </Button>
      }
    >
      <NumberField
        label='Freedom'
        value={level}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setLevel}
      />
    </ForgeCard>
  )
}

function DiscipleCard({
  schoolId,
  row,
  blocked,
}: {
  schoolId: number
  row: Disciple
  blocked: string | null
}) {
  const action = useRegimeRow(
    'disciple:edit',
    'disciple:delete',
    { school_id: schoolId, mortal_id: row.mortal.id },
    blocked
  )
  return (
    <Held
      icon={GraduationCap}
      tone='verdigris'
      title={`${row.mortal.name}, generation ${row.generation}`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Remove from the school'
      editTitle='Set the disciple'
      note='A disciple learns from a master each epoch; when the master dies the eldest line of the school takes the master’s place.'
      fields={[
        {
          key: 'master_entity_id',
          label: 'Master',
          kind: 'node',
          types: ['mortal'],
        },
        { key: 'generation', label: 'Generation', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Master', <Ref key='master' node={row.master} empty='a founder' />],
        ]}
      />
    </Held>
  )
}

function SchoolCard({
  row,
  rivals,
  blocked,
}: {
  row: SchoolView
  rivals: Record<string, string>
  blocked: string | null
}) {
  const action = useRegimeRow(
    'school:edit',
    'school:delete',
    { school_id: row.id },
    blocked
  )
  return (
    <Held
      icon={School}
      tone={row.persecuted ? 'danger' : 'gold'}
      title={row.name}
      caption={`${row.disciples.length} in the line · since epoch ${row.since_epoch}`}
      removeLabel='Dissolve the school'
      editTitle='Set the school'
      note='Masters teach disciples, a school quickens research where it gathers and keeps its knowledge from being forgotten; persecuted schools hold on to what others lose, and rival schools fall out.'
      fields={[
        { key: 'name', label: 'Name of the school', kind: 'text' },
        {
          key: 'doctrine_entity_id',
          label: 'Doctrine',
          kind: 'node',
          types: DOCTRINE_TYPES,
        },
        {
          key: 'founder_entity_id',
          label: 'Founder',
          kind: 'node',
          types: ['mortal'],
        },
        { key: 'rival_id', label: 'Rival school', kind: 'pick', table: rivals },
        { key: 'persecuted', label: 'Persecuted', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          {row.persecuted && <Chip icon={Lock}>Persecuted</Chip>}
          {row.rival && (
            <Chip icon={Swords}>{`Rival of ${theNamed(row.rival.name)}`}</Chip>
          )}
        </>
      }
    >
      <Facts
        items={[
          [
            'Founder',
            <Ref key='founder' node={row.founder} empty='forgotten' />,
          ],
          [
            'Doctrine',
            <Ref key='doctrine' node={row.doctrine} empty='its own' />,
          ],
        ]}
      />
      <Listed
        title='The line of masters and disciples'
        items={row.disciples}
        empty='The school has no living members.'
        noun={['member', 'members']}
        itemKey={(item) => item.mortal.id}
      >
        {(item) => (
          <DiscipleCard schoolId={row.id} row={item} blocked={blocked} />
        )}
      </Listed>
    </Held>
  )
}

function SchoolForge({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: RegimeNodeView
  blocked: string | null
}) {
  const [founder, setFounder] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [name, setName] = useState('')
  const [doctrine, setDoctrine] = useState<number | null>(
    kind === 'theory' || kind === 'ideology' ? nodeId : null
  )
  const [school, setSchool] = useState<string>(
    data.schools[0] ? String(data.schools[0].id) : ''
  )
  const [disciple, setDisciple] = useState<number | null>(null)
  const founding = useRegimeAction(
    'school:found',
    (_: void) => ({
      founder_id: founder ?? 0,
      name: name.trim(),
      doctrine_id: doctrine,
    }),
    'The school is founded'
  )
  const admitting = useRegimeAction(
    'disciple:admit',
    (_: void) => ({
      school_id: Number(school),
      mortal_id: disciple ?? 0,
      master_id:
        data.schools.find((item) => String(item.id) === school)?.founder?.id ??
        null,
    }),
    'A disciple joins'
  )
  const foundBusy = why(
    founder === null
      ? 'Choose a founder'
      : name.trim() === ''
        ? 'Name the school'
        : blocked,
    founding.isPending
  )
  const admitBusy = why(
    data.schools.length === 0
      ? 'No school is read here to admit a disciple to'
      : disciple === null
        ? 'Choose a disciple'
        : blocked,
    admitting.isPending
  )
  return (
    <>
      <ForgeCard
        icon={School}
        tone='gold'
        title='Found a school of thought'
        note='A founder, a name and, if you like, the theory or ideology it teaches.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={foundBusy !== null}
            disabledReason={foundBusy ?? undefined}
            onClick={() => founding.mutate()}
          >
            <School />
            Found it
          </Button>
        }
      >
        <NodePicker
          label='Founder'
          value={founder}
          onChange={setFounder}
          blocked={blocked}
          types={['mortal']}
        />
        <TextField
          label='Name of the school'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <NodePicker
          label='Doctrine'
          value={doctrine}
          onChange={setDoctrine}
          blocked={blocked}
          types={DOCTRINE_TYPES}
        />
      </ForgeCard>
      <ForgeCard
        icon={UserPlus}
        tone='verdigris'
        title='Admit a disciple'
        note='The disciple learns from the founder of the school.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={admitBusy !== null}
            disabledReason={admitBusy ?? undefined}
            onClick={() => admitting.mutate()}
          >
            <UserPlus />
            Admit them
          </Button>
        }
      >
        <MindPicker
          label='School'
          value={school}
          table={Object.fromEntries(
            data.schools.map((item) => [String(item.id), item.name])
          )}
          blocked={
            data.schools.length === 0 ? 'No school is read here' : blocked
          }
          onPick={setSchool}
        />
        <NodePicker
          label='Disciple'
          value={disciple}
          onChange={setDisciple}
          blocked={blocked}
          types={['mortal']}
        />
      </ForgeCard>
    </>
  )
}

export function LearningPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: RegimeNodeView
  blocked: string | null
}) {
  const isRealm = kind === 'polity'
  const isStructure = kind === 'structure'
  return (
    <div data-surface='LearningPanel' className='flex min-w-0 flex-col gap-4'>
      {data.examination ? (
        <ExamCard polityId={nodeId} row={data.examination} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isRealm
            ? 'This realm does not choose its officials by examination.'
            : NOT_REALM}
        </Muted>
      )}
      <ExamForge polityId={nodeId} isRealm={isRealm} blocked={blocked} />
      <Listed
        title='Sittings'
        items={data.sittings}
        empty='No examinations have been held here.'
        noun={['sitting', 'sittings']}
        itemKey={(item) => item.id}
      >
        {(item) => <SittingCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Credentials'
        items={data.credentials}
        empty='No credential was earned or granted here.'
        noun={['credential', 'credentials']}
        itemKey={(item) => item.id}
      >
        {(item) => <CredentialCard row={item} blocked={blocked} />}
      </Listed>
      <CredentialForge nodeId={nodeId} kind={kind} blocked={blocked} />
      {data.freedom ? (
        <FreedomCard
          structureId={nodeId}
          row={data.freedom}
          blocked={blocked}
        />
      ) : (
        <Muted variant='caption'>
          {isStructure
            ? 'The freedom of this house has not been read yet.'
            : NOT_HOUSE}
        </Muted>
      )}
      <FreedomForge
        structureId={nodeId}
        isStructure={isStructure}
        blocked={blocked}
      />
      <Listed
        title='Schools of thought'
        items={data.schools}
        empty='No school of thought gathers here.'
        noun={['school', 'schools']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <SchoolCard
            row={item}
            rivals={{
              none: 'No rival',
              ...Object.fromEntries(
                data.schools
                  .filter((other) => other.id !== item.id)
                  .map((other) => [String(other.id), other.name])
              ),
            }}
            blocked={blocked}
          />
        )}
      </Listed>
      <SchoolForge nodeId={nodeId} kind={kind} data={data} blocked={blocked} />
    </div>
  )
}
