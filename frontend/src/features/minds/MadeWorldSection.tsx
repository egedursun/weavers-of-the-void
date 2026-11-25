import { useState } from 'react'
import {
  BadgeCheck,
  Boxes,
  Building2,
  Bug,
  Database,
  Eye,
  Factory,
  FileKey,
  Flame,
  Lock,
  OctagonX,
  Pickaxe,
  Plus,
  Sprout,
  Trash2,
  Users,
} from 'lucide-react'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { ACCOUNT_KINDS } from '@/features/collective/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MATERIAL_LABEL } from '@/features/entity/economy/labels'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import {
  ChoiceField,
  NumberField,
  ToggleField,
} from '@/features/wars/military/parts'
import {
  type DataStoreView,
  type MadeRealmView,
  type MadeWorldNodeView,
  type ReplicatorLineView,
  useMadeAction,
  useNodeMadeWorld,
  useProfileEdit,
  useRowDelete,
  useRowEdit,
} from './api'
import {
  ATTRIBUTIONS,
  AUTHENTICITIES,
  COMMODITIES,
  COMPANY_CHARTERS,
  DATA_CONTENTS,
  HOLDING_KINDS,
  INTRUSION_AIMS,
  INTRUSION_APPROACHES,
  INTRUSION_OUTCOMES,
  INTRUSION_TARGETS,
  MADE_MIND_STANCES,
  MADE_WORLD_ICON,
  MIND_ORIGINS,
  MIND_SEATS,
  MIND_UPKEEPS,
  REALM_AWARENESS,
  REALM_ENTRIES,
  REALM_PURPOSES,
  RELIC_STANCES,
  RELIC_STATES,
  RELIC_USES,
  REPLICATOR_OUTPUTS,
  REPLICATOR_SCALES,
  REPLICATOR_STAGES,
  SURVEILLANCE_FOCUSES,
} from './labels'

type View = MadeWorldNodeView
type Blocked = { blocked: string | null }
const SHOWN = 6
const YES_NO = { true: 'Yes', false: 'No' }
const HELD =
  'Values you set are held against the engine until you release them.'
const MATERIALS = Object.fromEntries(
  Object.entries(MATERIAL_LABEL).map(([key, label]) => [
    key,
    { label, icon: Boxes, tone: 'muted' as const },
  ])
)

const INTRUSION_FIELDS: readonly Field[] = [
  {
    key: 'target',
    label: 'What was broken into',
    kind: 'pick',
    table: table(INTRUSION_TARGETS),
  },
  {
    key: 'approach',
    label: 'Approach',
    kind: 'pick',
    table: table(INTRUSION_APPROACHES),
  },
  { key: 'aim', label: 'Aim', kind: 'pick', table: table(INTRUSION_AIMS) },
  { key: 'stealth', label: 'Stealth', kind: 'number', min: 0, max: 100 },
  { key: 'detection', label: 'Detection', kind: 'number', min: 0, max: 100 },
  {
    key: 'attribution',
    label: 'Who was named',
    kind: 'pick',
    table: table(ATTRIBUTIONS),
  },
  { key: 'blamed_node_id', label: 'Blamed', kind: 'node', types: [] },
  {
    key: 'outcome',
    label: 'Outcome',
    kind: 'pick',
    table: table(INTRUSION_OUTCOMES),
  },
]
const STORE_FIELDS: readonly Field[] = [
  {
    key: 'holder_node_id',
    label: 'Keeper of the store',
    kind: 'node',
    types: [],
  },
  {
    key: 'owner_node_id',
    label: 'Owner of the store',
    kind: 'node',
    types: [],
  },
  { key: 'security', label: 'Security', kind: 'number', min: 0, max: 100 },
]
const SURVEILLANCE_FIELDS: readonly Field[] = [
  {
    key: 'capacity',
    label: 'Capacity of the watch',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'reach_pct', label: 'Reach (%)', kind: 'number', min: 0, max: 100 },
  {
    key: 'focus',
    label: 'What it looks for',
    kind: 'pick',
    table: table(SURVEILLANCE_FOCUSES),
  },
]
const TRUST_FIELDS: readonly Field[] = [
  {
    key: 'information_trust',
    label: 'Trust in records',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'shared_account_pct',
    label: 'Records held genuine (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
]
const COMPANY_FIELDS: readonly Field[] = [
  {
    key: 'charter',
    label: 'Charter',
    kind: 'pick',
    table: table(COMPANY_CHARTERS),
  },
  {
    key: 'headquarters_entity_id',
    label: 'Headquarters',
    kind: 'node',
    types: ['settlement', 'structure'],
  },
]
const PRESENCE_FIELDS: readonly Field[] = [
  { key: 'licensed', label: 'Licensed there', kind: 'pick', table: YES_NO },
  { key: 'influence', label: 'Influence', kind: 'number', min: 0, max: 100 },
]
const LINE_FIELDS: readonly Field[] = [
  {
    key: 'scale',
    label: 'Scale',
    kind: 'pick',
    table: table(REPLICATOR_SCALES),
  },
  {
    key: 'output',
    label: 'What it makes',
    kind: 'pick',
    table: table(REPLICATOR_OUTPUTS),
  },
  {
    key: 'feedstock',
    label: 'What it feeds on',
    kind: 'pick',
    table: MATERIAL_LABEL,
  },
  { key: 'growth_pct', label: 'Growth (%)', kind: 'number', min: 0, max: 100 },
  {
    key: 'error_pct',
    label: 'Copy error (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'containment',
    label: 'Containment',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'kill_switch', label: 'Kill switch', kind: 'pick', table: YES_NO },
  {
    key: 'stage',
    label: 'Stage',
    kind: 'pick',
    table: table(REPLICATOR_STAGES),
  },
  { key: 'owner_node_id', label: 'Owner of the line', kind: 'node', types: [] },
  { key: 'mind_node_id', label: 'Mind that runs it', kind: 'node', types: [] },
]
const PRESENCE_MASS_FIELDS: readonly Field[] = [
  { key: 'mass', label: 'Mass', kind: 'number', min: 0, max: 1000000 },
  { key: 'growth', label: 'Growth here (%)', kind: 'number', min: 0, max: 100 },
]
const FABRICATION_FIELDS: readonly Field[] = [
  {
    key: 'share_pct',
    label: 'Share fabricated (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'dividend_pct',
    label: 'Dividend paid out (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
]
const SCARCITY_FIELDS: readonly Field[] = [
  { key: 'scarcity', label: 'Scarcity', kind: 'number', min: 0, max: 100 },
]
const PATTERN_FIELDS: readonly Field[] = [
  {
    key: 'commodity',
    label: 'Good it makes',
    kind: 'pick',
    table: table(COMMODITIES),
  },
  {
    key: 'holder_node_id',
    label: 'Holder of the pattern',
    kind: 'node',
    types: [],
  },
  {
    key: 'licence_fee',
    label: 'Licence fee',
    kind: 'number',
    min: 0,
    max: 1000000,
  },
  { key: 'open', label: 'Open to all', kind: 'pick', table: YES_NO },
]
const RELIC_FIELDS: readonly Field[] = [
  {
    key: 'make_knowledge',
    label: 'Knowledge it takes to make',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'repair_knowledge',
    label: 'Knowledge it takes to repair',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'function_state',
    label: 'How it works',
    kind: 'pick',
    table: table(RELIC_STATES),
  },
  {
    key: 'understood_pct',
    label: 'Understood (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'use',
    label: 'How it is used',
    kind: 'pick',
    table: table(RELIC_USES),
  },
  {
    key: 'is_relic',
    label: 'A relic of a lost making',
    kind: 'pick',
    table: YES_NO,
  },
]
const SALVAGE_FIELDS: readonly Field[] = [
  {
    key: 'yield_left',
    label: 'Yield left',
    kind: 'number',
    min: 0,
    max: 1000000,
  },
  {
    key: 'rights_holder_node_id',
    label: 'Holder of the salvage right',
    kind: 'node',
    types: [],
  },
]
const SUBSTRATE_FIELDS: readonly Field[] = [
  {
    key: 'origin',
    label: 'Origin of these minds',
    kind: 'pick',
    table: table(MIND_ORIGINS),
  },
  {
    key: 'share_pct',
    label: 'Share of the people (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
]
const REALM_FIELDS: readonly Field[] = [
  { key: 'host_node_id', label: 'What hosts it', kind: 'node', types: [] },
  {
    key: 'keeper_node_id',
    label: 'Keeper of the realm',
    kind: 'node',
    types: [],
  },
  {
    key: 'realm_purpose',
    label: 'Purpose',
    kind: 'pick',
    table: table(REALM_PURPOSES),
  },
  {
    key: 'time_ratio_pct',
    label: 'Time against the world (%)',
    kind: 'number',
    min: 1,
    max: 10000,
  },
  { key: 'fidelity', label: 'Fidelity', kind: 'number', min: 0, max: 100 },
  { key: 'entry', label: 'Way in', kind: 'pick', table: table(REALM_ENTRIES) },
  {
    key: 'aware_inside',
    label: 'Whether those inside know',
    kind: 'pick',
    table: table(REALM_AWARENESS),
  },
  {
    key: 'upkeep',
    label: 'What keeps its host running',
    kind: 'pick',
    table: table(MIND_UPKEEPS),
  },
  {
    key: 'frozen_until_epoch',
    label: 'Still until epoch',
    kind: 'number',
    min: 0,
    max: 100000,
  },
  { key: 'sealed', label: 'Sealed', kind: 'pick', table: YES_NO },
]
const DOCTRINE_FIELDS: readonly Field[] = [
  {
    key: 'made_mind_stance',
    label: 'Stance on made minds',
    kind: 'pick',
    table: table(MADE_MIND_STANCES),
  },
  {
    key: 'copy_stance',
    label: 'Stance on copies',
    kind: 'pick',
    table: table(MADE_MIND_STANCES),
  },
  {
    key: 'augment_stance',
    label: 'Stance on augments',
    kind: 'pick',
    table: table(MADE_MIND_STANCES),
  },
  {
    key: 'made_afterlife_stance',
    label: 'Stance on an afterlife for made minds',
    kind: 'pick',
    table: table(MADE_MIND_STANCES),
  },
  {
    key: 'relic_stance',
    label: 'Stance on relics',
    kind: 'pick',
    table: table(RELIC_STANCES),
  },
]

function Rows<T>({
  items,
  render,
  empty,
}: {
  items: readonly T[]
  render: (item: T) => React.ReactNode
  empty: string
}) {
  const page = useShowMore(items, SHOWN, SHOWN * 2)
  if (!items.length) return <Muted variant='caption'>{empty}</Muted>
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul className='flex min-w-0 flex-col gap-2'>
        {page.visible.map(render)}
      </ul>
      <ShowMore state={page} />
    </div>
  )
}

function RowEditor({
  title,
  tableName,
  rowKey,
  fields,
  locked,
  blocked,
}: {
  title: string
  tableName: string
  rowKey: Record<string, number | string>
  fields: readonly Field[]
  locked: readonly string[]
} & Blocked) {
  const editing = useRowEdit(tableName, rowKey)
  const removing = useRowDelete(tableName, rowKey)
  return (
    <>
      <RecordEditor
        act={editing}
        title={title}
        note={HELD}
        fields={fields}
        locked={locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Strike it from the record'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </>
  )
}

function ProfileEditor({
  title,
  nodeId,
  tableName,
  fields,
  locked,
  blocked,
}: {
  title: string
  nodeId: number
  tableName: string
  fields: readonly Field[]
  locked: readonly string[]
} & Blocked) {
  const editing = useProfileEdit(nodeId, tableName)
  return (
    <RecordEditor
      act={editing}
      title={title}
      note={HELD}
      fields={fields}
      locked={locked}
      busy={why(blocked, editing.isPending)}
      onSave={(values) => editing.mutate({ values, release: [] })}
      onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
    />
  )
}

function Intrusions({ view, blocked }: { view: View } & Blocked) {
  const [target, setTarget] = useState<string>('network')
  const [targetId, setTargetId] = useState<number | null>(null)
  const [approach, setApproach] = useState<string>('technical')
  const [aim, setAim] = useState<string>('read')
  const [blamed, setBlamed] = useState<number | null>(null)
  const making = useMadeAction(
    'intrusion:make',
    (_: void) => ({
      actor_id: view.node.id,
      target: target as View['intrusions'][number]['target'],
      target_id: targetId,
      approach: approach as View['intrusions'][number]['approach'],
      aim: aim as View['intrusions'][number]['aim'],
      blamed_id: blamed,
    }),
    'The intrusion is made'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Rows
        items={view.intrusions}
        empty='No intrusion touches it.'
        render={(row) => (
          <RecordRow
            key={row.id}
            icon={INTRUSION_AIMS[row.aim].icon}
            tone={INTRUSION_OUTCOMES[row.outcome].tone}
            title={`${INTRUSION_AIMS[row.aim].label}: ${INTRUSION_TARGETS[row.target].label.toLowerCase()}, epoch ${row.epoch}`}
            caption={`${INTRUSION_OUTCOMES[row.outcome].label}, ${INTRUSION_APPROACHES[row.approach].label.toLowerCase()}, stealth ${row.stealth}, detection ${row.detection}, ${ATTRIBUTIONS[row.attribution].label.toLowerCase()}`}
          >
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Ref node={row.actor} empty='no known actor' />
              <Ref node={row.target_node} empty='no target left' />
              <Ref node={row.blamed} empty='no one blamed' />
            </div>
            <RowEditor
              title='Set this intrusion'
              tableName='intrusions'
              rowKey={{ id: row.id }}
              fields={INTRUSION_FIELDS}
              locked={row.locked}
              blocked={blocked}
            />
          </RecordRow>
        )}
      />
      <ForgeCard
        icon={Bug}
        tone='danger'
        title={`Have ${view.node.name} break into something`}
        note='Its skill and spies are set against the target’s security; it may be found, named, or blamed on another.'
        columns={3}
        action={
          <StepButton
            act={making}
            icon={Bug}
            label='Break in'
            busy={why(
              blocked ?? (targetId === null ? 'Pick the target' : null),
              making.isPending
            )}
            onClick={() => making.mutate()}
          />
        }
      >
        <ChoiceField
          label='What it breaks into'
          value={target}
          table={INTRUSION_TARGETS}
          blocked={blocked}
          onPick={setTarget}
        />
        <ThingPicker
          label='Target'
          value={targetId}
          onChange={setTargetId}
          blocked={blocked}
        />
        <ChoiceField
          label='Approach'
          value={approach}
          table={INTRUSION_APPROACHES}
          blocked={blocked}
          onPick={setApproach}
        />
        <ChoiceField
          label='Aim'
          value={aim}
          table={INTRUSION_AIMS}
          blocked={blocked}
          onPick={setAim}
        />
        <ThingPicker
          label='Blame it on'
          value={blamed}
          onChange={setBlamed}
          blocked={blocked}
        />
      </ForgeCard>
    </div>
  )
}

function Store({ store, blocked }: { store: DataStoreView } & Blocked) {
  const [content, setContent] = useState<string>('secret')
  const [subject, setSubject] = useState<number | null>(null)
  const putting = useMadeAction(
    'data_store:put',
    (_: void) => ({
      store_id: store.id,
      content: content as DataStoreView['contents'][number]['content'],
      subject_id: subject,
    }),
    'The store holds it now'
  )
  return (
    <RecordRow
      icon={Database}
      tone='info'
      title={`Store of records kept by ${store.holder?.name ?? 'no one'}`}
      caption={`Security ${store.security}`}
      aside={<Ref node={store.owner} empty='owned by no one' />}
    >
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={store.contents} as='li'>
          {(item) => (
            <StoreContent key={item.id} item={item} blocked={blocked} />
          )}
        </Paged>
      </ul>
      <ForgeCard
        icon={Plus}
        tone='info'
        title='Put a record into it'
        note='What a store holds can be read, altered or let out by intrusion.'
        columns={2}
        action={
          <StepButton
            act={putting}
            icon={Plus}
            label='Put it in'
            busy={why(blocked, putting.isPending)}
            onClick={() => putting.mutate()}
          />
        }
      >
        <ChoiceField
          label='What it holds'
          value={content}
          table={DATA_CONTENTS}
          blocked={blocked}
          onPick={setContent}
        />
        <ThingPicker
          label='About whom or what'
          value={subject}
          onChange={setSubject}
          blocked={blocked}
        />
      </ForgeCard>
      <RowEditor
        title='Set this store'
        tableName='data_stores'
        rowKey={{ id: store.id }}
        fields={STORE_FIELDS}
        locked={store.locked}
        blocked={blocked}
      />
    </RecordRow>
  )
}

function StoreContent({
  item,
  blocked,
}: { item: DataStoreView['contents'][number] } & Blocked) {
  const taking = useMadeAction(
    'data_store:take',
    (_: void) => ({ content_id: item.id }),
    'The store no longer holds it'
  )
  return (
    <RecordRow
      icon={DATA_CONTENTS[item.content].icon}
      tone={DATA_CONTENTS[item.content].tone}
      title={`${DATA_CONTENTS[item.content].label}${item.subject ? ` of ${item.subject.name}` : ''}`}
      caption={`Kept since epoch ${item.epoch}${item.reference !== null ? `, with a reference attached` : ''}`}
      aside={
        <StepButton
          act={taking}
          icon={Trash2}
          label='Take it out'
          busy={why(blocked, taking.isPending)}
          onClick={() => taking.mutate()}
        />
      }
    />
  )
}

function Stores({ view, blocked }: { view: View } & Blocked) {
  const [security, setSecurity] = useState('30')
  const opening = useMadeAction(
    'data_store:open',
    (_: void) => ({
      holder_id: view.node.id,
      owner_id: view.node.id,
      security: Number(security) || 0,
    }),
    'A store of records is opened'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Rows
        items={view.stores}
        empty='It keeps no store of records.'
        render={(store) => (
          <Store key={store.id} store={store} blocked={blocked} />
        )}
      />
      <ForgeCard
        icon={Database}
        tone='info'
        title={`Open a store of records for ${view.node.name}`}
        note='A store holds secrets, saved minds, knowledge, accounts, ledgers, identities and orders.'
        columns={2}
        action={
          <StepButton
            act={opening}
            icon={Database}
            label='Open it'
            busy={why(blocked, opening.isPending)}
            onClick={() => opening.mutate()}
          />
        }
      >
        <NumberField
          label='Security'
          value={security}
          min={0}
          max={100}
          onChange={setSecurity}
        />
      </ForgeCard>
    </div>
  )
}

function RecordMark({
  record,
  blocked,
}: { record: View['records'][number] } & Blocked) {
  const [authenticity, setAuthenticity] = useState<string>(record.authenticity)
  const marking = useMadeAction(
    'record:authenticity',
    (_: void) => ({
      account_id: record.id,
      authenticity: authenticity as View['records'][number]['authenticity'],
    }),
    'The record is marked so'
  )
  const kind = ACCOUNT_KINDS[record.kind]
  return (
    <RecordRow
      icon={AUTHENTICITIES[record.authenticity].icon}
      tone={AUTHENTICITIES[record.authenticity].tone}
      title={`${kind.label}${record.subject ? ` of ${record.subject.name}` : ''}, epoch ${record.epoch}`}
      caption={`${AUTHENTICITIES[record.authenticity].label}, credence ${record.credence}`}
      aside={<Ref node={record.author} empty='no known author' />}
    >
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <ChoiceField
          label='How genuine it is'
          value={authenticity}
          table={AUTHENTICITIES}
          blocked={blocked}
          onPick={setAuthenticity}
        />
        <StepButton
          act={marking}
          icon={BadgeCheck}
          label='Mark it so'
          busy={why(blocked, marking.isPending)}
          onClick={() => marking.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Company({ view, blocked }: { view: View } & Blocked) {
  const [holding, setHolding] = useState<number | null>(null)
  const [kind, setKind] = useState<string>('structure')
  const holdingIt = useMadeAction(
    'company:hold',
    (_: void) => ({
      company_id: view.node.id,
      holding_id: holding ?? -1,
      kind: kind as NonNullable<View['company']>['holdings'][number]['kind'],
    }),
    'The company holds it now'
  )
  const company = view.company
  if (!company)
    return view.enclave ? (
      <RecordRow
        icon={Building2}
        tone='danger'
        title={`An enclave of ${view.enclave.company?.name ?? 'a company'}`}
        caption={`Since epoch ${view.enclave.since_epoch}`}
      >
        <RowEditor
          title='Set this enclave'
          tableName='enclaves'
          rowKey={{ settlement_entity_id: view.node.id }}
          fields={[
            {
              key: 'company_entity_id',
              label: 'Company that holds it',
              kind: 'node',
              types: ['faction'],
            },
          ]}
          locked={view.enclave.locked}
          blocked={blocked}
        />
      </RecordRow>
    ) : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Chip icon={COMPANY_CHARTERS[company.charter].icon}>
          {COMPANY_CHARTERS[company.charter].label}
        </Chip>
        <Ref node={company.headquarters} empty='no headquarters' />
      </div>
      <ProfileEditor
        title='Set this company'
        nodeId={view.node.id}
        tableName='company_profiles'
        fields={COMPANY_FIELDS}
        locked={company.locked}
        blocked={blocked}
      />
      <Rows
        items={company.holdings}
        empty='It holds nothing yet.'
        render={(row) => (
          <RecordRow
            key={row.id}
            icon={HOLDING_KINDS[row.kind].icon}
            tone={HOLDING_KINDS[row.kind].tone}
            title={`${HOLDING_KINDS[row.kind].label}: ${row.holding?.name ?? 'gone'}`}
          >
            <RowEditor
              title='Set this holding'
              tableName='company_holdings'
              rowKey={{ id: row.id }}
              fields={[
                {
                  key: 'kind',
                  label: 'What it holds',
                  kind: 'pick',
                  table: table(HOLDING_KINDS),
                },
              ]}
              locked={row.locked}
              blocked={blocked}
            />
          </RecordRow>
        )}
      />
      <Rows
        items={company.presences}
        empty='It works in no realm.'
        render={(row) => (
          <RecordRow
            key={`${row.company?.id}-${row.polity?.id}`}
            icon={Users}
            tone='gold'
            title={`Influence ${row.influence} in ${row.polity?.name ?? 'a lost realm'}`}
            caption={row.licensed ? 'Licensed' : 'Unlicensed'}
          >
            <RowEditor
              title='Set this presence'
              tableName='company_presences'
              rowKey={{
                company_entity_id: row.company?.id ?? -1,
                polity_entity_id: row.polity?.id ?? -1,
              }}
              fields={PRESENCE_FIELDS}
              locked={row.locked}
              blocked={blocked}
            />
          </RecordRow>
        )}
      />
      <Rows
        items={company.enclaves}
        empty='It holds no enclave.'
        render={(row) => (
          <RecordRow
            key={row.settlement?.id}
            icon={Building2}
            tone='danger'
            title={`Enclave: ${row.settlement?.name ?? 'a lost town'}`}
            caption={`Since epoch ${row.since_epoch}`}
          />
        )}
      />
      <ForgeCard
        icon={Building2}
        tone='gold'
        title='Give it a holding'
        note='Holdings give a company influence in the realm they stand in; enough influence takes enclaves and may capture the realm’s rule.'
        columns={2}
        action={
          <StepButton
            act={holdingIt}
            icon={Plus}
            label='Give it'
            busy={why(
              blocked ?? (holding === null ? 'Pick the holding' : null),
              holdingIt.isPending
            )}
            onClick={() => holdingIt.mutate()}
          />
        }
      >
        <ThingPicker
          label='Holding'
          value={holding}
          onChange={setHolding}
          blocked={blocked}
        />
        <ChoiceField
          label='What it holds'
          value={kind}
          table={HOLDING_KINDS}
          blocked={blocked}
          onPick={setKind}
        />
      </ForgeCard>
    </div>
  )
}

function Line({ line, blocked }: { line: ReplicatorLineView } & Blocked) {
  const stage = REPLICATOR_STAGES[line.stage]
  const [place, setPlace] = useState<number | null>(null)
  const [mass, setMass] = useState('10')
  const stopping = useMadeAction(
    'replicator:stop',
    (_: void) => ({ line_id: line.id }),
    'The line is stopped'
  )
  const seeding = useMadeAction(
    'replicator:seed',
    (_: void) => ({
      line_id: line.id,
      place_id: place ?? -1,
      mass: Math.max(1, Number(mass) || 1),
    }),
    'The line takes hold there'
  )
  return (
    <RecordRow
      icon={stage.icon}
      tone={stage.tone}
      title={`${line.name}: ${REPLICATOR_OUTPUTS[line.output].label.toLowerCase()}, ${stage.label.toLowerCase()}`}
      caption={`${REPLICATOR_SCALES[line.scale].label}, feeds on ${MATERIAL_LABEL[line.feedstock].toLowerCase()}, growth ${line.growth_pct}%, copy error ${line.error_pct}%, containment ${line.containment}${line.kill_switch ? ', kill switch' : ''}, since epoch ${line.founded_epoch}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={line.owner} empty='owned by no one' />
        <Ref node={line.maker} empty='maker unknown' />
        <Ref node={line.mind} empty='no mind runs it' />
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={line.presences} as='li'>
          {(presence) => (
            <Presence key={presence.id} presence={presence} blocked={blocked} />
          )}
        </Paged>
      </ul>
      <ForgeCard
        icon={Sprout}
        tone='warning'
        title='Seed it in another place'
        note='A loose line spreads from there on its own.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              act={seeding}
              icon={Sprout}
              label='Seed it'
              busy={why(
                blocked ?? (place === null ? 'Pick the place' : null),
                seeding.isPending
              )}
              onClick={() => seeding.mutate()}
            />
            <StepButton
              act={stopping}
              icon={OctagonX}
              label='Stop it everywhere'
              busy={why(
                blocked ??
                  (line.stage === 'stopped' ? 'It is stopped already' : null),
                stopping.isPending
              )}
              onClick={() => stopping.mutate()}
            />
          </div>
        }
      >
        <ThingPicker
          label='Place'
          value={place}
          onChange={setPlace}
          blocked={blocked}
          types={['region']}
        />
        <NumberField label='Mass' value={mass} min={1} onChange={setMass} />
      </ForgeCard>
      <RowEditor
        title='Set this line'
        tableName='replicator_lines'
        rowKey={{ id: line.id }}
        fields={LINE_FIELDS}
        locked={line.locked}
        blocked={blocked}
      />
    </RecordRow>
  )
}

function Presence({
  presence,
  blocked,
}: { presence: View['presences'][number] } & Blocked) {
  const lifting = useMadeAction(
    'replicator:lift',
    (_: void) => ({ presence_id: presence.id }),
    'The line is gone from there'
  )
  const editing = useRowEdit('replicator_presence', { id: presence.id })
  return (
    <RecordRow
      icon={Boxes}
      tone='warning'
      title={`${presence.line_name || 'A line'} in ${presence.place?.name ?? 'a lost place'}`}
      caption={`Mass ${presence.mass}, growth ${presence.growth}%`}
    >
      <RecordEditor
        act={editing}
        title='Set this presence'
        note={HELD}
        fields={PRESENCE_MASS_FIELDS}
        locked={presence.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={lifting}
        icon={Trash2}
        label='Clear it from here'
        busy={why(blocked, lifting.isPending)}
        onClick={() => lifting.mutate()}
      />
    </RecordRow>
  )
}

function Replicators({ view, blocked }: { view: View } & Blocked) {
  const [name, setName] = useState('')
  const [output, setOutput] = useState<string>('goods')
  const [scale, setScale] = useState<string>('machine')
  const [feedstock, setFeedstock] = useState<string>('iron')
  const [containment, setContainment] = useState('80')
  const [killSwitch, setKillSwitch] = useState(true)
  const [place, setPlace] = useState<number | null>(null)
  const founding = useMadeAction(
    'replicator:found',
    (_: void) => ({
      name: name.trim(),
      output: output as ReplicatorLineView['output'],
      scale: scale as ReplicatorLineView['scale'],
      feedstock: feedstock as ReplicatorLineView['feedstock'],
      containment: Number(containment) || 0,
      kill_switch: killSwitch,
      owner_id: view.node.id,
      maker_id: view.node.id,
      place_id: place ?? -1,
    }),
    'A self-making line begins'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Rows
        items={view.lines}
        empty='It owns, made or runs no self-making line.'
        render={(line) => <Line key={line.id} line={line} blocked={blocked} />}
      />
      <Rows
        items={view.presences}
        empty='No self-making line has taken hold here.'
        render={(presence) => (
          <Presence key={presence.id} presence={presence} blocked={blocked} />
        )}
      />
      <ForgeCard
        icon={Boxes}
        tone='warning'
        title={`Start a self-making line owned by ${view.node.name}`}
        note='A line grows on its feedstock and makes what it is set to; copy errors weaken its containment until it spreads or runs away.'
        columns={3}
        action={
          <StepButton
            act={founding}
            icon={Boxes}
            label='Start it'
            busy={why(
              blocked ??
                (name.trim()
                  ? place === null
                    ? 'Pick where it starts'
                    : null
                  : 'Name the line'),
              founding.isPending
            )}
            onClick={() => founding.mutate()}
          />
        }
      >
        <TextField
          label='Name of the line'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <ChoiceField
          label='What it makes'
          value={output}
          table={REPLICATOR_OUTPUTS}
          blocked={blocked}
          onPick={setOutput}
        />
        <ChoiceField
          label='Scale'
          value={scale}
          table={REPLICATOR_SCALES}
          blocked={blocked}
          onPick={setScale}
        />
        <ChoiceField
          label='What it feeds on'
          value={feedstock}
          table={MATERIALS}
          blocked={blocked}
          onPick={setFeedstock}
        />
        <NumberField
          label='Containment'
          value={containment}
          min={0}
          max={100}
          onChange={setContainment}
        />
        <ThingPicker
          label='Where it starts'
          value={place}
          onChange={setPlace}
          blocked={blocked}
          types={['region']}
        />
        <ToggleField
          item={{
            label: 'Give it a kill switch',
            icon: OctagonX,
            tone: 'danger',
          }}
          checked={killSwitch}
          disabled={blocked !== null}
          onChange={setKillSwitch}
        />
      </ForgeCard>
    </div>
  )
}

function Abundance({ view, blocked }: { view: View } & Blocked) {
  const [commodity, setCommodity] = useState<string>('goods')
  const [fee, setFee] = useState('5')
  const [open, setOpen] = useState(false)
  const granting = useMadeAction(
    'pattern:grant',
    (_: void) => ({
      commodity: commodity as View['patterns'][number]['commodity'],
      holder_id: view.node.id,
      fee: Number(fee) || 0,
      open,
    }),
    'The pattern right is set'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {view.fabrication && (
        <>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
            <KpiTile
              label='Goods fabricated'
              value={`${view.fabrication.share_pct}%`}
              icon={Factory}
              tone='gold'
            />
            <KpiTile
              label='Dividend paid out'
              value={`${view.fabrication.dividend_pct}%`}
              icon={Factory}
              tone='success'
            />
            <KpiTile
              label='Reckoned in epoch'
              value={String(view.fabrication.updated_epoch)}
              icon={Factory}
              tone='muted'
            />
          </div>
          <ProfileEditor
            title='Set its fabrication'
            nodeId={view.node.id}
            tableName='fabrication'
            fields={FABRICATION_FIELDS}
            locked={view.fabrication.locked}
            blocked={blocked}
          />
        </>
      )}
      <Rows
        items={view.scarcity}
        empty='No scarcity is reckoned here.'
        render={(row) => (
          <RecordRow
            key={row.commodity}
            icon={COMMODITIES[row.commodity].icon}
            tone={COMMODITIES[row.commodity].tone}
            title={`${COMMODITIES[row.commodity].label}: scarcity ${row.scarcity}`}
            caption={`Reckoned in epoch ${row.updated_epoch}`}
          >
            <RowEditor
              title='Set this scarcity'
              tableName='market_scarcity'
              rowKey={{
                settlement_entity_id: view.node.id,
                commodity: row.commodity,
              }}
              fields={SCARCITY_FIELDS}
              locked={row.locked}
              blocked={blocked}
            />
          </RecordRow>
        )}
      />
      <Rows
        items={view.patterns}
        empty='It holds no pattern.'
        render={(row) => (
          <RecordRow
            key={row.id}
            icon={FileKey}
            tone={row.open ? 'success' : 'gold'}
            title={`Pattern for ${COMMODITIES[row.commodity].label.toLowerCase()}`}
            caption={`${row.open ? 'Open to all' : `Licence fee ${row.licence_fee}`}, since epoch ${row.since_epoch}`}
            aside={<Ref node={row.holder} empty='held by no one' />}
          >
            <RowEditor
              title='Set this pattern'
              tableName='pattern_rights'
              rowKey={{ id: row.id }}
              fields={PATTERN_FIELDS}
              locked={row.locked}
              blocked={blocked}
            />
          </RecordRow>
        )}
      />
      <ForgeCard
        icon={FileKey}
        tone='gold'
        title={`Give ${view.node.name} a pattern`}
        note='The holder of a closed pattern takes a share of the dividend wherever the good is fabricated.'
        columns={3}
        action={
          <StepButton
            act={granting}
            icon={FileKey}
            label='Grant it'
            busy={why(blocked, granting.isPending)}
            onClick={() => granting.mutate()}
          />
        }
      >
        <ChoiceField
          label='Good it makes'
          value={commodity}
          table={COMMODITIES}
          blocked={blocked}
          onPick={setCommodity}
        />
        <NumberField
          label='Licence fee'
          value={fee}
          min={0}
          onChange={setFee}
        />
        <ToggleField
          item={{ label: 'Open to all', icon: FileKey, tone: 'success' }}
          checked={open}
          disabled={blocked !== null}
          onChange={setOpen}
        />
      </ForgeCard>
    </div>
  )
}

function Relics({ view, blocked }: { view: View } & Blocked) {
  const [make, setMake] = useState('5')
  const [repair, setRepair] = useState('4')
  const [holder, setHolder] = useState<number | null>(null)
  const [left, setLeft] = useState('50')
  const marking = useMadeAction(
    'relic:mark',
    (_: void) => ({
      thing_id: view.node.id,
      make_knowledge: Number(make) || 0,
      repair_knowledge: Number(repair) || 0,
    }),
    'The thing is a relic now'
  )
  const opening = useMadeAction(
    'salvage:open',
    (_: void) => ({
      site_id: view.node.id,
      holder_id: holder,
      yield_left: Number(left) || 0,
    }),
    'The site may be salvaged'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      {view.relic && (
        <>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Chip icon={RELIC_STATES[view.relic.function_state].icon}>
              {RELIC_STATES[view.relic.function_state].label}
            </Chip>
            <Chip icon={RELIC_USES[view.relic.use].icon}>
              {RELIC_USES[view.relic.use].label}
            </Chip>
            <Chip icon={Eye}>Understood {view.relic.understood_pct}%</Chip>
            <Chip icon={Lock}>
              Making takes {view.relic.make_knowledge}, repair{' '}
              {view.relic.repair_knowledge}
              {view.relic.is_relic ? ', a relic of a lost making' : ''},
              reckoned in epoch {view.relic.updated_epoch}
            </Chip>
          </div>
          <ProfileEditor
            title='Set this relic'
            nodeId={view.node.id}
            tableName='made_relics'
            fields={RELIC_FIELDS}
            locked={view.relic.locked}
            blocked={blocked}
          />
        </>
      )}
      {view.salvage && (
        <>
          <RecordRow
            icon={Pickaxe}
            tone='gold'
            title={`Salvage left: ${view.salvage.yield_left}`}
            caption={
              view.salvage.last_salvaged_epoch === null
                ? 'Never salvaged'
                : `Last salvaged in epoch ${view.salvage.last_salvaged_epoch}`
            }
            aside={
              <Ref node={view.salvage.rights_holder} empty='open to anyone' />
            }
          />
          <ProfileEditor
            title='Set this salvage site'
            nodeId={view.node.id}
            tableName='salvage_sites'
            fields={SALVAGE_FIELDS}
            locked={view.salvage.locked}
            blocked={blocked}
          />
        </>
      )}
      <ForgeCard
        icon={Flame}
        tone='verdigris'
        title={`Make ${view.node.name} a relic of a lost making`}
        note='A relic wears without anyone who can repair it, is studied until its repair is relearned and may be revered by those who keep it.'
        columns={2}
        action={
          <StepButton
            act={marking}
            icon={Flame}
            label='Make it a relic'
            busy={why(blocked, marking.isPending)}
            onClick={() => marking.mutate()}
          />
        }
      >
        <NumberField
          label='Knowledge it takes to make'
          value={make}
          min={0}
          max={100}
          onChange={setMake}
        />
        <NumberField
          label='Knowledge it takes to repair'
          value={repair}
          min={0}
          max={100}
          onChange={setRepair}
        />
      </ForgeCard>
      <ForgeCard
        icon={Pickaxe}
        tone='gold'
        title={`Open ${view.node.name} to salvage`}
        note='The holder of the salvage right takes from it each epoch until nothing is left.'
        columns={2}
        action={
          <StepButton
            act={opening}
            icon={Pickaxe}
            label='Open it'
            busy={why(blocked, opening.isPending)}
            onClick={() => opening.mutate()}
          />
        }
      >
        <ThingPicker
          label='Holder of the salvage right'
          value={holder}
          onChange={setHolder}
          blocked={blocked}
        />
        <NumberField label='Yield' value={left} min={0} onChange={setLeft} />
      </ForgeCard>
    </div>
  )
}

function Realm({ realm, blocked }: { realm: MadeRealmView } & Blocked) {
  const purpose = REALM_PURPOSES[realm.realm_purpose]
  return (
    <RecordRow
      icon={purpose.icon}
      tone={realm.sealed ? 'danger' : purpose.tone}
      title={`${realm.dimension.name}: ${purpose.label.toLowerCase()}${realm.sealed ? ', sealed' : ''}`}
      caption={`${realm.time_ratio_pct}% of world time, fidelity ${realm.fidelity}, ${REALM_ENTRIES[realm.entry].label.toLowerCase()}, ${REALM_AWARENESS[realm.aware_inside].label.toLowerCase()}, kept by ${MIND_UPKEEPS[realm.upkeep].label.toLowerCase()}, minds inside: ${realm.minds_inside}${realm.frozen_until_epoch ? `, still until epoch ${realm.frozen_until_epoch}` : ''}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={realm.host} empty='no host' />
        <Ref node={realm.keeper} empty='no keeper' />
      </div>
      <RowEditor
        title='Set this realm'
        tableName='made_realm_profiles'
        rowKey={{ dimension_id: realm.dimension.id }}
        fields={REALM_FIELDS}
        locked={realm.locked}
        blocked={blocked}
      />
    </RecordRow>
  )
}

function Realms({ view, blocked }: { view: View } & Blocked) {
  const [name, setName] = useState('')
  const [host, setHost] = useState<number | null>(null)
  const [purpose, setPurpose] = useState<string>('dwelling')
  const [ratio, setRatio] = useState('100')
  const [entry, setEntry] = useState<string>('interface')
  const [aware, setAware] = useState<string>('knows')
  const [upkeep, setUpkeep] = useState<string>('maintenance')
  const making = useMadeAction(
    'realm:make',
    (_: void) => ({
      name: name.trim(),
      keeper_id: view.node.id,
      host_id: host,
      purpose: purpose as MadeRealmView['realm_purpose'],
      time_ratio_pct: Math.max(1, Number(ratio) || 100),
      entry: entry as MadeRealmView['entry'],
      aware: aware as MadeRealmView['aware_inside'],
      upkeep: upkeep as MadeRealmView['upkeep'],
    }),
    'A made realm opens'
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Rows
        items={view.realms}
        empty='It keeps, hosts or is no made realm.'
        render={(realm) => (
          <Realm key={realm.dimension.id} realm={realm} blocked={blocked} />
        )}
      />
      <ForgeCard
        icon={MIND_SEATS.realm.icon}
        tone='verdigris'
        title={`Make a realm kept by ${view.node.name}`}
        note='A made realm runs at its own time and stands still when its host goes down; its minds run there instead of in the world.'
        columns={3}
        action={
          <StepButton
            act={making}
            icon={MIND_SEATS.realm.icon}
            label='Make it'
            busy={why(
              blocked ?? (name.trim() ? null : 'Name the realm'),
              making.isPending
            )}
            onClick={() => making.mutate()}
          />
        }
      >
        <TextField
          label='Name of the realm'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <ThingPicker
          label='What hosts it'
          value={host}
          onChange={setHost}
          blocked={blocked}
        />
        <ChoiceField
          label='Purpose'
          value={purpose}
          table={REALM_PURPOSES}
          blocked={blocked}
          onPick={setPurpose}
        />
        <NumberField
          label='Time against the world (%)'
          value={ratio}
          min={1}
          max={10000}
          onChange={setRatio}
        />
        <ChoiceField
          label='Way in'
          value={entry}
          table={REALM_ENTRIES}
          blocked={blocked}
          onPick={setEntry}
        />
        <ChoiceField
          label='Whether those inside know'
          value={aware}
          table={REALM_AWARENESS}
          blocked={blocked}
          onPick={setAware}
        />
        <ChoiceField
          label='What keeps its host running'
          value={upkeep}
          table={MIND_UPKEEPS}
          blocked={blocked}
          onPick={setUpkeep}
        />
      </ForgeCard>
    </div>
  )
}

export function MadeWorldSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeMadeWorld(nodeId)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-made-world'
      title='The made world: intrusions, stores, watching, trust, companies, self-making lines, abundance, relics and made realms'
      description='Everything made minds and their makers build around this thing: what breaks into it, what it keeps and watches, how far its records are trusted, what it owns and makes, what it has lost the making of and the realms it keeps.'
      icon={MADE_WORLD_ICON}
      tone='gold'
    >
      <div
        data-surface='MadeWorldSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the made world around it' />
        ) : query.isError ? (
          <EmptyState
            icon={MADE_WORLD_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Intrusions view={query.data} blocked={blocked} />
            <Stores view={query.data} blocked={blocked} />
            {query.data.surveillance && (
              <div className='flex min-w-0 flex-col gap-3'>
                <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
                  <KpiTile
                    label='Capacity of the watch'
                    value={String(query.data.surveillance.capacity)}
                    icon={Eye}
                    tone='warning'
                  />
                  <KpiTile
                    label='Reach of the watch'
                    value={`${query.data.surveillance.reach_pct}%`}
                    icon={Eye}
                    tone='warning'
                  />
                  <KpiTile
                    label='It looks for'
                    value={
                      SURVEILLANCE_FOCUSES[query.data.surveillance.focus].label
                    }
                    icon={
                      SURVEILLANCE_FOCUSES[query.data.surveillance.focus].icon
                    }
                    tone={
                      SURVEILLANCE_FOCUSES[query.data.surveillance.focus].tone
                    }
                  />
                </div>
                <Muted variant='caption'>
                  Reckoned in epoch {query.data.surveillance.updated_epoch}.
                </Muted>
                <ProfileEditor
                  title='Set the watch'
                  nodeId={nodeId}
                  tableName='surveillance_profiles'
                  fields={SURVEILLANCE_FIELDS}
                  locked={query.data.surveillance.locked}
                  blocked={blocked}
                />
              </div>
            )}
            {query.data.trust && (
              <div className='flex min-w-0 flex-col gap-3'>
                <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
                  <KpiTile
                    label='Trust in its records'
                    value={String(query.data.trust.information_trust)}
                    icon={BadgeCheck}
                    tone={
                      query.data.trust.information_trust < 30
                        ? 'danger'
                        : 'success'
                    }
                  />
                  <KpiTile
                    label='Records held genuine'
                    value={`${query.data.trust.shared_account_pct}%`}
                    icon={BadgeCheck}
                    tone='info'
                  />
                  <KpiTile
                    label='Reckoned in epoch'
                    value={String(query.data.trust.updated_epoch)}
                    icon={BadgeCheck}
                    tone='muted'
                  />
                </div>
                <ProfileEditor
                  title='Set its trust'
                  nodeId={nodeId}
                  tableName='information_trust'
                  fields={TRUST_FIELDS}
                  locked={query.data.trust.locked}
                  blocked={blocked}
                />
              </div>
            )}
            <Rows
              items={query.data.records}
              empty='It keeps no record whose truth can be marked.'
              render={(record) => (
                <RecordMark key={record.id} record={record} blocked={blocked} />
              )}
            />
            <Company view={query.data} blocked={blocked} />
            <Replicators view={query.data} blocked={blocked} />
            <Abundance view={query.data} blocked={blocked} />
            <Relics view={query.data} blocked={blocked} />
            <Rows
              items={query.data.substrates}
              empty='Its members are not counted by the seat of their minds.'
              render={(row) => (
                <RecordRow
                  key={row.seat}
                  icon={MIND_SEATS[row.seat].icon}
                  tone={MIND_SEATS[row.seat].tone}
                  title={`${row.share_pct}% ${MIND_SEATS[row.seat].label.toLowerCase()}`}
                  caption={MIND_ORIGINS[row.origin].label}
                >
                  <RowEditor
                    title='Set this share of the people'
                    tableName='people_substrates'
                    rowKey={{ people_entity_id: nodeId, seat: row.seat }}
                    fields={SUBSTRATE_FIELDS}
                    locked={row.locked}
                    blocked={blocked}
                  />
                </RecordRow>
              )}
            />
            <Realms view={query.data} blocked={blocked} />
            {query.data.doctrine && (
              <div className='flex min-w-0 flex-col gap-3'>
                <div className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Chip
                    icon={
                      MADE_MIND_STANCES[query.data.doctrine.made_mind_stance]
                        .icon
                    }
                  >
                    Made minds:{' '}
                    {MADE_MIND_STANCES[
                      query.data.doctrine.made_mind_stance
                    ].label.toLowerCase()}
                  </Chip>
                  <Chip
                    icon={
                      MADE_MIND_STANCES[query.data.doctrine.copy_stance].icon
                    }
                  >
                    Copies:{' '}
                    {MADE_MIND_STANCES[
                      query.data.doctrine.copy_stance
                    ].label.toLowerCase()}
                  </Chip>
                  <Chip
                    icon={
                      MADE_MIND_STANCES[query.data.doctrine.augment_stance].icon
                    }
                  >
                    Augments:{' '}
                    {MADE_MIND_STANCES[
                      query.data.doctrine.augment_stance
                    ].label.toLowerCase()}
                  </Chip>
                  <Chip
                    icon={
                      MADE_MIND_STANCES[
                        query.data.doctrine.made_afterlife_stance
                      ].icon
                    }
                  >
                    Afterlife of made minds:{' '}
                    {MADE_MIND_STANCES[
                      query.data.doctrine.made_afterlife_stance
                    ].label.toLowerCase()}
                  </Chip>
                  <Chip
                    icon={RELIC_STANCES[query.data.doctrine.relic_stance].icon}
                  >
                    Relics:{' '}
                    {RELIC_STANCES[
                      query.data.doctrine.relic_stance
                    ].label.toLowerCase()}
                  </Chip>
                </div>
                <ProfileEditor
                  title='Set what this faith holds of made things'
                  nodeId={nodeId}
                  tableName='cult_doctrines'
                  fields={DOCTRINE_FIELDS}
                  locked={query.data.doctrine.locked}
                  blocked={blocked}
                />
              </div>
            )}
          </>
        )}
      </div>
    </Section>
  )
}
