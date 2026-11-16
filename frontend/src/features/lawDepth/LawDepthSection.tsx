import { type ReactNode, useState } from 'react'
import {
  Eye,
  Gavel,
  type LucideIcon,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { postAction } from '@/api/actions'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { useEntityType } from '@/features/arcana/model'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { CRIMES } from '@/features/entity/justice/crimes'
import { VERDICTS } from '@/features/entity/justice/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { NetworkGraph } from './NetworkGraph'
import {
  type AgentMotiveView,
  type AppealView,
  type CellView,
  type DefectionView,
  type JurisdictionView,
  type KillingView,
  type LawAction,
  type MoleHuntView,
  type NodeLawView,
  type OracleCaseView,
  type OutlawView,
  type PardonView,
  type PrecedentView,
  type PrisonerView,
  type PrisonView,
  type RegistryView,
  useLawAction,
  useNodeLaw,
} from './api'
import {
  CELL_ICON,
  CLAIMS,
  COURTS,
  DEED_ICON,
  HUNT_OUTCOMES,
  KILL_METHODS,
  LAW_DEPTH_ICON,
  LEGAL_SYSTEMS,
  MOTIVES,
  OUTLAW_ICON,
  PARDON_ICON,
  PRECEDENT_ICON,
  PRISON_ICON,
  PROTECTED,
  REGISTRY_KINDS,
  SEEN,
  YES_NO,
} from './labels'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }
type Field = Parameters<typeof RecordEditor>[0]['fields'][number]

const HOLDER_TYPES = ['polity', 'cult', 'settlement']
const VERDICT_PICK = { guilty: 'Guilty', acquitted: 'Acquitted' }
const SPAN = 100

function clamp(text: string, max = SPAN) {
  const value = Number(text)
  return Number.isNaN(value) ? 0 : Math.max(0, Math.min(max, Math.round(value)))
}

function Held({
  icon,
  tone,
  title,
  caption,
  removeLabel,
  editTitle,
  note,
  fields,
  locked,
  blocked,
  onEdit,
  onRemove,
  children,
  extra,
}: {
  icon: LucideIcon
  tone: KpiTone
  title: ReactNode
  caption: ReactNode
  removeLabel: string
  editTitle: string
  note: string
  fields: Field[]
  locked: string[]
  blocked: string | null
  onEdit: ((vars: Edit) => void) | null
  onRemove: () => void
  children?: ReactNode
  extra?: ReactNode
}) {
  return (
    <RecordRow
      icon={icon}
      tone={tone}
      title={title}
      caption={caption}
      aside={
        <div className='flex min-w-0 flex-wrap gap-2'>
          {extra}
          <Button
            size='sm'
            variant='ghost'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={onRemove}
          >
            <Trash2 />
            {removeLabel}
          </Button>
        </div>
      }
    >
      {children}
      {onEdit && (
        <RecordEditor
          title={editTitle}
          note={note}
          fields={fields}
          locked={locked}
          busy={blocked}
          onSave={(values) => onEdit({ values, release: [] })}
          onRelease={(release) => onEdit({ values: {}, release })}
        />
      )}
    </RecordRow>
  )
}

function useRow<E extends LawAction, D extends LawAction, K extends object>(
  edit: E,
  remove: D,
  keys: K,
  blocked: string | null
) {
  const editing = useLawAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useLawAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

function useRemove<D extends LawAction, K extends object>(
  remove: D,
  keys: K,
  blocked: string | null
) {
  const removing = useLawAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, removing.isPending),
    onRemove: () => removing.mutate(),
  }
}

function Listed<T>({
  title,
  items,
  empty,
  noun,
  itemKey,
  children,
}: {
  title: string
  items: T[]
  empty: string
  noun: [string, string]
  itemKey: (item: T) => string | number
  children: (item: T) => ReactNode
}) {
  return (
    <>
      <Label variant='overline'>{`${title} (${items.length})`}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={items}
          initial={3}
          noun={noun}
          className='flex min-w-0 flex-col gap-2'
          itemKey={itemKey}
        >
          {children}
        </PagedList>
      )}
    </>
  )
}

function SystemCard({
  holderId,
  data,
  blocked,
}: {
  holderId: number
  data: NodeLawView
  blocked: string | null
}) {
  const action = useRow(
    'legal_system:edit',
    'legal_system:delete',
    { holder_id: holderId },
    blocked
  )
  const system = data.system
  if (!system) return null
  const spec = LEGAL_SYSTEMS[system.system]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={`Its courts have judged so since epoch ${system.since_epoch}`}
      removeLabel='Let it be chosen anew'
      editTitle='Set the legal system'
      note='The system decides how disputes are judged: oaths and friends who swear, a code, the clergy, earlier rulings or a god’s answer.'
      fields={[
        {
          key: 'system',
          label: 'Legal system',
          kind: 'pick',
          table: table(LEGAL_SYSTEMS),
        },
      ]}
      locked={system.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function SystemForge({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const [system, setSystem] = useState('codified')
  const setting = useLawAction(
    'legal_system:set',
    (_: void) => ({
      holder_id: holderId,
      system: system as keyof typeof LEGAL_SYSTEMS,
    }),
    'The realm judges so now'
  )
  const busy = why(blocked, setting.isPending)
  return (
    <ForgeCard
      icon={LAW_DEPTH_ICON}
      tone='gold'
      title='Decree a legal system'
      note='Set and hold how this realm, cult or town makes law and judges disputes.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Gavel />
          Judge by it
        </Button>
      }
    >
      <MindPicker
        label='Legal system'
        value={system}
        table={table(LEGAL_SYSTEMS)}
        blocked={blocked}
        onPick={setSystem}
      />
    </ForgeCard>
  )
}

function PrecedentCard({
  row,
  blocked,
}: {
  row: PrecedentView
  blocked: string | null
}) {
  const action = useRow(
    'precedent:edit',
    'precedent:delete',
    { precedent_id: row.id },
    blocked
  )
  const crime = CRIMES[row.crime] ?? CRIMES.theft
  const verdict = VERDICTS[row.verdict] ?? VERDICTS.guilty
  return (
    <Held
      icon={PRECEDENT_ICON}
      tone={row.overturned ? 'muted' : 'verdigris'}
      title={`${crime.label}: ${verdict.label}`}
      caption={`${COURTS[row.court].label}, epoch ${row.epoch}${row.case_id ? `, from case ${row.case_id}` : ''}${row.overturned ? ' · set aside' : ''}`}
      removeLabel='Strike'
      editTitle='Set the precedent'
      note='Later courts follow a ruling by its authority; it grows when followed and fades with time.'
      fields={[
        {
          key: 'verdict',
          label: 'Ruling',
          kind: 'pick',
          table: VERDICT_PICK,
        },
        {
          key: 'authority',
          label: 'Authority',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'overturned',
          label: 'Set aside',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Authority' value={row.authority} tone='info' />
    </Held>
  )
}

function PrecedentForge({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const [crime, setCrime] = useState('theft')
  const [verdict, setVerdict] = useState('guilty')
  const [court, setCourt] = useState('local')
  const [authority, setAuthority] = useState('50')
  const adding = useLawAction(
    'precedent:add',
    (_: void) => ({
      holder_id: holderId,
      crime: crime as PrecedentView['crime'],
      verdict: verdict as PrecedentView['verdict'],
      court: court as PrecedentView['court'],
      authority: clamp(authority),
    }),
    'The ruling binds the courts'
  )
  const busy = why(blocked, adding.isPending)
  return (
    <ForgeCard
      icon={PRECEDENT_ICON}
      tone='verdigris'
      title='Set down a ruling'
      note='A precedent binds later courts of this realm on the same crime.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => adding.mutate()}
        >
          <Plus />
          Set it down
        </Button>
      }
    >
      <MindPicker
        label='Crime'
        value={crime}
        table={table(CRIMES)}
        blocked={blocked}
        onPick={setCrime}
      />
      <MindPicker
        label='Ruling'
        value={verdict}
        table={VERDICT_PICK}
        blocked={blocked}
        onPick={setVerdict}
      />
      <MindPicker
        label='Court'
        value={court}
        table={table(COURTS)}
        blocked={blocked}
        onPick={setCourt}
      />
      <NumberField
        label='Authority (0–100)'
        min={0}
        max={SPAN}
        value={authority}
        blocked={blocked}
        onChange={setAuthority}
      />
    </ForgeCard>
  )
}

function AppealCard({
  row,
  blocked,
}: {
  row: AppealView
  blocked: string | null
}) {
  const action = useRow(
    'appeal:edit',
    'appeal:delete',
    { case_id: row.case_id },
    blocked
  )
  const hearing = useLawAction(
    'appeal:hear',
    (_: void) => ({ case_id: row.case_id }),
    'The higher court has ruled'
  )
  const busy = why(action.busy, hearing.isPending)
  const decided = row.decided_epoch !== null && row.decided_epoch !== undefined
  return (
    <Held
      icon={COURTS[row.to_court].icon}
      tone={decided ? (row.reversed ? 'success' : 'muted') : 'info'}
      title={
        <>
          {`${CRIMES[row.crime]?.label ?? row.crime}: `}
          <Ref node={row.accused} empty='a lost accused' />
        </>
      }
      caption={`${COURTS[row.from_court].label} to ${COURTS[row.to_court].label.toLowerCase()}, fee ${row.fee}, filed epoch ${row.filed_epoch}${decided ? (row.reversed ? `, overturned in epoch ${row.decided_epoch}` : `, upheld in epoch ${row.decided_epoch}`) : ', waiting'}`}
      removeLabel='Withdraw'
      editTitle='Set the appeal'
      note='An appeal is heard after a delay; an advocate’s skill and weak evidence make a reversal likelier.'
      fields={[
        {
          key: 'to_court',
          label: 'Court above',
          kind: 'pick',
          table: table(COURTS),
        },
        { key: 'fee', label: 'Fee', kind: 'number', min: 0 },
        {
          key: 'reversed',
          label: 'Overturned',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || decided}
          disabledReason={
            busy ?? (decided ? 'The appeal is already decided' : undefined)
          }
          onClick={() => hearing.mutate()}
        >
          <Gavel />
          Hear it now
        </Button>
      }
    />
  )
}

function AppealForge({ blocked }: { blocked: string | null }) {
  const [caseId, setCaseId] = useState('')
  const [court, setCourt] = useState('provincial')
  const [fee, setFee] = useState('20')
  const filing = useLawAction(
    'appeal:file',
    (_: void) => ({
      case_id: clamp(caseId, Number.MAX_SAFE_INTEGER),
      to_court: court as AppealView['to_court'],
      fee: clamp(fee, 100000),
    }),
    'The appeal is filed'
  )
  const missing = caseId === '' ? 'Give the number of a conviction' : null
  const busy = why(blocked ?? missing, filing.isPending)
  return (
    <ForgeCard
      icon={COURTS.high.icon}
      tone='info'
      title='Carry a conviction higher'
      note='Bring a closed conviction before a higher court.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => filing.mutate()}
        >
          <Plus />
          File the appeal
        </Button>
      }
    >
      <NumberField
        label='Case number'
        min={1}
        value={caseId}
        blocked={blocked}
        onChange={setCaseId}
      />
      <MindPicker
        label='Court above'
        value={court}
        table={table(COURTS)}
        blocked={blocked}
        onPick={setCourt}
      />
      <NumberField
        label='Fee'
        min={0}
        value={fee}
        blocked={blocked}
        onChange={setFee}
      />
    </ForgeCard>
  )
}

function OracleCard({
  row,
  blocked,
}: {
  row: OracleCaseView
  blocked: string | null
}) {
  const [verdict, setVerdict] = useState<string>(row.oracle_answer ?? 'none')
  const answering = useLawAction(
    'oracle:answer',
    (_: void) => ({
      case_id: row.case_id,
      verdict:
        verdict === 'none'
          ? null
          : (verdict as NonNullable<OracleCaseView['oracle_answer']>),
    }),
    'The oracle will speak your answer'
  )
  const busy = why(blocked, answering.isPending)
  return (
    <RecordRow
      icon={Sparkles}
      tone='gold'
      title={
        <>
          {`${CRIMES[row.crime]?.label ?? row.crime}: `}
          <Ref node={row.accused} empty='a lost accused' />
        </>
      }
      caption={
        row.oracle_answer
          ? `The oracle will answer: ${VERDICTS[row.oracle_answer]?.label ?? row.oracle_answer}`
          : 'The oracle waits; unanswered, it names the truth only by chance.'
      }
      aside={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => answering.mutate()}
        >
          <Sparkles />
          Give the answer
        </Button>
      }
    >
      <MindPicker
        label='Your answer'
        value={verdict}
        table={{ none: 'Leave it to chance', ...VERDICT_PICK }}
        blocked={blocked}
        onPick={setVerdict}
      />
    </RecordRow>
  )
}

function RegistryCard({
  row,
  blocked,
}: {
  row: RegistryView
  blocked: string | null
}) {
  const action = useRow(
    'registry:edit',
    'registry:delete',
    { registry_id: row.id },
    blocked
  )
  const spec = REGISTRY_KINDS[row.kind]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={
        <>
          <Ref node={row.owner} empty='no owner' />
          {' over '}
          <Ref node={row.counterparty ?? row.subject} empty='nothing named' />
          {`, ${row.amount} owed, in the registry of `}
          <Ref node={row.holder} empty='a lost realm' />
          {` since epoch ${row.registered_epoch}`}
        </>
      }
      removeLabel='Strike'
      editTitle='Set the deed'
      note='Under a written code the courts make the other party pay what is registered; elsewhere it rests on strength.'
      fields={[
        { key: 'amount', label: 'Amount owed', kind: 'number', min: 0 },
        { key: 'owner_entity_id', label: 'Owner (id)', kind: 'number', min: 1 },
        {
          key: 'counterparty_entity_id',
          label: 'Other party (id)',
          kind: 'number',
          min: 1,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function RegistryForge({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const [kind, setKind] = useState('debt')
  const [owner, setOwner] = useState<number | null>(null)
  const [other, setOther] = useState<number | null>(null)
  const [amount, setAmount] = useState('50')
  const adding = useLawAction(
    'registry:add',
    (_: void) => ({
      holder_id: holderId,
      kind: kind as RegistryView['kind'],
      owner_id: owner,
      counterparty_id: kind === 'land_title' ? null : other,
      subject_id: kind === 'land_title' ? other : null,
      amount: clamp(amount, 100000),
    }),
    'The deed is registered'
  )
  const missing = owner === null ? 'Choose who holds the right' : null
  const busy = why(blocked ?? missing, adding.isPending)
  return (
    <ForgeCard
      icon={DEED_ICON}
      tone='gold'
      title='Register a deed'
      note='Record a title or a contract in this registry.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => adding.mutate()}
        >
          <Plus />
          Register it
        </Button>
      }
    >
      <MindPicker
        label='Deed'
        value={kind}
        table={table(REGISTRY_KINDS)}
        blocked={blocked}
        onPick={setKind}
      />
      <NodePicker
        label='Holder of the right'
        value={owner}
        onChange={setOwner}
        blocked={blocked}
      />
      <NodePicker
        label={kind === 'land_title' ? 'The land' : 'The other party'}
        value={other}
        onChange={setOther}
        blocked={blocked}
      />
      <NumberField
        label='Amount'
        min={0}
        value={amount}
        blocked={blocked}
        onChange={setAmount}
      />
    </ForgeCard>
  )
}

function ClaimCard({
  row,
  blocked,
}: {
  row: JurisdictionView
  blocked: string | null
}) {
  const action = useRow(
    'jurisdiction:edit',
    'jurisdiction:delete',
    {
      holder_id: row.holder?.id ?? 0,
      claimant_id: row.claimant?.id ?? 0,
      claim: row.claim,
    },
    blocked
  )
  const spec = CLAIMS[row.claim]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={
        <>
          <Ref node={row.claimant} empty='a lost claimant' />
          {` claims ${spec.label.toLowerCase()}`}
        </>
      }
      caption={
        <>
          {'In '}
          <Ref node={row.holder} empty='a lost realm' />
          {` since epoch ${row.since_epoch}`}
        </>
      }
      removeLabel='End the claim'
      editTitle='Set the claim'
      note='A strong claim spares the claimant’s members in court and, past a point, becomes a struggle with the crown.'
      fields={[
        {
          key: 'strength',
          label: 'Strength',
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
      <Meter label='Strength' value={row.strength} tone='warning' />
    </Held>
  )
}

function ClaimForge({
  holderId,
  blocked,
}: {
  holderId: number
  blocked: string | null
}) {
  const [claimant, setClaimant] = useState<number | null>(null)
  const [claim, setClaim] = useState('clergy')
  const [strength, setStrength] = useState('50')
  const setting = useLawAction(
    'jurisdiction:set',
    (_: void) => ({
      holder_id: holderId,
      claimant_id: claimant ?? 0,
      claim: claim as JurisdictionView['claim'],
      strength: clamp(strength),
    }),
    'The claim is made'
  )
  const missing = claimant === null ? 'Choose who claims the courts' : null
  const busy = why(blocked ?? missing, setting.isPending)
  return (
    <ForgeCard
      icon={CLAIMS.clergy.icon}
      tone='warning'
      title='Grant courts of their own'
      note='Let a church, a guild or a foreign realm judge its own in this realm.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Plus />
          Grant the claim
        </Button>
      }
    >
      <NodePicker
        label='Claimant'
        value={claimant}
        onChange={setClaimant}
        blocked={blocked}
        types={['cult', 'faction', 'polity']}
      />
      <MindPicker
        label='Claim'
        value={claim}
        table={table(CLAIMS)}
        blocked={blocked}
        onPick={setClaim}
      />
      <NumberField
        label='Strength (0–100)'
        min={0}
        max={SPAN}
        value={strength}
        blocked={blocked}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

function PardonCard({
  row,
  blocked,
}: {
  row: PardonView
  blocked: string | null
}) {
  const action = useRemove('pardon:delete', { pardon_id: row.id }, blocked)
  return (
    <Held
      icon={PARDON_ICON}
      tone={row.corrupt ? 'danger' : row.amnesty ? 'gold' : 'success'}
      title={
        row.amnesty ? (
          'An amnesty'
        ) : (
          <>
            {'Pardon of '}
            <Ref node={row.pardoned} empty='a lost mortal' />
          </>
        )
      }
      caption={
        <>
          {'Granted by '}
          <Ref node={row.granter} empty='a lost ruler' />
          {` in epoch ${row.epoch}${row.case_id ? `, for case ${row.case_id}` : ''}${row.corrupt ? ' · read as corruption' : ''}`}
        </>
      }
      removeLabel='Strike from the record'
      editTitle=''
      note=''
      fields={[]}
      locked={[]}
      blocked={action.busy}
      onEdit={null}
      onRemove={action.onRemove}
    />
  )
}

function MercyForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [granter, setGranter] = useState<number | null>(
    type === 'mortal' ? nodeId : null
  )
  const [pardoned, setPardoned] = useState<number | null>(null)
  const pardon = useLawAction(
    'pardon:grant',
    (_: void) => ({ granter_id: granter ?? 0, mortal_id: pardoned ?? 0 }),
    'The pardon is granted'
  )
  const amnesty = useLawAction(
    'amnesty:declare',
    (_: void) => ({ polity_id: nodeId }),
    'The amnesty is declared'
  )
  const missing =
    granter === null || pardoned === null
      ? 'Choose who pardons and who is pardoned'
      : null
  const busy = why(blocked ?? missing, pardon.isPending)
  const realm = type === 'polity' ? null : 'Only a realm declares an amnesty'
  const amnestyBusy = why(blocked ?? realm, amnesty.isPending)
  return (
    <ForgeCard
      icon={PARDON_ICON}
      tone='success'
      title='Show mercy'
      note='A pardon frees one prisoner or outlaw; an amnesty frees every one of a realm.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => pardon.mutate()}
          >
            <Plus />
            Pardon
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={amnestyBusy !== null}
            disabledReason={amnestyBusy ?? undefined}
            onClick={() => amnesty.mutate()}
          >
            <PARDON_ICON />
            Declare an amnesty
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Who pardons'
        value={granter}
        onChange={setGranter}
        blocked={blocked}
        types={['mortal']}
      />
      <NodePicker
        label='Who is pardoned'
        value={pardoned}
        onChange={setPardoned}
        blocked={blocked}
        types={['mortal']}
      />
    </ForgeCard>
  )
}

function OutlawCard({
  row,
  blocked,
}: {
  row: OutlawView
  blocked: string | null
}) {
  const action = useRow(
    'outlaw:edit',
    'outlaw:delete',
    { mortal_id: row.mortal?.id ?? 0 },
    blocked
  )
  return (
    <Held
      icon={OUTLAW_ICON}
      tone={row.renown >= 50 ? 'gold' : 'danger'}
      title={<Ref node={row.mortal} empty='a lost outlaw' />}
      caption={
        <>
          {'Outlawed by '}
          <Ref node={row.polity} empty='no realm' />
          {` in epoch ${row.declared_epoch}, a bounty of ${row.bounty} from the realm and ${row.private_bounty} put up by others`}
        </>
      }
      removeLabel='Lift the outlawry'
      editTitle='Set the outlaw'
      note='An outlaw has no standing in court; hunters chase the bounty, and those who escape grow in renown among the folk who shelter them.'
      fields={[
        { key: 'bounty', label: 'Realm bounty', kind: 'number', min: 0 },
        {
          key: 'private_bounty',
          label: 'Private bounty',
          kind: 'number',
          min: 0,
        },
        { key: 'renown', label: 'Renown', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Renown' value={row.renown} tone='warning' />
    </Held>
  )
}

function OutlawForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(
    type === 'mortal' ? nodeId : null
  )
  const [realm, setRealm] = useState<number | null>(
    type === 'polity' ? nodeId : null
  )
  const [bounty, setBounty] = useState('30')
  const declaring = useLawAction(
    'outlaw:declare',
    (_: void) => ({
      mortal_id: mortal ?? 0,
      polity_id: realm,
      bounty: clamp(bounty, 100000),
    }),
    'The mortal is outlawed'
  )
  const missing = mortal === null ? 'Choose who is outlawed' : null
  const busy = why(blocked ?? missing, declaring.isPending)
  return (
    <ForgeCard
      icon={OUTLAW_ICON}
      tone='danger'
      title='Declare an outlaw'
      note='Strip a mortal of the law’s protection and set a bounty on them.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => declaring.mutate()}
        >
          <Plus />
          Outlaw them
        </Button>
      }
    >
      <NodePicker
        label='Mortal'
        value={mortal}
        onChange={setMortal}
        blocked={blocked}
        types={['mortal']}
      />
      <NodePicker
        label='Realm that outlaws them'
        value={realm}
        onChange={setRealm}
        blocked={blocked}
        types={['polity']}
      />
      <NumberField
        label='Bounty'
        min={0}
        value={bounty}
        blocked={blocked}
        onChange={setBounty}
      />
    </ForgeCard>
  )
}

const PRISON_FIELDS: Field[] = [
  { key: 'food', label: 'Food', kind: 'number', min: 0, max: SPAN },
  { key: 'crowding', label: 'Crowding', kind: 'number', min: 0, max: SPAN },
  { key: 'cruelty', label: 'Cruelty', kind: 'number', min: 0, max: SPAN },
  {
    key: 'gang_strength',
    label: 'Gang strength',
    kind: 'number',
    min: 0,
    max: SPAN,
  },
]

function PrisonCard({
  structureId,
  row,
  blocked,
}: {
  structureId: number
  row: PrisonView
  blocked: string | null
}) {
  const action = useRow(
    'prison:edit',
    'prison:delete',
    { structure_id: structureId },
    blocked
  )
  return (
    <Held
      icon={PRISON_ICON}
      tone={row.food < 30 || row.crowding >= 100 ? 'danger' : 'warning'}
      title={<Ref node={row.structure} empty='this prison' />}
      caption='Its food follows the town’s stores, its cruelty the penal code and its crowding the prisoners it holds.'
      removeLabel='Draw anew'
      editTitle='Set the prison'
      note='Hunger and crowding wound prisoners, gangs and crowding make escapes likelier.'
      fields={PRISON_FIELDS}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Food', row.food],
          ['Crowding', row.crowding],
          ['Cruelty', row.cruelty],
          ['Gangs', row.gang_strength],
        ]}
      />
    </Held>
  )
}

function PrisonerCard({
  row,
  blocked,
}: {
  row: PrisonerView
  blocked: string | null
}) {
  const action = useRow(
    'prisoner:edit',
    'prisoner:free',
    { mortal_id: row.mortal?.id ?? 0 },
    blocked
  )
  return (
    <Held
      icon={PRISON_ICON}
      tone='warning'
      title={<Ref node={row.mortal} empty='a lost prisoner' />}
      caption={
        <>
          {'Held in '}
          <Ref node={row.prison} empty='a lost prison' />
          {` since epoch ${row.since_epoch}, ${plural(row.term, 'epoch', 'epochs')} left${row.case_id ? `, for case ${row.case_id}` : ''}`}
        </>
      }
      removeLabel='Free'
      editTitle='Set the sentence'
      note='Prisoners rise in the gangs and learn intrigue inside; at release they carry a stigma.'
      fields={[
        {
          key: 'term',
          label: 'Epochs left',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'gang_rank',
          label: 'Rank in the gangs',
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
      <Meter
        label='Rank in the gangs'
        value={row.gang_rank}
        tone='destructive'
      />
    </Held>
  )
}

function PrisonForge({
  data,
  type,
  blocked,
}: {
  data: NodeLawView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const [mortal, setMortal] = useState<number | null>(
    type === 'mortal' ? nodeId : null
  )
  const [prison, setPrison] = useState<string>(
    data.prisons_here[0] ? String(data.prisons_here[0].id) : ''
  )
  const [term, setTerm] = useState('3')
  const jailing = useLawAction(
    'prisoner:jail',
    (_: void) => ({
      mortal_id: mortal ?? 0,
      prison_id: Number(prison),
      term: clamp(term),
    }),
    'The mortal is in prison'
  )
  const conditions = useLawAction(
    'prison:set',
    (_: void) => ({ structure_id: Number(prison), values: {} }),
    'The prison keeps its conditions'
  )
  const choices = Object.fromEntries(
    data.prisons_here.map((row) => [String(row.id), row.name])
  )
  const none =
    data.prisons_here.length === 0 ? 'No prison stands here to use' : null
  const missing = mortal === null ? 'Choose who is imprisoned' : null
  const busy = why(blocked ?? none ?? missing, jailing.isPending)
  const setBusy = why(blocked ?? none, conditions.isPending)
  return (
    <ForgeCard
      icon={PRISON_ICON}
      tone='warning'
      title='Imprison'
      note='Put a mortal in a prison of this town for a number of epochs, or begin keeping a prison’s conditions.'
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => jailing.mutate()}
          >
            <Plus />
            Imprison
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={setBusy !== null}
            disabledReason={setBusy ?? undefined}
            onClick={() => conditions.mutate()}
          >
            <PRISON_ICON />
            Keep its conditions
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Mortal'
        value={mortal}
        onChange={setMortal}
        blocked={blocked}
        types={['mortal']}
      />
      <MindPicker
        label='Prison'
        value={prison}
        table={choices}
        blocked={blocked ?? none}
        onPick={setPrison}
      />
      <NumberField
        label='Epochs'
        min={0}
        max={SPAN}
        value={term}
        blocked={blocked}
        onChange={setTerm}
      />
    </ForgeCard>
  )
}

function AgentCard({
  row,
  blocked,
}: {
  row: AgentMotiveView
  blocked: string | null
}) {
  const editing = useGodAction({
    run: (vars: Edit) =>
      vars.release.length > 0
        ? postAction('military:release', {
            kind: 'spy_agent',
            record_id: row.agent_id,
            columns: vars.release,
          })
        : postAction('military:edit', {
            kind: 'spy_agent',
            record_id: row.agent_id,
            values: vars.values,
            hold: true,
          }),
    success: 'Set so',
  })
  const busy = why(blocked, editing.isPending)
  const spec = MOTIVES[row.motive]
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone}
      title={<Ref node={row.mortal} empty='a nameless agent' />}
      caption={`Agent of network ${row.network_id}, recruited ${spec.label.toLowerCase()}${row.cell_id ? `, in cell ${row.cell_id}` : ', in no cell'}`}
    >
      <Meter label='Loyalty' value={row.loyalty} tone='success' />
      <RecordEditor
        title='Set the agent'
        note='Loyalty follows the motive of recruitment; an agent of little loyalty may cross to the other side.'
        fields={[
          {
            key: 'motive',
            label: 'Motive',
            kind: 'pick',
            table: table(MOTIVES),
          },
          {
            key: 'loyalty',
            label: 'Loyalty',
            kind: 'number',
            min: 0,
            max: SPAN,
          },
          { key: 'cell_id', label: 'Cell (number)', kind: 'number', min: 1 },
        ]}
        locked={[]}
        busy={busy}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(release) => editing.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function CellCard({ row, blocked }: { row: CellView; blocked: string | null }) {
  const action = useRow(
    'spy_cell:edit',
    'spy_cell:delete',
    { cell_id: row.id },
    blocked
  )
  return (
    <Held
      icon={CELL_ICON}
      tone='info'
      title={`Cell ${row.id} of network ${row.network_id}`}
      caption={
        <>
          {'Handled by '}
          <Ref node={row.handler} empty='no handler' />
          {', safe house '}
          <Ref node={row.safe_house} empty='none' />
          {`, ${row.dead_drops} dead drops`}
        </>
      }
      removeLabel='Break up'
      editTitle='Set the cell'
      note='A caught agent exposes only their own cell; a safe house spares them some of it.'
      fields={[
        {
          key: 'handler_entity_id',
          label: 'Handler (id)',
          kind: 'number',
          min: 1,
        },
        {
          key: 'safe_house_entity_id',
          label: 'Safe house (id)',
          kind: 'number',
          min: 1,
        },
        { key: 'dead_drops', label: 'Dead drops', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function CellForge({
  data,
  blocked,
}: {
  data: NodeLawView
  blocked: string | null
}) {
  const [network, setNetwork] = useState<string>(
    data.networks[0] ? String(data.networks[0].id) : ''
  )
  const [handler, setHandler] = useState<number | null>(null)
  const [safe, setSafe] = useState<number | null>(null)
  const [drops, setDrops] = useState('1')
  const adding = useLawAction(
    'spy_cell:add',
    (_: void) => ({
      network_id: Number(network),
      handler_id: handler,
      safe_house_id: safe,
      dead_drops: clamp(drops),
    }),
    'The cell is formed'
  )
  const choices = Object.fromEntries(
    data.networks.map((row) => [
      String(row.id),
      `${row.owner?.name ?? 'Someone'} in ${row.target?.name ?? 'somewhere'}`,
    ])
  )
  const none = data.networks.length === 0 ? 'No spy network works here' : null
  const busy = why(blocked ?? none, adding.isPending)
  return (
    <ForgeCard
      icon={CELL_ICON}
      tone='info'
      title='Form a spy cell'
      note='Give a network a cell with a handler, a safe house and dead drops.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => adding.mutate()}
        >
          <Plus />
          Form the cell
        </Button>
      }
    >
      <MindPicker
        label='Network'
        value={network}
        table={choices}
        blocked={blocked ?? none}
        onPick={setNetwork}
      />
      <NodePicker
        label='Handler'
        value={handler}
        onChange={setHandler}
        blocked={blocked}
        types={['mortal']}
      />
      <NodePicker
        label='Safe house'
        value={safe}
        onChange={setSafe}
        blocked={blocked}
        types={['structure', 'household']}
      />
      <NumberField
        label='Dead drops'
        min={0}
        max={SPAN}
        value={drops}
        blocked={blocked}
        onChange={setDrops}
      />
    </ForgeCard>
  )
}

function HuntCard({
  row,
  blocked,
}: {
  row: MoleHuntView
  blocked: string | null
}) {
  const action = useRemove('mole_hunt:delete', { hunt_id: row.id }, blocked)
  const spec = HUNT_OUTCOMES[row.outcome]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={
        <>
          <Ref node={row.spymaster} empty='a lost spymaster' />
          {' of '}
          <Ref node={row.polity} empty='a lost realm' />
          {' accused '}
          <Ref node={row.suspect} empty='no one' />
          {` in epoch ${row.epoch}; ${row.mole ? 'a true mole' : 'innocent'}`}
        </>
      }
      removeLabel='Strike from the record'
      editTitle=''
      note=''
      fields={[]}
      locked={[]}
      blocked={action.busy}
      onEdit={null}
      onRemove={action.onRemove}
    />
  )
}

function DefectionCard({
  row,
  blocked,
}: {
  row: DefectionView
  blocked: string | null
}) {
  const action = useRow(
    'defection:edit',
    'defection:delete',
    { defection_id: row.id },
    blocked
  )
  const spec = PROTECTED[row.protected ? 'true' : 'false']
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={<Ref node={row.defector} empty='a lost defector' />}
      caption={
        <>
          {'Crossed from '}
          <Ref node={row.from_side} empty='nowhere' />
          {' to '}
          <Ref node={row.to_side} empty='nowhere' />
          {` in epoch ${row.epoch} with ${plural(row.secrets, 'secret', 'secrets')}; ${spec.label.toLowerCase()}`}
        </>
      }
      removeLabel='Strike from the record'
      editTitle='Set the defection'
      note='An unprotected defector may be killed by the realm they left.'
      fields={[
        { key: 'secrets', label: 'Secrets carried', kind: 'number', min: 0 },
        {
          key: 'protected',
          label: 'Protected',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function KillingCard({
  row,
  blocked,
}: {
  row: KillingView
  blocked: string | null
}) {
  const action = useRow(
    'killing:edit',
    'killing:delete',
    { killing_id: row.id },
    blocked
  )
  const spec = KILL_METHODS[row.method]
  const seen = SEEN[row.recognised ? 'true' : 'false']
  return (
    <Held
      icon={spec.icon}
      tone={row.recognised ? 'danger' : 'muted'}
      title={
        <>
          <Ref node={row.victim} empty='a lost victim' />
          {` · ${spec.label.toLowerCase()}`}
        </>
      }
      caption={
        <>
          {'By '}
          <Ref node={row.killer} empty='an unknown hand' />
          {', examined by '}
          <Ref node={row.examiner} empty='no healer' />
          {` in epoch ${row.epoch}; ${seen.label.toLowerCase()}`}
        </>
      }
      removeLabel='Strike from the record'
      editTitle='Set the killing'
      note='Whether a death is seen as murder decides if a feud, a case or a war follows.'
      fields={[
        {
          key: 'method',
          label: 'Method',
          kind: 'pick',
          table: table(KILL_METHODS),
        },
        {
          key: 'recognised',
          label: 'Seen as murder',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function ShadowForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(
    type === 'mortal' ? nodeId : null
  )
  const [side, setSide] = useState<number | null>(null)
  const [method, setMethod] = useState('poison')
  const hunting = useLawAction(
    'mole_hunt:order',
    (_: void) => ({ polity_id: nodeId }),
    'The spymaster hunts'
  )
  const defecting = useLawAction(
    'defection:make',
    (_: void) => ({
      mortal_id: mortal ?? 0,
      from_id: null,
      to_id: side ?? 0,
      protected: true,
    }),
    'The mortal has crossed over'
  )
  const killing = useLawAction(
    'killing:add',
    (_: void) => ({
      victim_id: mortal ?? 0,
      killer_id: side,
      method: method as KillingView['method'],
      recognised: true,
    }),
    'The killing is recorded'
  )
  const realm = type === 'polity' ? null : 'Only a realm’s spymaster hunts'
  const huntBusy = why(blocked ?? realm, hunting.isPending)
  const missing =
    mortal === null ? 'Choose a mortal' : side === null ? 'Choose a side' : null
  const busy = why(blocked ?? missing, defecting.isPending, killing.isPending)
  return (
    <ForgeCard
      icon={Eye}
      tone='danger'
      title='Work in the shadows'
      note='Order a mole hunt, have a mortal defect to another side with what they know, or record how a killing was done.'
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={huntBusy !== null}
            disabledReason={huntBusy ?? undefined}
            onClick={() => hunting.mutate()}
          >
            <Search />
            Hunt for moles
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => defecting.mutate()}
          >
            <Plus />
            Defect to that side
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => killing.mutate()}
          >
            <Plus />
            Record a killing by them
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Mortal'
        value={mortal}
        onChange={setMortal}
        blocked={blocked}
        types={['mortal']}
      />
      <NodePicker
        label='Side or killer'
        value={side}
        onChange={setSide}
        blocked={blocked}
      />
      <MindPicker
        label='Method'
        value={method}
        table={table(KILL_METHODS)}
        blocked={blocked}
        onPick={setMethod}
      />
    </ForgeCard>
  )
}

function LawBody({
  data,
  type,
  blocked,
}: {
  data: NodeLawView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const holder = type !== null && HOLDER_TYPES.includes(type)
  const holderReason = holder
    ? null
    : 'Only a realm, cult or town keeps a legal system'
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Precedents'
          value={data.precedents.length}
          icon={PRECEDENT_ICON}
          tone='verdigris'
        />
        <KpiTile
          label='Prisoners'
          value={data.prisoners.length}
          icon={PRISON_ICON}
          tone='warning'
        />
        <KpiTile
          label='Outlaws'
          value={data.outlaws.length}
          icon={OUTLAW_ICON}
          tone='danger'
        />
        <KpiTile
          label='Agents'
          value={data.agents.length}
          icon={CELL_ICON}
          tone='info'
        />
      </div>
      {data.system ? (
        <SystemCard holderId={nodeId} data={data} blocked={blocked} />
      ) : (
        <Chip icon={LAW_DEPTH_ICON}>
          {holder ? 'No legal system is set yet' : holderReason}
        </Chip>
      )}
      <SystemForge holderId={nodeId} blocked={blocked ?? holderReason} />
      <Listed
        title='Case law'
        items={data.precedents}
        empty='No ruling binds these courts.'
        noun={['precedent', 'precedents']}
        itemKey={(row) => row.id}
      >
        {(row) => <PrecedentCard row={row} blocked={blocked} />}
      </Listed>
      <PrecedentForge holderId={nodeId} blocked={blocked ?? holderReason} />
      <Listed
        title='Oracle trials'
        items={data.oracle_cases}
        empty='No case waits on a god’s answer here.'
        noun={['case', 'cases']}
        itemKey={(row) => row.case_id}
      >
        {(row) => <OracleCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Appeals'
        items={data.appeals}
        empty='No conviction is carried higher here.'
        noun={['appeal', 'appeals']}
        itemKey={(row) => row.case_id}
      >
        {(row) => <AppealCard row={row} blocked={blocked} />}
      </Listed>
      <AppealForge blocked={blocked} />
      <Listed
        title='Registry'
        items={data.registries}
        empty='No title or contract is registered here.'
        noun={['deed', 'deeds']}
        itemKey={(row) => row.id}
      >
        {(row) => <RegistryCard row={row} blocked={blocked} />}
      </Listed>
      <RegistryForge holderId={nodeId} blocked={blocked ?? holderReason} />
      <Listed
        title='Claims to courts'
        items={data.jurisdictions}
        empty='No one claims courts of their own here.'
        noun={['claim', 'claims']}
        itemKey={(row) => `${row.holder?.id}-${row.claimant?.id}-${row.claim}`}
      >
        {(row) => <ClaimCard row={row} blocked={blocked} />}
      </Listed>
      <ClaimForge
        holderId={nodeId}
        blocked={
          blocked ?? (type === 'polity' ? null : 'Only a realm grants courts')
        }
      />
      <Listed
        title='Pardons and amnesties'
        items={data.pardons}
        empty='No pardon is recorded here.'
        noun={['pardon', 'pardons']}
        itemKey={(row) => row.id}
      >
        {(row) => <PardonCard row={row} blocked={blocked} />}
      </Listed>
      <MercyForge nodeId={nodeId} type={type} blocked={blocked} />
      <Listed
        title='Outlaws'
        items={data.outlaws}
        empty='No outlaw is named here.'
        noun={['outlaw', 'outlaws']}
        itemKey={(row) => row.mortal?.id ?? 0}
      >
        {(row) => <OutlawCard row={row} blocked={blocked} />}
      </Listed>
      <OutlawForge nodeId={nodeId} type={type} blocked={blocked} />
      {data.prison ? (
        <PrisonCard structureId={nodeId} row={data.prison} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          Food, crowding, cruelty and gangs belong to prisons.
        </Muted>
      )}
      <Listed
        title='Prisoners'
        items={data.prisoners}
        empty='No one is held in prison here.'
        noun={['prisoner', 'prisoners']}
        itemKey={(row) => row.mortal?.id ?? 0}
      >
        {(row) => <PrisonerCard row={row} blocked={blocked} />}
      </Listed>
      <PrisonForge data={data} type={type} blocked={blocked} />
      <NetworkGraph data={data} />
      <Listed
        title='Agents and their motives'
        items={data.agents}
        empty='No agent spies here.'
        noun={['agent', 'agents']}
        itemKey={(row) => row.agent_id}
      >
        {(row) => <AgentCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Spy cells'
        items={data.cells}
        empty='No network here is sorted into cells.'
        noun={['cell', 'cells']}
        itemKey={(row) => row.id}
      >
        {(row) => <CellCard row={row} blocked={blocked} />}
      </Listed>
      <CellForge data={data} blocked={blocked} />
      <Listed
        title='Mole hunts'
        items={data.hunts}
        empty='No hunt for moles is recorded here.'
        noun={['hunt', 'hunts']}
        itemKey={(row) => row.id}
      >
        {(row) => <HuntCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Defections'
        items={data.defections}
        empty='No one has crossed sides here.'
        noun={['defection', 'defections']}
        itemKey={(row) => row.id}
      >
        {(row) => <DefectionCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Killings'
        items={data.killings}
        empty='No killing is recorded here.'
        noun={['killing', 'killings']}
        itemKey={(row) => row.id}
      >
        {(row) => <KillingCard row={row} blocked={blocked} />}
      </Listed>
      <ShadowForge nodeId={nodeId} type={type} blocked={blocked} />
    </div>
  )
}

export function LawDepthSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeLaw(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-law-depth'
      title='Courts, prisons and shadows'
      description='The legal system and its case law, appeals and oracle trials; the registry of titles and contracts; claims to courts; pardons, outlaws and prisons; spy agents and their motives, cells, mole hunts, defections and the killings done in secret.'
      icon={LAW_DEPTH_ICON}
      tone='gold'
    >
      <div
        data-surface='LawDepthSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the courts' />
        ) : query.isError ? (
          <EmptyState
            icon={LAW_DEPTH_ICON}
            size='inline'
            title='The courts could not be read'
            description={query.error.message}
          />
        ) : (
          <LawBody data={query.data} type={type} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
